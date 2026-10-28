from unittest import mock

import requests

from hacker_news import hacker_news, models
from utils.tests import HackerNewsTestCase, mocked_requests_get


class ScrapeMappingTest(HackerNewsTestCase):
    def test_snapshot_walks_comments_pre_order(self):
        with mock.patch('requests.Session.get',
                side_effect=mocked_requests_get):
            snapshot = hacker_news.fetch_snapshot()

        self.assertEqual([post['rank'] for post in snapshot], [1, 2, 3])

        # (id, level, parent, rank) of the job post's comment tree
        self.assertEqual(
            [(item['id'], level, parent, rank)
                for item, level, parent, rank in snapshot[2]['comments']],
            [(103, 0, None, 1), (104, 0, None, 2), (105, 1, 104, 3)])

    def test_nested_comment_gets_its_true_parent(self):
        session = models.Session()

        try:
            comment = session.get(models.Comment, 105)

            self.assertEqual(comment.parent_comment, 104)
            self.assertEqual(comment.level, 1)
        finally:
            session.close()

    def test_deleted_comment_and_job_mapping(self):
        session = models.Session()

        try:
            comment = session.get(models.Comment, 103)
            post = session.get(models.Post, 3)

            self.assertEqual(comment.content, '[deleted]')
            self.assertEqual(comment.total_word_count, 0)
            self.assertEqual(comment.username, '')
            self.assertEqual(post.type, 'job')
            self.assertEqual(post.username, '')
            self.assertEqual(post.website, 'test2.com')

            # Firebase job items carry a score; the feed must store 0
            self.assertEqual(session.query(models.FeedPost).filter_by(
                post_id=3).one().point_count, 0)

            ask = session.get(models.Post, 2)

            self.assertEqual(ask.link, 'item?id=2')
            self.assertEqual(ask.website, '')
        finally:
            session.close()


class FetchItemTest(HackerNewsTestCase):
    def test_retries_server_errors_then_succeeds(self):
        class Response:
            def __init__(self, status):
                self.status_code = status

            def json(self):
                return {'id': 1}

            def raise_for_status(self):
                pass

        calls = [Response(503), requests.ConnectionError(), Response(200)]

        def get(*args, **kwargs):
            result = calls.pop(0)

            if isinstance(result, Exception):
                raise result

            return result

        with mock.patch('requests.Session.get', side_effect=get), \
                mock.patch.object(hacker_news, 'RETRY_BACKOFF', 0):
            self.assertEqual(hacker_news.fetch_item(1), {'id': 1})

    def test_null_item_is_none(self):
        with mock.patch('requests.Session.get',
                side_effect=mocked_requests_get):
            self.assertIsNone(hacker_news.fetch_item(99999))

    def test_client_error_is_not_retried(self):
        class Response:
            status_code = 404

            def raise_for_status(self):
                raise requests.HTTPError('404')

        with mock.patch('requests.Session.get',
                side_effect=[Response()]) as get, \
                mock.patch.object(hacker_news, 'RETRY_BACKOFF', 0):
            with self.assertRaises(requests.HTTPError):
                hacker_news.fetch_item(1)

        self.assertEqual(get.call_count, 1)

    def test_every_request_sends_user_agent_and_timeout(self):
        with mock.patch('requests.Session.get',
                side_effect=mocked_requests_get) as get:
            hacker_news.fetch_snapshot()

        self.assertGreater(get.call_count, 3)

        for call in get.call_args_list:
            self.assertIn('hacker_news_scrape', call.kwargs['headers'][
                'User-Agent'])
            self.assertIn('github.com/estherh5/hacker_news_scrape',
                call.kwargs['headers']['User-Agent'])
            self.assertEqual(call.kwargs['timeout'],
                hacker_news.REQUEST_TIMEOUT)


class WriteFailureTest(HackerNewsTestCase):
    def test_failure_after_feed_flush_persists_nothing(self):
        def counts():
            session = models.Session()

            try:
                return [session.query(model).count() for model in (
                    models.Feed, models.Post, models.Comment,
                    models.FeedPost, models.FeedComment)]
            finally:
                session.close()

        before = counts()

        # The seeded database already holds these items, so fail at the
        # commit: the Feed and FeedPost rows have been flushed by then
        failing = models.Session()

        failing.commit = mock.Mock(side_effect=RuntimeError('boom'))

        with mock.patch('requests.Session.get',
                side_effect=mocked_requests_get), \
                mock.patch.object(models, 'Session', return_value=failing):
            with self.assertRaises(RuntimeError):
                hacker_news.scrape_loop()

        self.assertEqual(counts(), before)
