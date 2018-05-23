import os

from datetime import datetime
from sqlalchemy import create_engine, Column, ForeignKey, Index, Integer, \
    String
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.types import Enum, TEXT, TIMESTAMP


engine = create_engine(os.environ['DB_CONNECTION'])

Base = declarative_base()

Session = sessionmaker(bind=engine)


class Feed(Base):
    __tablename__ = 'feed'
    id = Column(Integer, primary_key=True, nullable=False)
    created = Column(TIMESTAMP(timezone=False), default=datetime.utcnow,
        nullable=False)
    __table_args__ = (Index('feed_id_index', 'id'), )


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
    __table_args__ = (Index('comment_index', 'id', 'level', 'parent_comment',
        'post_id', 'total_word_count', 'username'), )

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
    __table_args__ = (Index('feed_comment_index', 'comment_id', 'feed_id',
        'feed_rank'), )

    comment = relationship("Comment", back_populates='feeds')


Comment.feeds = relationship(
    "FeedComment", order_by=FeedComment.feed_id, back_populates='comment')


class UserContentCounts(Base):
    __tablename__ = 'user_content_counts'
    feed_id = Column(Integer, ForeignKey('feed.id'), primary_key=True)
    username = Column(TEXT, primary_key=True)
    comment_count = Column(Integer)
    word_count = Column(Integer)
    __table_args__ = (Index('user_content_index', 'comment_count',
        'feed_id', 'username', 'word_count'), )
