import alembic.config
import json
import os
import requests
import testing.postgresql
import time
import unittest

from datetime import date, datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from testing.common.database import DatabaseFactory
from unittest import mock

from hacker_news import hacker_news, models
from server import app

import management


# Mock requests to the Hacker News Firebase API to test scrape function. The
# fixtures under fixtures/firebase hold each item's age in "age_seconds" rather
# than a fixed "time", so the seeded rows always fall in the same 'hour',
# 'day', 'week' and 'all' periods whenever the suite runs.
def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, data, status_code):
            self.data = data
            self.status_code = status_code

        def json(self):
            return self.data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.HTTPError(str(self.status_code))

    prefix = 'https://hacker-news.firebaseio.com/v0/'
    url = args[0]

    assert url.startswith(prefix), 'Unexpected request to ' + url

    name = url[len(prefix):-len('.json')]

    if name == 'topstories':
        path = 'fixtures/firebase/topstories.json'
    else:
        path = 'fixtures/firebase/' + name.replace('/', '-') + '.json'

    if not os.path.exists(path):
        return MockResponse(None, 200)

    with open(path, 'r') as fixture:
        data = json.load(fixture)

    if isinstance(data, dict) and 'age_seconds' in data:
        data['time'] = int(time.time()) - data.pop('age_seconds')

    return MockResponse(data, 200)


