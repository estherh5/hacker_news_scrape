"""Rollup and retention for the Hacker News archive.

Raw comments and feed links are held to a rolling window; everything older is
folded into the rollup tables and deleted, so storage plateaus instead of
growing indefinitely. The 'all' time period is answered from the rollups plus
whatever is still inside the window.

The load-bearing rule is what a fact is attached to:

  * Feed-scoped facts (feed_post rows) roll up when that feed ages out.
  * Comment-scoped facts roll up when that comment is deleted.

A comment appears in roughly thirteen feeds, so rolling comment facts up
per-feed would count each comment about thirteen times and inflate every
all-time average accordingly.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert

from hacker_news import hacker_news, models

# Raw comments and feed links are kept for this many days. The stats API's
# longest window is 'week' (7 days); the extra day is slack.
RETENTION_DAYS = 8


def merge_feed_rollups(session, feed_id):
    """Fold one feed's feed_post rows into feed_summary and post_stat.

    Feed-scoped facts only. Comment-scoped facts belong in
    merge_comment_rollups, which runs once per comment at deletion time.

    The accumulation below is not idempotent on its own. Correctness comes
    from the caller running this exactly once per feed, inside the same
    transaction that sets feed.rolled_up.
    """
    totals = session.query(
        func.count().label('post_row_count'),
        func.coalesce(func.sum(models.FeedPost.point_count), 0).label('points'),
        func.coalesce(
            func.sum(models.FeedPost.comment_count), 0).label('comments'),
    ).filter(models.FeedPost.feed_id == feed_id).one()

    session.execute(
        insert(models.FeedSummary).values(
            feed_id=feed_id,
            post_row_count=totals.post_row_count,
            sum_point_count=totals.points,
            sum_comment_count=totals.comments,
        ).on_conflict_do_update(
            index_elements=['feed_id'],
            set_={
                'post_row_count':
                    models.FeedSummary.post_row_count + totals.post_row_count,
                'sum_point_count':
                    models.FeedSummary.sum_point_count + totals.points,
                'sum_comment_count':
                    models.FeedSummary.sum_comment_count + totals.comments,
            },
        )
    )

    rows = session.query(models.FeedPost).filter(
        models.FeedPost.feed_id == feed_id).all()

    for row in rows:
        session.execute(
            insert(models.PostStat).values(
                post_id=row.post_id,
                max_comment_count=row.comment_count,
                max_point_count=row.point_count,
                best_feed_rank=row.feed_rank,
            ).on_conflict_do_update(
                index_elements=['post_id'],
                set_={
                    'max_comment_count': func.greatest(
                        models.PostStat.max_comment_count, row.comment_count),
                    'max_point_count': func.greatest(
                        models.PostStat.max_point_count, row.point_count),
                    # Rank 1 is the top of the front page, so best is lowest
                    'best_feed_rank': func.least(
                        models.PostStat.best_feed_rank, row.feed_rank),
                },
            )
        )


def merge_comment_rollups(session, comment_ids):
    """Fold comments into word_total, user_total and comment_daily_total.

    Call this exactly once per comment, at the moment it is deleted -- never
    when a feed it appears in ages out. A comment appears in roughly thirteen
    feeds, so per-feed accumulation would count it thirteen times.

    Like merge_feed_rollups, the accumulation is not idempotent on its own.
    """
    comment_ids = list(comment_ids)

    if not comment_ids:
        return

    # ts_stat takes its query as a SQL string literal, so comment ids cannot
    # be bound inside it. A temporary table keeps them out of that string
    # entirely rather than interpolating them into it.
    session.execute(text('CREATE TEMPORARY TABLE pruning_comment '
        '(id integer PRIMARY KEY)'))

    session.execute(
        text('INSERT INTO pruning_comment (id) '
             'SELECT unnest(CAST(:ids AS integer[]))'),
        {'ids': comment_ids})

    try:
        session.execute(text("""
            INSERT INTO comment_daily_total AS t
                        (day, comment_count, sum_level, sum_word_count)
                 SELECT c.created::date, count(*), sum(c.level),
                        sum(c.total_word_count)
                   FROM comment c
                        JOIN pruning_comment p ON p.id = c.id
               GROUP BY c.created::date
            ON CONFLICT (day) DO UPDATE
                    SET comment_count = t.comment_count +
                                        EXCLUDED.comment_count,
                        sum_level = t.sum_level + EXCLUDED.sum_level,
                        sum_word_count = t.sum_word_count +
                                         EXCLUDED.sum_word_count
        """))

        session.execute(text("""
            INSERT INTO user_total AS t (username, comment_count, word_count)
                 SELECT c.username, count(*), sum(c.total_word_count)
                   FROM comment c
                        JOIN pruning_comment p ON p.id = c.id
                  WHERE c.username != ''
               GROUP BY c.username
            ON CONFLICT (username) DO UPDATE
                    SET comment_count = t.comment_count +
                                        EXCLUDED.comment_count,
                        word_count = t.word_count + EXCLUDED.word_count
        """))

        # Words are stored unfiltered; LENGTH(word) > 1 is applied at read
        # time so it tracks whatever the endpoint does
        session.execute(text("""
            INSERT INTO word_total AS t (word, ndoc, nentry)
                 SELECT word, ndoc, nentry
                   FROM ts_stat(
                        $$SELECT c.word_counts
                            FROM comment c
                                 JOIN pruning_comment p ON p.id = c.id$$
                        )
            ON CONFLICT (word) DO UPDATE
                    SET ndoc = t.ndoc + EXCLUDED.ndoc,
                        nentry = t.nentry + EXCLUDED.nentry
        """))
    finally:
        session.execute(text('DROP TABLE pruning_comment'))


def update_pins(session, comment_ids):
    """Pin all-time record holders so they survive pruning.

    Returns the set of comment ids that must NOT be deleted.

    Two endpoints return raw comment text for the 'all' period --
    comments_highest_word_count and deepest_comment_tree. Without pins they
    would silently degrade to whatever happens to be inside the retention
    window.
    """
    comment_ids = list(comment_ids)

    if not comment_ids:
        return set()

    # Pin count tracks MAX_RESULT_COUNT rather than a literal: the endpoint
    # accepts ?count= up to that, so pinning fewer would return a short list
    limit = hacker_news.MAX_RESULT_COUNT

    session.execute(
        text("""
            INSERT INTO pinned_comment (comment_id, reason)
                 SELECT id, 'word_count'
                   FROM comment
                  WHERE id = ANY(CAST(:ids AS integer[]))
               ORDER BY total_word_count DESC
                  LIMIT :limit
            ON CONFLICT (comment_id) DO NOTHING
        """),
        {'ids': comment_ids, 'limit': limit})

    # Drop word_count pins displaced by longer comments. Pins added for the
    # deepest tree are left alone -- they are held for a different reason.
    session.execute(
        text("""
            DELETE FROM pinned_comment
                  WHERE reason = 'word_count'
                    AND comment_id NOT IN (
                        SELECT p.comment_id
                          FROM pinned_comment p
                               JOIN comment c ON c.id = p.comment_id
                         WHERE p.reason = 'word_count'
                      ORDER BY c.total_word_count DESC
                         LIMIT :limit)
        """),
        {'limit': limit})

    # The deepest comment plus every ancestor, or the tree cannot render
    session.execute(
        text("""
            WITH RECURSIVE deepest AS (
                SELECT id, parent_comment
                  FROM comment
                 WHERE id = ANY(CAST(:ids AS integer[]))
              ORDER BY level DESC
                 LIMIT 1
            ), chain AS (
                SELECT id, parent_comment FROM deepest
                 UNION ALL
                SELECT c.id, c.parent_comment
                  FROM comment c
                       JOIN chain ON chain.parent_comment = c.id
            )
            INSERT INTO pinned_comment (comment_id, reason)
                 SELECT id, 'deepest_tree' FROM chain
            ON CONFLICT (comment_id) DO NOTHING
        """),
        {'ids': comment_ids})

    rows = session.execute(
        text('SELECT comment_id FROM pinned_comment')).fetchall()

    return {row[0] for row in rows}


def prune_aged_feeds(now=None):
    """Roll up and delete every feed older than RETENTION_DAYS.

    One transaction per feed. The merges are += accumulations and are NOT
    idempotent on their own -- setting feed.rolled_up inside the same
    transaction is what makes this exactly-once. Never split them.

    Returns the number of feeds pruned.
    """
    if now is None:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

    cutoff = now - timedelta(days=RETENTION_DAYS)

    session = models.Session()

    try:
        feed_ids = [row.id for row in session.query(models.Feed.id).filter(
            models.Feed.created < cutoff,
            models.Feed.rolled_up.is_(False),
        ).order_by(models.Feed.created).all()]
    finally:
        session.close()

    pruned = 0

    for feed_id in feed_ids:
        session = models.Session()

        try:
            merge_feed_rollups(session, feed_id)

            session.query(models.FeedPost).filter(
                models.FeedPost.feed_id == feed_id).delete(
                synchronize_session=False)

            session.query(models.FeedComment).filter(
                models.FeedComment.feed_id == feed_id).delete(
                synchronize_session=False)

            # Comments with no remaining link to ANY feed have fully aged out.
            # This is what lets a comment that stayed on the front page longer
            # than the window survive until its last link disappears.
            orphan_ids = [row[0] for row in session.execute(text("""
                SELECT c.id
                  FROM comment c
                 WHERE NOT EXISTS (SELECT 1 FROM feed_comment fc
                                    WHERE fc.comment_id = c.id)
            """)).fetchall()]

            if orphan_ids:
                keep = update_pins(session, orphan_ids)

                deletable = [i for i in orphan_ids if i not in keep]

                # Pinned comments stay in the raw table, so they are never
                # merged here. The 'all' queries read rollups PLUS live rows,
                # so each comment is still counted exactly once.
                merge_comment_rollups(session, deletable)

                if deletable:
                    session.query(models.Comment).filter(
                        models.Comment.id.in_(deletable)).delete(
                        synchronize_session=False)

            session.query(models.Feed).filter(
                models.Feed.id == feed_id).update(
                {'rolled_up': True}, synchronize_session=False)

            session.commit()

            pruned += 1
        except Exception:
            session.rollback()

            raise
        finally:
            session.close()

    return pruned
