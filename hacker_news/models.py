import os

from datetime import datetime
from sqlalchemy import (Boolean, Column, Date, ForeignKey, Index, Integer,
    create_engine)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.types import Enum, TEXT, TIMESTAMP


def normalize_database_url(database_url):
    if database_url and database_url.startswith('postgres://'):
        return database_url.replace('postgres://', 'postgresql://', 1)
    return database_url


def create_database_engine(database_url):
    return create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
    )


database_url = os.getenv('DB_CONNECTION') or os.getenv('DATABASE_URL')
engine = create_database_engine(database_url) if database_url else None
Session = sessionmaker(bind=engine, expire_on_commit=False)

Base = declarative_base()


class Feed(Base):
    __tablename__ = 'feed'
    id = Column(Integer, primary_key=True, nullable=False)
    created = Column(TIMESTAMP(timezone=False), default=datetime.utcnow,
        nullable=False)
    # Set once this feed's raw rows have been folded into the rollup tables
    # and deleted. Written in the same transaction as the merge, which is what
    # makes the prune job exactly-once.
    rolled_up = Column(Boolean, default=False, nullable=False,
        server_default='false')


class Post(Base):
    __tablename__ = 'post'
    id = Column(Integer, primary_key=True, nullable=False)
    created = Column(TIMESTAMP(timezone=False), default=datetime.utcnow,
        nullable=False)
    link = Column(TEXT, nullable=False)
    title = Column(TEXT, nullable=False)
    type = Column(Enum('article', 'ask', 'job', 'show', name='post_type'),
        nullable=False)
    username = Column(TEXT)
    website = Column(TEXT)
    __table_args__ = (Index('post_index', 'id', 'username'), )


class Comment(Base):
    __tablename__ = 'comment'
    id = Column(Integer, primary_key=True, nullable=False)
    content = Column(TEXT, nullable=False)
    created = Column(TIMESTAMP(timezone=False), default=datetime.utcnow,
        nullable=False)
    level = Column(Integer, nullable=False)
    parent_comment = Column(Integer,
        ForeignKey('comment.id', ondelete='CASCADE'), nullable=True)
    post_id = Column(Integer, ForeignKey('post.id', ondelete='CASCADE'),
        nullable=False)
    total_word_count = Column(Integer, default=0, nullable=False)
    username = Column(TEXT, nullable=False)
    word_counts = Column(TSVECTOR, nullable=False)

    post = relationship("Post", back_populates='comments')


Post.comments = relationship(
    "Comment", order_by=Comment.created, back_populates='post')


class FeedPost(Base):
    __tablename__ = 'feed_post'
    feed_id = Column(Integer, ForeignKey('feed.id', ondelete='CASCADE'),
        primary_key=True, nullable=False)
    post_id = Column(Integer, ForeignKey('post.id', ondelete='CASCADE'),
        primary_key=True, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    feed_rank = Column(Integer, nullable=False)
    point_count = Column(Integer, default=0, nullable=False)
    __table_args__ = (Index('feed_post_index', 'comment_count', 'feed_id',
        'feed_rank', 'point_count', 'post_id'), )

    post = relationship("Post", back_populates='feeds')


Post.feeds = relationship(
    "FeedPost", order_by=FeedPost.feed_id, back_populates='post')


class FeedComment(Base):
    __tablename__ = 'feed_comment'
    comment_id = Column(Integer, ForeignKey('comment.id', ondelete='CASCADE'),
        primary_key=True, nullable=False)
    feed_id = Column(Integer, ForeignKey('feed.id', ondelete='CASCADE'),
        primary_key=True, nullable=False)
    feed_rank = Column(Integer, nullable=False)
    # The primary key leads with comment_id, so it cannot serve the stats
    # queries, which all filter by feed_id
    __table_args__ = (Index('feed_comment_feed_id_index', 'feed_id'), )

    comment = relationship("Comment", back_populates='feeds')


Comment.feeds = relationship(
    "FeedComment", order_by=FeedComment.feed_id, back_populates='comment')


# Rollup tables below. They hold the permanent aggregate history that lets the
# 'all' time period keep answering after raw comments and feed links have been
# pruned. Facts attached to a feed are folded in when that feed ages out;
# facts attached to a comment are folded in when that comment is deleted,
# because a comment appears in roughly thirteen feeds and rolling it up
# per-feed would count it thirteen times.

class FeedSummary(Base):
    __tablename__ = 'feed_summary'
    feed_id = Column(Integer, ForeignKey('feed.id', ondelete='CASCADE'),
        primary_key=True, nullable=False)
    post_row_count = Column(Integer, default=0, nullable=False)
    sum_point_count = Column(Integer, default=0, nullable=False)
    sum_comment_count = Column(Integer, default=0, nullable=False)


class CommentDailyTotal(Base):
    __tablename__ = 'comment_daily_total'
    # The day the comment was written, not the day it was pruned
    day = Column(Date, primary_key=True, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    sum_level = Column(Integer, default=0, nullable=False)
    sum_word_count = Column(Integer, default=0, nullable=False)


class WordTotal(Base):
    __tablename__ = 'word_total'
    # Stored unfiltered; the LENGTH(word) > 1 filter is applied at read time
    # so it matches whatever the endpoint does
    word = Column(TEXT, primary_key=True, nullable=False)
    ndoc = Column(Integer, default=0, nullable=False)
    nentry = Column(Integer, default=0, nullable=False)


class UserTotal(Base):
    __tablename__ = 'user_total'
    username = Column(TEXT, primary_key=True, nullable=False)
    comment_count = Column(Integer, default=0, nullable=False)
    word_count = Column(Integer, default=0, nullable=False)


class PostStat(Base):
    __tablename__ = 'post_stat'
    post_id = Column(Integer, ForeignKey('post.id', ondelete='CASCADE'),
        primary_key=True, nullable=False)
    max_comment_count = Column(Integer, default=0, nullable=False)
    max_point_count = Column(Integer, default=0, nullable=False)
    # Rank 1 is the top of the front page, so the best rank is the lowest
    best_feed_rank = Column(Integer, nullable=False)


class PinnedComment(Base):
    __tablename__ = 'pinned_comment'
    comment_id = Column(Integer, ForeignKey('comment.id', ondelete='CASCADE'),
        primary_key=True, nullable=False)
    reason = Column(TEXT, nullable=False)
