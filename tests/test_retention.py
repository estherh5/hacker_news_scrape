from unittest import mock

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


class PruneAgedFeedsTest(HackerNewsTestCase):
    def test_prunes_only_feeds_outside_the_window(self):
        session = models.Session()

        try:
            # Fixture feed 4 is two weeks old; feed 3 is five days old
            self.assertEqual(retention.prune_aged_feeds(), 1)

            session.expire_all()

            self.assertTrue(session.get(models.Feed, 4).rolled_up)
            self.assertFalse(session.get(models.Feed, 3).rolled_up)

            self.assertEqual(session.query(models.FeedComment).filter(
                models.FeedComment.feed_id == 4).count(), 0)
            self.assertTrue(session.query(models.FeedComment).filter(
                models.FeedComment.feed_id == 3).count() > 0)

            # Posts and feeds themselves are never deleted
            self.assertIsNotNone(session.get(models.Post, 6))
            self.assertIsNotNone(session.get(models.Feed, 4))
        finally:
            session.close()

    def test_is_exactly_once(self):
        session = models.Session()

        try:
            retention.prune_aged_feeds()

            session.expire_all()
            first = session.get(models.FeedSummary, 4).sum_point_count

            self.assertEqual(retention.prune_aged_feeds(), 0)

            session.expire_all()
            second = session.get(models.FeedSummary, 4).sum_point_count

            self.assertEqual(first, second)
        finally:
            session.close()

    def test_keeps_comment_still_linked_to_an_in_window_feed(self):
        session = models.Session()

        try:
            # Comment 8 now appears in aged feed 4 AND in-window feed 3, the
            # way a comment that sits on the front page for over a week does
            session.add(models.FeedComment(comment_id=8, feed_id=3,
                feed_rank=1))
            session.commit()

            retention.prune_aged_feeds()
            session.expire_all()

            self.assertIsNotNone(session.get(models.Comment, 8))

            # And it must NOT be rolled up yet, or it double-counts when its
            # last link finally disappears
            self.assertEqual(session.query(models.UserTotal).count(), 0)
            self.assertEqual(session.query(models.CommentDailyTotal).count(), 0)
        finally:
            session.close()

    def test_rolls_up_comment_when_its_last_link_goes(self):
        session = models.Session()

        try:
            base = session.get(models.Comment, 8)

            # An ordinary comment is only deleted if it is not a record
            # holder, so give it competition: one much longer comment and one
            # much deeper one. MAX_RESULT_COUNT is pinned to 1 so exactly one
            # word-count record is held rather than the usual hundred.
            for cid, level, words in ((910, 0, 999), (911, 99, 1), (912, 0, 2)):
                session.add(models.Comment(id=cid, content='c%d' % cid,
                    created=base.created, level=level, parent_comment=None,
                    post_id=base.post_id, total_word_count=words,
                    username='someone', word_counts=func.to_tsvector(
                        'simple_english', 'c%d' % cid)))

                # Link them to the aged feed. Pruning only considers comments
                # the pruned feed referenced, which is what a real comment
                # always looks like.
                session.add(models.FeedComment(comment_id=cid, feed_id=4,
                    feed_rank=1))

            session.commit()

            with mock.patch.object(hacker_news, 'MAX_RESULT_COUNT', 1):
                retention.prune_aged_feeds()

            session.expire_all()

            # 910 is pinned as longest, 911 as deepest, 912 is neither
            self.assertIsNotNone(session.get(models.Comment, 910))
            self.assertIsNotNone(session.get(models.Comment, 911))
            self.assertIsNone(session.get(models.Comment, 912))

            # and the deleted one was counted on its way out
            self.assertEqual(session.query(models.CommentDailyTotal).count(), 1)
            self.assertTrue(session.query(models.UserTotal).count() > 0)
        finally:
            session.close()

    def test_failure_mid_prune_leaves_no_partial_state(self):
        with mock.patch.object(retention, 'merge_comment_rollups',
                side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                retention.prune_aged_feeds()

        session = models.Session()

        try:
            # Nothing committed: feed unmarked, raw rows intact, no rollups
            self.assertFalse(session.get(models.Feed, 4).rolled_up)
            self.assertTrue(session.query(models.FeedPost).filter(
                models.FeedPost.feed_id == 4).count() > 0)
            self.assertEqual(session.query(models.FeedSummary).count(), 0)
        finally:
            session.close()

        # And a clean re-run completes it
        self.assertEqual(retention.prune_aged_feeds(), 1)


class AverageEndpointsAcrossPruneTest(HackerNewsTestCase):
    ENDPOINTS = (
        'average_comment_count',
        'average_point_count',
        'average_comment_word_count',
        'average_comment_tree_depth',
    )

    def test_all_averages_unchanged_by_pruning(self):
        urls = ['/api/hacker_news/stats/all/%s' % e for e in self.ENDPOINTS]
        before = {u: self.client.get(u).get_data(as_text=True) for u in urls}

        retention.prune_aged_feeds()

        changed = [u for u in urls
                   if self.client.get(u).get_data(as_text=True) != before[u]]

        self.assertEqual(changed, [], 'changed across the prune boundary')


class GoldenEquivalenceTest(HackerNewsTestCase):
    """The primary gate: every stats endpoint, every period, byte-identical
    across the prune boundary."""

    ENDPOINTS = (
        'average_comment_count', 'average_comment_tree_depth',
        'average_comment_word_count', 'average_point_count',
        'comment_words', 'comments_highest_word_count',
        'deepest_comment_tree', 'post_types',
        'posts_highest_comment_count', 'posts_highest_point_count',
        'title_words', 'top_posts', 'top_websites',
        'users_most_comments', 'users_most_posts', 'users_most_words',
    )

    def _capture(self, urls):
        return {u: self.client.get(u).get_data(as_text=True) for u in urls}

    def _seed_prunable_comments(self):
        """Attach enough comments to the aged feed that some are really
        deleted.

        Without this the gate is hollow: the fixture has one aged comment,
        which update_pins correctly keeps as the all-time record holder, so
        nothing is deleted and the rollup read paths are never exercised.

        Seeded past MAX_RESULT_COUNT on purpose. Lowering that cap instead
        would delete more comments but would also stop
        comments_highest_word_count from having enough pinned rows to answer,
        producing a failure that says nothing about the rollups.
        """
        session = models.Session()

        try:
            base = session.get(models.Comment, 8)
            extra = hacker_news.MAX_RESULT_COUNT + 10

            for i in range(extra):
                cid = 1000 + i

                session.add(models.Comment(id=cid, content='seeded %d' % i,
                    created=base.created, level=i % 5, parent_comment=None,
                    post_id=base.post_id, total_word_count=i + 1,
                    username='user%d' % (i % 7),
                    word_counts=func.to_tsvector('simple_english',
                        'seeded alpha%d beta' % i)))

                session.add(models.FeedComment(comment_id=cid, feed_id=4,
                    feed_rank=(i % 30) + 1))

            session.commit()
        finally:
            session.close()

    def test_all_sixteen_endpoints_survive_pruning(self):
        self._seed_prunable_comments()

        urls = ['/api/hacker_news/stats/all/%s' % e for e in self.ENDPOINTS]
        before = self._capture(urls)

        session = models.Session()

        try:
            before_comments = session.query(models.Comment).count()
        finally:
            session.close()

        retention.prune_aged_feeds()

        session = models.Session()

        try:
            after_comments = session.query(models.Comment).count()
            rolled = session.query(models.CommentDailyTotal).count()
        finally:
            session.close()

        # Guard the guard: if nothing was deleted and rolled up, the
        # comparison below proves nothing
        self.assertTrue(rolled > 0, 'no comments were rolled up')
        self.assertTrue(after_comments < before_comments,
            'no comments were deleted, so the rollup paths were not exercised')

        after = self._capture(urls)
        changed = [u.rsplit('/', 1)[1] for u in urls if after[u] != before[u]]

        self.assertEqual(changed, [], 'changed across prune: %s' % changed)

    def test_windowed_periods_are_untouched(self):
        self._seed_prunable_comments()

        urls = ['/api/hacker_news/stats/%s/%s' % (p, e)
                for p in ('hour', 'day', 'week') for e in self.ENDPOINTS]
        before = self._capture(urls)

        retention.prune_aged_feeds()

        after = self._capture(urls)
        changed = [u for u in urls if after[u] != before[u]]

        self.assertEqual(changed, [], 'changed across prune: %s' % changed)
