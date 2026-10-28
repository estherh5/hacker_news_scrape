from unittest import mock

from hacker_news import hacker_news, models
from utils.tests import HackerNewsTestCase, mocked_requests_get


def feed_count():
    session = models.Session()

    try:
        return session.query(models.Feed).count()

    finally:
        session.close()


class ScrapeFailureVisibilityTest(HackerNewsTestCase):
    """A failing scrape must not report success or leave anything behind.

    The scraper once ran its page tasks under asyncio.wait, which captures
    task exceptions inside the Task objects instead of raising. Every page
    task could die and the run would still print 'Scrape completed', leaving
    an empty feed in the database. That is how eight-year-old stale fixtures
    went unnoticed, and it would hide a real change in Hacker News the same
    way.
    """

    def test_fetch_failure_propagates_and_persists_nothing(self):
        before = feed_count()

        with mock.patch('requests.Session.get',
                side_effect=RuntimeError('network down')):
            with self.assertRaises(RuntimeError):
                hacker_news.scrape_loop()

        self.assertEqual(feed_count(), before)

    def test_midway_failure_persists_nothing(self):
        before = feed_count()

        def fail_on_comment(*args, **kwargs):
            if args[0].endswith('item/104.json'):
                raise RuntimeError('network down')

            return mocked_requests_get(*args, **kwargs)

        with mock.patch('requests.Session.get', side_effect=fail_on_comment):
            with self.assertRaises(RuntimeError):
                hacker_news.scrape_loop()

        self.assertEqual(feed_count(), before)

    def test_scrape_loop_can_run_more_than_once(self):
        with mock.patch('requests.Session.get',
                side_effect=mocked_requests_get):
            first = hacker_news.scrape_loop()
            second = hacker_news.scrape_loop()

        self.assertNotEqual(first, second)


class EmptySnapshotTest(HackerNewsTestCase):
    """An API that answers but returns nothing must fail, not commit an
    empty Feed."""

    def _run(self, get):
        before = feed_count()

        with mock.patch.object(hacker_news, 'MIN_POSTS', 60), \
                mock.patch('requests.Session.get', side_effect=get):
            with self.assertRaises(RuntimeError):
                hacker_news.scrape_loop()

        self.assertEqual(feed_count(), before)

    def test_empty_topstories_raises_and_persists_nothing(self):
        def get(url, *args, **kwargs):
            if url.endswith('topstories.json'):
                return mock.Mock(status_code=200, json=lambda: [])

            return mocked_requests_get(url, *args, **kwargs)

        self._run(get)

    def test_all_null_items_raises_and_persists_nothing(self):
        def get(url, *args, **kwargs):
            if url.endswith('topstories.json'):
                return mock.Mock(status_code=200, json=lambda: [1, 2, 3])

            return mock.Mock(status_code=200, json=lambda: None)

        self._run(get)
