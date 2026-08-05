from unittest import mock

from hacker_news import hacker_news
from utils.tests import HackerNewsTestCase


class ScrapeFailureVisibilityTest(HackerNewsTestCase):
    """A failing scrape must not report success.

    scrape_loop originally used asyncio.wait, which captures task exceptions
    inside the Task objects instead of raising. Every page task could die and
    the run would still print 'Scrape completed', leaving an empty feed in the
    database. That is how eight-year-old stale fixtures went unnoticed, and it
    would hide a real Hacker News markup change the same way.
    """

    def test_page_failure_propagates(self):
        with mock.patch('requests.get',
                side_effect=RuntimeError('network down')):
            with self.assertRaises(RuntimeError):
                hacker_news.scrape_loop()

    def test_scrape_loop_can_run_more_than_once(self):
        # scrape_loop closed the global event loop, so a second call in the
        # same process failed with 'Event loop is closed'
        hacker_news.scrape_loop()
        hacker_news.scrape_loop()
