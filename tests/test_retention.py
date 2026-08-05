from sqlalchemy import func, text

from hacker_news import hacker_news, models, retention
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


class MergeFeedRollupsTest(HackerNewsTestCase):
    def test_merges_feed_post_rows_into_summary_and_post_stat(self):
        session = models.Session()

        try:
            # Fixture feed 4 holds one feed_post: rank 7, points 7, comments 7
            retention.merge_feed_rollups(session, 4)
            session.commit()

            summary = session.get(models.FeedSummary, 4)

            self.assertEqual(summary.post_row_count, 1)
            self.assertEqual(summary.sum_point_count, 7)
            self.assertEqual(summary.sum_comment_count, 7)

            stat = session.get(models.PostStat, 6)

            self.assertEqual(stat.max_point_count, 7)
            self.assertEqual(stat.max_comment_count, 7)
            self.assertEqual(stat.best_feed_rank, 7)
        finally:
            session.close()

    def test_post_stat_keeps_best_value_seen(self):
        session = models.Session()

        try:
            session.add(models.PostStat(post_id=6, max_comment_count=99,
                max_point_count=2, best_feed_rank=1))
            session.commit()

            retention.merge_feed_rollups(session, 4)
            session.commit()

            stat = session.get(models.PostStat, 6)

            # Counts keep the higher value; rank keeps the LOWER one, because
            # rank 1 is the top of the front page
            self.assertEqual(stat.max_comment_count, 99)
            self.assertEqual(stat.max_point_count, 7)
            self.assertEqual(stat.best_feed_rank, 1)
        finally:
            session.close()

    def test_summary_accumulates_when_called_again(self):
        session = models.Session()

        try:
            retention.merge_feed_rollups(session, 4)
            session.commit()
            retention.merge_feed_rollups(session, 4)
            session.commit()

            summary = session.get(models.FeedSummary, 4)

            # Not idempotent by design -- the prune job's transaction plus the
            # rolled_up flag is what guarantees this runs once per feed
            self.assertEqual(summary.post_row_count, 2)
            self.assertEqual(summary.sum_point_count, 14)
        finally:
            session.close()


class MergeCommentRollupsTest(HackerNewsTestCase):
    def test_merges_one_comment_exactly_once(self):
        session = models.Session()

        try:
            comment = session.get(models.Comment, 8)
            expected_words = comment.total_word_count
            expected_day = comment.created.date()
            username = comment.username

            retention.merge_comment_rollups(session, [8])
            session.commit()

            daily = session.get(models.CommentDailyTotal, expected_day)

            self.assertEqual(daily.comment_count, 1)
            self.assertEqual(daily.sum_word_count, expected_words)

            user = session.get(models.UserTotal, username)

            self.assertEqual(user.comment_count, 1)
            self.assertEqual(user.word_count, expected_words)

            self.assertTrue(session.query(models.WordTotal).count() > 0)
        finally:
            session.close()

    def test_buckets_by_the_day_the_comment_was_written(self):
        session = models.Session()

        try:
            comment = session.get(models.Comment, 8)
            written_day = comment.created.date()

            retention.merge_comment_rollups(session, [8])
            session.commit()

            days = [row.day for row in
                    session.query(models.CommentDailyTotal).all()]

            self.assertEqual(days, [written_day])
        finally:
            session.close()

    def test_stores_single_character_words_unfiltered(self):
        # The LENGTH(word) > 1 filter belongs at read time, matching the
        # endpoint. Storing pre-filtered would silently change results if that
        # threshold ever moved.
        #
        # 'q' rather than 'a': simple_english carries english stopwords, so
        # to_tsvector drops 'a' at index time and it never reaches storage at
        # all. That is a different mechanism from the read-time length filter.
        session = models.Session()

        try:
            session.execute(text(
                "UPDATE comment SET word_counts = to_tsvector("
                "'simple_english', 'q bb') WHERE id = 8"))
            session.commit()

            retention.merge_comment_rollups(session, [8])
            session.commit()

            words = {w.word for w in session.query(models.WordTotal).all()}

            self.assertIn('q', words)
        finally:
            session.close()

    def test_ignores_blank_usernames(self):
        session = models.Session()

        try:
            session.execute(
                text("UPDATE comment SET username = '' WHERE id = 8"))
            session.commit()

            retention.merge_comment_rollups(session, [8])
            session.commit()

            self.assertEqual(session.query(models.UserTotal).count(), 0)
        finally:
            session.close()

    def test_empty_input_is_a_no_op(self):
        session = models.Session()

        try:
            retention.merge_comment_rollups(session, [])
            session.commit()

            self.assertEqual(session.query(models.CommentDailyTotal).count(), 0)
        finally:
            session.close()


class UpdatePinsTest(HackerNewsTestCase):
    def _add_comment(self, session, comment_id, level, parent, words):
        base = session.get(models.Comment, 8)

        session.add(models.Comment(id=comment_id, content='c%d' % comment_id,
            created=base.created, level=level, parent_comment=parent,
            post_id=base.post_id, total_word_count=words, username='someone',
            word_counts=func.to_tsvector('simple_english', 'c%d' % comment_id)))

    def test_pins_record_holder_and_returns_it_as_keepable(self):
        session = models.Session()

        try:
            keep = retention.update_pins(session, [8])
            session.commit()

            self.assertIn(8, keep)
            self.assertIsNotNone(session.get(models.PinnedComment, 8))
        finally:
            session.close()

    def test_pins_deepest_comment_with_full_ancestor_chain(self):
        session = models.Session()

        try:
            self._add_comment(session, 900, 0, None, 1)
            self._add_comment(session, 901, 1, 900, 1)
            self._add_comment(session, 902, 9, 901, 1)
            session.commit()

            keep = retention.update_pins(session, [900, 901, 902])
            session.commit()

            # The deepest comment is useless without its ancestors -- the tree
            # endpoint walks parent_comment to render the thread
            self.assertIn(902, keep)
            self.assertIn(901, keep)
            self.assertIn(900, keep)
        finally:
            session.close()

    def test_keeps_only_the_top_n_by_word_count(self):
        session = models.Session()

        try:
            limit = hacker_news.MAX_RESULT_COUNT

            for i in range(limit + 5):
                self._add_comment(session, 1000 + i, 0, None, i + 1)

            session.commit()

            retention.update_pins(session,
                [1000 + i for i in range(limit + 5)])
            session.commit()

            pinned = session.query(models.PinnedComment).filter_by(
                reason='word_count').count()

            self.assertEqual(pinned, limit)
        finally:
            session.close()

    def test_empty_input_is_a_no_op(self):
        session = models.Session()

        try:
            self.assertEqual(retention.update_pins(session, []), set())
        finally:
            session.close()
