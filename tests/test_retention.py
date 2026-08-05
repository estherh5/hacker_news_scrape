from hacker_news import models
from utils.tests import HackerNewsTestCase


class RollupSchemaTest(HackerNewsTestCase):
    def test_rollup_tables_exist_and_are_empty(self):
        session = models.Session()

        try:
            self.assertEqual(session.query(models.FeedSummary).count(), 0)
            self.assertEqual(session.query(models.CommentDailyTotal).count(), 0)
            self.assertEqual(session.query(models.WordTotal).count(), 0)
            self.assertEqual(session.query(models.UserTotal).count(), 0)
            self.assertEqual(session.query(models.PostStat).count(), 0)
            self.assertEqual(session.query(models.PinnedComment).count(), 0)
        finally:
            session.close()

    def test_feeds_start_not_rolled_up(self):
        session = models.Session()

        try:
            feeds = session.query(models.Feed).all()

            self.assertTrue(len(feeds) > 0)
            self.assertTrue(all(feed.rolled_up is False for feed in feeds))
        finally:
            session.close()
