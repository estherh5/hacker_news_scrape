import alembic.config
import json
import os
import testing.postgresql
import unittest

from datetime import date, datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from testing.common.database import DatabaseFactory
from unittest import mock

from hacker_news import hacker_news, models
from server import app

import management


# Mock requests to Hacker News to test scrape function
def mocked_requests_get(*args, **kwargs):
    class MockResponse:
        def __init__(self, content, status_code):
            self.content = content
            self.status_code = status_code

    feed_urls = []
    feed_pages = []

    post_urls = []
    post_pages = []

    for i in range(1, 4):
        feed_urls.append('https://news.ycombinator.com/news?p=' + str(i))

        feed_page = 'fixtures/test-feed-page-' + str(i) + '.html'

        with open(feed_page, 'r') as test_feed_page:
            test_feed_page = test_feed_page.read()

            feed_pages.append(test_feed_page.encode('utf-8'))

        post_urls.append('https://news.ycombinator.com/item?id=' + str(i))

        post_page = 'fixtures/test-post-' + str(i) + '-page.html'

        with open(post_page, 'r') as test_post_page:
            test_post_page = test_post_page.read()

        post_pages.append(test_post_page.encode('utf-8'))

    post_urls.append('https://news.ycombinator.com/item?id=3&p=2')

    post_page = 'fixtures/test-post-3-page-2.html'
    with open(post_page, 'r') as test_post_page:
        test_post_page = test_post_page.read()

    post_pages.append(test_post_page.encode('utf-8'))

    for i in range(len(feed_urls)):
        if args[0] == feed_urls[i]:
            return MockResponse(feed_pages[i], 200)

    for i in range(len(post_urls)):
        if args[0] == post_urls[i]:
            return MockResponse(post_pages[i], 200)


# Create database tables and load initial data from fixtures and fake HN scrape
# into test database
@mock.patch('requests.get', side_effect=mocked_requests_get)
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
