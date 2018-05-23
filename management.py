#!/usr/bin/env python3
import argparse
import getpass
import os

from crontab import CronTab
from datetime import datetime
from sqlalchemy import create_engine, Column, ForeignKey, Index, Integer, \
    MetaData, String, Table
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.types import Enum, TEXT, TIMESTAMP

from hacker_news import hacker_news, models


def initialize_database():
    # Connect to database
    session = models.Session()

    metadata = MetaData()

    # Create post_type Enum type
    post_type = Enum('article', 'ask', 'job', 'show', name='post_type',
        metadata=metadata)

    # Create feed table
    feed = Table('feed', metadata,
        Column('id', Integer, primary_key=True, nullable=False,
            index=True),
        Column('created', TIMESTAMP(timezone=False),
            default=datetime.utcnow, nullable=False)
        )

    # Create post table
    post = Table('post', metadata,
        Column('id', Integer, primary_key=True, nullable=False),
        Column('created', TIMESTAMP(timezone=False),
            default=datetime.utcnow, nullable=False),
        Column('link', TEXT, nullable=False),
        Column('title', TEXT, nullable=False),
        Column('type', post_type, nullable=False),
        Column('username', TEXT),
        Column('website', TEXT),
        Index('post_index', 'id', 'username')
        )

    # Create feed_post table
    feed_post = Table('feed_post', metadata,
        Column('feed_id', Integer,
            ForeignKey('feed.id', ondelete='CASCADE'), primary_key=True,
            nullable=False),
        Column('post_id', Integer,
            ForeignKey('post.id', ondelete='CASCADE'), primary_key=True,
            nullable=False),
        Column('comment_count', Integer, default=0, nullable=False),
        Column('feed_rank', Integer, nullable=False),
        Column('point_count', Integer, default=0, nullable=False),
        Index('feed_post_index', 'comment_count', 'feed_id', 'feed_rank',
            'point_count', 'post_id')
        )

    # Create comment table
    comment = Table('comment', metadata,
        Column('id', Integer, primary_key=True, nullable=False),
        Column('content', TEXT, nullable=False),
        Column('created', TIMESTAMP(timezone=False),
            default=datetime.utcnow, nullable=False),
        Column('level', Integer, nullable=False),
        Column('parent_comment', Integer,
            ForeignKey('comment.id', ondelete='CASCADE'), nullable=False),
        Column('post_id', Integer,
            ForeignKey('post.id', ondelete='CASCADE'), nullable=False),
        Column('total_word_count', Integer, default=0, nullable=False),
        Column('username', TEXT, nullable=False),
        Column('word_counts', TSVECTOR, nullable=False),
        Index('comment_index', 'id', 'level', 'parent_comment', 'post_id',
            'total_word_count', 'username')
        )

    # Create feed_comment table
    feed_comment = Table('feed_comment', metadata,
        Column('comment_id', Integer,
            ForeignKey('comment.id', ondelete='CASCADE'), primary_key=True,
            nullable=False),
        Column('feed_id', Integer,
            ForeignKey('feed.id', ondelete='CASCADE'), primary_key=True,
            nullable=False),
        Column('feed_rank', Integer, nullable=False),
        Index('feed_comment_index', 'comment_id', 'feed_id', 'feed_rank')
        )

    metadata.create_all(models.engine, checkfirst=True)

    # Create materialized view and custom text dictionary for detecting stop
    # words without word stemming
    session.execute(
        """
        CREATE MATERIALIZED VIEW IF NOT EXISTS user_content_counts AS
                 SELECT comment_table.username,
                        count(comment_table.username) AS comment_count,
                        sum(comment_table.total_word_count) AS word_count,
                        comment_table.feed_id
                   FROM (
                         SELECT comment.id, comment.content,
                                comment.username, comment.total_word_count,
                                feed_comment.feed_id
                           FROM comment
                                JOIN feed_comment
                                  ON feed_comment.comment_id = comment.id
                          WHERE comment.username != '') comment_table
               GROUP BY comment_table.username, comment_table.feed_id
               ORDER BY word_count DESC;

        CREATE INDEX IF NOT EXISTS user_content_index
               ON user_content_counts (username, comment_count, word_count,
                                       feed_id);

        DO $$
        BEGIN
            IF NOT EXISTS
                          (SELECT 1
                             FROM pg_ts_dict
                            WHERE dictname = 'simple_english')
                     THEN CREATE TEXT SEARCH DICTIONARY simple_english (
                        TEMPLATE = pg_catalog.simple,
                        STOPWORDS = english
                     );
            END IF;
        END
        $$;

        DO $$
        BEGIN
            IF NOT EXISTS
                          (SELECT 1
                             FROM pg_ts_config
                            WHERE cfgname = 'simple_english')
                     THEN CREATE TEXT SEARCH CONFIGURATION simple_english (
                        COPY = english
                     );
            END IF;
        END
        $$;

        ALTER TEXT SEARCH CONFIGURATION simple_english
            ALTER MAPPING FOR asciihword, asciiword, hword, hword_asciipart,
                              hword_part, word
                         WITH simple_english;
        """
        )

    session.commit()

    session.close()

    print('Database ' + os.environ['DB_NAME'] + ' initialized successfully.')

    return


def schedule_hourly_scrape():
    # Initiate CronTab instance for current user
    user = getpass.getuser()
    cron = CronTab(user)

    # Create hourly job to scrape Hacker News website
    job = cron.new(
        command='export WORKON_HOME=~/.virtualenvs; ' +
        'VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3; ' +
        'source /usr/local/bin/virtualenvwrapper.sh; ' +
        'workon ' + os.environ['VIRTUAL_ENV_NAME'] + '; ' +
        'source ~/.virtualenvs/' + os.environ['VIRTUAL_ENV_NAME'] +
        '/bin/postactivate; python ' + os.path.abspath(__file__) + ' scrape_hn'
        )
    job.minute.on(0)

    cron.write()

    print('Hourly scrape scheduled for Hacker News.')

    return


# Add arguments for initializing database in CLI
parser = argparse.ArgumentParser(description='Management commands')
parser.add_argument('action', type=str, help="an action for the database")
args = parser.parse_args()
if args.action == 'init_db':
    initialize_database()
if args.action == 'sched_scrape':
    schedule_hourly_scrape()
if args.action == 'scrape_hn':
    hacker_news.scrape_loop()