# Create database tables and load initial data from fixtures and fake HN scrape
# into test database
@mock.patch('requests.Session.get', side_effect=mocked_requests_get)
def initialize_test_database(postgresql, mock_get):
    db_port = postgresql.dsn()['port']
    db_host = postgresql.dsn()['host']
    db_user = postgresql.dsn()['user']
    database = postgresql.dsn()['database']
    os.environ['DB_NAME'] = database

    os.environ['DB_CONNECTION'] = ('postgresql://' + db_user + '@' + db_host +
        ':' + str(db_port) + '/' + database)

    models.engine = create_engine(os.environ['DB_CONNECTION'])

    models.Session = sessionmaker(bind=models.engine)

    # Create custom text dictionary and database tables
    management.initialize_database()

    alembicArgs = [
        '--raiseerr',
        'upgrade', 'head',
    ]

    alembic.config.main(argv=alembicArgs)

    # Run fake Hacker News scrape to get sample feed, post, and comment from
    # past hour
    hacker_news.scrape_loop()

    # Connect to database
    session = models.Session()

    # Add sample feed to database for remaining time periods ('day', 'week',
    # 'all')
    past_day_feed = models.Feed(id=2, created=(
        datetime.combine(date.today(), datetime.min.time())).isoformat())
    session.add(past_day_feed)

    past_week_feed = models.Feed(id=3, created=(
        datetime.combine(date.today() - timedelta(days=5),
        datetime.min.time())).isoformat())
    session.add(past_week_feed)

    all_feed = models.Feed(id=4, created=(
        datetime.combine(date.today() - timedelta(weeks=2),
        datetime.min.time())).isoformat())
    session.add(all_feed)

    # Add sample post to database for remaining time periods ('day', 'week',
    # 'all')
    posts_file = 'fixtures/test-post.json'
    with open(posts_file, 'r') as post_data:
        post = json.load(post_data)

    past_day_post = models.Post(created=(
        datetime.combine(date.today() - timedelta(hours=20),
        datetime.min.time())).isoformat(), id=4, link=post['link'],
        title=post['title'], type='job', username=post['username'],
        website=post['website'])

    session.add(past_day_post)

    past_week_post = models.Post(created=(
        datetime.combine(date.today() - timedelta(days=5),
        datetime.min.time())).isoformat(), id=5, link=post['link'],
        title=post['title'], type='ask', username=post['username'],
        website=post['website'])

    session.add(past_week_post)

    all_post = models.Post(created=(
        datetime.combine(date.today() - timedelta(weeks=2),
        datetime.min.time())).isoformat(), id=6, link=post['link'],
        title=post['title'], type='show', username=post['username'],
        website=post['website'])

    session.add(all_post)

    # Add sample feed_post data to database for each feed and post
    past_day_feed_post = models.FeedPost(feed_id=past_day_feed.id,
        feed_rank=3, point_count=3, post_id=past_day_post.id, comment_count=3)

    session.add(past_day_feed_post)

    past_week_feed_post = models.FeedPost(feed_id=past_week_feed.id,
        feed_rank=5, point_count=5, post_id=past_week_post.id, comment_count=5)

    session.add(past_week_feed_post)

    all_feed_post = models.FeedPost(feed_id=all_feed.id,
        feed_rank=7, point_count=7, post_id=all_post.id, comment_count=7)

    session.add(all_feed_post)

    # Add sample comment to database for remaining time periods ('day', 'week',
    # 'all')
    comment_file = 'fixtures/test-comment.json'
    with open(comment_file, 'r') as comment_data:
        comment = json.load(comment_data)

    past_day_comment = models.Comment(content=comment['content'], created=(
        datetime.combine(date.today() - timedelta(hours=20),
        datetime.min.time())).isoformat(), id=6, level=0,
        parent_comment=None, post_id=past_day_post.id,
        total_word_count=len(comment['content'].split()),
        username=comment['username'],
        word_counts=func.to_tsvector('simple_english',
        comment['content'].lower()))

    session.add(past_day_comment)

    past_week_comment = models.Comment(content=comment['content'], created=(
        datetime.combine(date.today() - timedelta(days=5),
        datetime.min.time())).isoformat(), id=7, level=0,
        parent_comment=None, post_id=past_week_post.id,
        total_word_count=len(comment['content'].split()),
        username=comment['username'],
        word_counts=func.to_tsvector('simple_english',
        comment['content'].lower()))

    session.add(past_week_comment)

    all_comment = models.Comment(content=comment['content'], created=(
        datetime.combine(date.today() - timedelta(weeks=2),
        datetime.min.time())).isoformat(), id=8, level=0,
        parent_comment=None, post_id=all_post.id,
        total_word_count=len(comment['content'].split()),
        username=comment['username'],
        word_counts=func.to_tsvector('simple_english',
        comment['content'].lower()))

    session.add(all_comment)

    # Add sample feed_comment data to database for each feed and comment
    past_day_feed_comment = models.FeedComment(
        comment_id=past_day_comment.id, feed_id=past_day_feed.id,
        feed_rank=3)

    session.add(past_day_feed_comment)

    past_week_feed_comment = models.FeedComment(
        comment_id=past_week_comment.id, feed_id=past_week_feed.id,
        feed_rank=5)

    session.add(past_week_feed_comment)

    all_feed_comment = models.FeedComment(comment_id=all_comment.id,
        feed_id=all_feed.id, feed_rank=7)

    session.add(all_feed_comment)

    session.commit()

    # The rows above set their ids explicitly, which does not advance the
    # serial sequences. Without this, the next inserted Feed, Post or Comment
    # reuses an id that already exists and fails on the primary key.
    for table in ('feed', 'post', 'comment'):
        session.execute(text(
            "SELECT setval(pg_get_serial_sequence('%s', 'id'), "
            "COALESCE((SELECT max(id) FROM %s), 1))" % (table, table)))

    session.commit()

    session.close()


# Create factory instance of Postgresql class that has cached database for
# testing
class PostgresqlFactory(DatabaseFactory):
    target_class = testing.postgresql.Postgresql


Postgresql = PostgresqlFactory(cache_initialized_db=True,
                               on_initialized=initialize_test_database)


class HackerNewsTestCase(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.postgresql = Postgresql()
        self.db_port = self.postgresql.dsn()['port']
        self.db_host = self.postgresql.dsn()['host']
        self.db_user = self.postgresql.dsn()['user']
        self.database = self.postgresql.dsn()['database']

        os.environ['DB_CONNECTION'] = ('postgresql://' + self.db_user + '@' +
            self.db_host + ':' + str(self.db_port) + '/' + self.database)

        models.engine = create_engine(os.environ['DB_CONNECTION'])

        models.Session = sessionmaker(bind=models.engine)

    def tearDown(self):
        self.postgresql.stop()
