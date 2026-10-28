import json
import os
import requests
import time

from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from flask import abort, jsonify, make_response, request
from sqlalchemy import desc, literal_column, text
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func
from urllib.parse import urlparse

from hacker_news import models

REQUEST_TIMEOUT = 15
REQUEST_ATTEMPTS = 3
RETRY_BACKOFF = 1
FETCH_WORKERS = 16
POST_COUNT = 90
FIREBASE_URL = 'https://hacker-news.firebaseio.com/v0/'
USER_AGENT = ('hacker_news_scrape '
    '(+https://github.com/estherh5/hacker_news_scrape)')
MAX_RESULT_COUNT = 100

# The only SQL ever formatted into a text() query. Callers pass a key, never
# the SQL itself, so an unknown key is a KeyError rather than a new query.
USER_ORDERS = {
    'comment_count': 'comment_count',
    'word_count': 'word_count',
}
POST_ORDERS = {
    'comment_count': 'comment_count DESC',
    'point_count': 'point_count DESC',
    # Ascending: rank 1 is the top of the front page
    'feed_rank': 'feed_rank, point_count DESC',
}
AVERAGES = {
    'comment_count': {
        'rollup': 'feed_summary', 'rollup_sum': 'sum_comment_count',
        'rollup_count': 'post_row_count', 'live': 'feed_post',
        'live_column': 'comment_count',
    },
    'comment_tree_depth': {
        'rollup': 'comment_daily_total', 'rollup_sum': 'sum_level',
        'rollup_count': 'comment_count', 'live': 'comment',
        'live_column': 'level',
    },
    'comment_word_count': {
        'rollup': 'comment_daily_total', 'rollup_sum': 'sum_word_count',
        'rollup_count': 'comment_count', 'live': 'comment',
        'live_column': 'total_word_count',
    },
    'point_count': {
        'rollup': 'feed_summary', 'rollup_sum': 'sum_point_count',
        'rollup_count': 'post_row_count', 'live': 'feed_post',
        'live_column': 'point_count',
    },
}


def get_count(default):
    raw_count = request.args.get('count')
    if raw_count is None:
        return default

    try:
        count = int(raw_count)
    except (TypeError, ValueError):
        count = None

    if count is None or not 1 <= count <= MAX_RESULT_COUNT:
        abort(
            400,
            description=(
                f'count must be an integer between 1 and {MAX_RESULT_COUNT}'
            ),
        )
    return count


def serialize_query(query, session):
    try:
        return [dict(row._mapping) for row in query.all()]
    finally:
        session.close()


def has_database():
    return models.engine is not None


def fetch_item(item_id, session=None):
    """Fetch one item from the Hacker News Firebase API.

    Returns the item dict, or None when the API answers null (an item that
    does not exist). Connection errors, timeouts and 5xx responses are
    retried with backoff; anything else raises.
    """
    session = session or requests.Session()

    url = FIREBASE_URL + 'item/' + str(item_id) + '.json'

    return _get_json(url, session)


def _get_json(url, session):
    for attempt in range(REQUEST_ATTEMPTS):
        try:
            response = session.get(
                url, headers={'User-Agent': USER_AGENT},
                timeout=REQUEST_TIMEOUT)

            if response.status_code >= 500:
                raise requests.HTTPError(
                    str(response.status_code) + ' from ' + url)

            response.raise_for_status()

            return response.json()

        except (requests.ConnectionError, requests.Timeout,
                requests.HTTPError):
            if attempt == REQUEST_ATTEMPTS - 1:
                raise

            time.sleep(RETRY_BACKOFF * 2 ** attempt)


def fetch_snapshot():
    """Fetch the first three pages of the front page with all comments.

    Returns one dict per post, in rank order: {'rank', 'item', 'comments'},
    where 'comments' lists (item, level, parent_id, rank) depth-first,
    pre-order, following each item's kids order. parent_id is None when the
    parent is the post itself.
    """
    session = requests.Session()

    ids = _get_json(FIREBASE_URL + 'topstories.json', session) or []

    ids = ids[:POST_COUNT]

    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        def fetch(item_id):
            return item_id, fetch_item(item_id, session)

        posts = []

        for rank, (item_id, item) in enumerate(pool.map(fetch, ids), 1):
            # A null or deleted post has no title or link to store
            if item and not item.get('deleted'):
                posts.append({'rank': rank, 'item': item, 'comments': []})

        # Walk every post's comment tree one depth at a time, fetching each
        # depth concurrently across all posts
        items = {}

        frontier = [(post['item']['id'], kid) for post in posts
            for kid in post['item'].get('kids', [])]

        while frontier:
            results = pool.map(fetch, [kid for _, kid in frontier])

            next_frontier = []

            for (_, kid), (_, item) in zip(frontier, results):
                if item:
                    items[kid] = item

                    next_frontier.extend(
                        (kid, child) for child in item.get('kids', []))

            frontier = next_frontier

    for post in posts:
        post_id = post['item']['id']

        # Iterative pre-order walk, so a deep thread cannot hit the recursion
        # limit. Kids are pushed reversed to pop in their original order.
        stack = [(kid, 0, None)
            for kid in reversed(post['item'].get('kids', []))]

        while stack:
            kid, level, parent_id = stack.pop()

            item = items.get(kid)

            if not item:
                continue

            post['comments'].append(
                (item, level, parent_id, len(post['comments']) + 1))

            stack.extend((child, level + 1, kid)
                for child in reversed(item.get('kids', [])))

    return posts


def to_utc(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).replace(
        tzinfo=None)


def has_text(item):
    return bool(item.get('text')) and not (
        item.get('deleted') or item.get('dead'))


def comment_text(item):
    if item.get('dead'):
        return '[flagged]'

    if not has_text(item):
        return '[deleted]'

    soup = BeautifulSoup(item['text'], 'html.parser')

    # HN separates paragraphs with bare <p> tags; without a break the last
    # word of one paragraph fuses with the first of the next
    for paragraph in soup.find_all('p'):
        paragraph.insert_before('\n')

    return soup.get_text().strip()


def post_type(item):
    title = item.get('title', '')

    if item.get('type') == 'job':
        return 'job'

    if 'Show HN:' in title:
        return 'show'

    if 'Ask HN:' in title:
        return 'ask'

    return 'article'


def scrape_loop():
    # Fetch everything before touching the database, so a failed fetch leaves
    # no feed behind
    snapshot = fetch_snapshot()

    session = models.Session()

    try:
        new_feed = models.Feed()

        session.add(new_feed)

        session.flush()

        feed_id = new_feed.id

        post_ids = [post['item']['id'] for post in snapshot]

        comment_ids = [item['id'] for post in snapshot
            for item, _, _, _ in post['comments']]

        # One existence check per table
        existing_posts = set(row[0] for row in session.execute(
            text('SELECT id FROM post WHERE id = ANY(:ids)'),
            {'ids': post_ids}))

        existing_comments = set(row[0] for row in session.execute(
            text('SELECT id FROM comment WHERE id = ANY(:ids)'),
            {'ids': comment_ids}))

        new_comments = []

        feed_comments = []

        for post in snapshot:
            item = post['item']

            post_id = item['id']

            if post_id not in existing_posts:
                url = item.get('url')

                session.add(models.Post(
                    created=to_utc(item['time']), id=post_id,
                    link=url or 'item?id=' + str(post_id),
                    title=item['title'], type=post_type(item),
                    username=item.get('by', ''),
                    website=(urlparse(url).hostname or '').removeprefix(
                    'www.') if url else ''))

            session.add(models.FeedPost(
                comment_count=item.get('descendants', 0), feed_id=feed_id,
                feed_rank=post['rank'], point_count=item.get('score', 0),
                post_id=post_id))

            for comment, level, parent_id, rank in post['comments']:
                comment_id = comment['id']

                if comment_id not in existing_comments:
                    content = comment_text(comment)

                    new_comments.append({
                        'id': comment_id, 'content': content,
                        'created': to_utc(comment['time']), 'level': level,
                        'parent_comment': parent_id, 'post_id': post_id,
                        'total_word_count': (
                            len(content.split()) if has_text(comment) else 0),
                        'username': comment.get('by', ''),
                    })

                feed_comments.append(models.FeedComment(
                    comment_id=comment_id, feed_id=feed_id, feed_rank=rank))

        # Posts must exist before their comments, and comments before their
        # feed links, which are only added once the comments are in
        session.flush()

        if new_comments:
            # Pre-order keeps each parent ahead of its children. word_counts
            # is NOT NULL, so insert an empty vector and fill them all in with
            # the single UPDATE below. Deleted and flagged placeholders keep
            # the empty vector, so '[deleted]' never counts as a word.
            session.execute(
                models.Comment.__table__.insert().values(
                    word_counts=literal_column("''::tsvector")),
                new_comments)

            session.execute(text(
                "UPDATE comment SET word_counts = "
                "to_tsvector('simple_english', lower(content)) "
                "WHERE id = ANY(:new_ids)"),
                {'new_ids': [comment['id'] for comment in new_comments
                    if comment['total_word_count']]})

        session.add_all(feed_comments)

        session.commit()

    except Exception:
        session.rollback()

        raise

    finally:
        session.close()

    print('Scrape completed for first three pages of Hacker News.')

    return feed_id


def get_comment(comment_id):
    # Connect to database
    session = models.Session()

    # Get comment from database
    try:
        comment = session.query(models.Comment).with_entities(
            models.Comment.content, models.Comment.created,
            models.Comment.level, models.Comment.parent_comment,
            models.Comment.post_id, models.Comment.username,
            models.FeedComment.feed_rank).join(models.FeedComment).filter(
            models.Comment.id == comment_id).order_by(
            models.FeedComment.feed_id.desc()).limit(1).one()

        session.close()

        return jsonify(comment._asdict())

    # Return error if comment not returned from query
    except NoResultFound:
        session.close()

        return make_response('Comment not found', 404)


def get_post(post_id):
    # Connect to database
    session = models.Session()

    # Get post from database
    try:
        post = session.query(models.Post).with_entities(models.Post.created,
            models.Post.link, models.Post.title, models.Post.type,
            models.Post.username, models.Post.website,
            models.FeedPost.comment_count, models.FeedPost.feed_rank,
            models.FeedPost.point_count).join(models.FeedPost).filter(
            models.Post.id == post_id).order_by(
            models.FeedPost.feed_id.desc()).limit(1).one()

        session.close()

        return jsonify(post._asdict())

    # Return error if post not returned from query
    except NoResultFound:
        session.close()

        return make_response('Post not found', 404)


def get_feeds(time_period):
    # Return time period if there is no database connection
    if not has_database():
        return time_period

    session = models.Session()

    try:
        if time_period == 'all':
            return None

        if time_period == 'hour':
            rows = session.query(models.Feed.id).order_by(
                models.Feed.created.desc()
            ).limit(1).all()
        else:
            days = 1 if time_period == 'day' else 7
            cutoff = (
                datetime.now(timezone.utc).replace(tzinfo=None) -
                timedelta(days=days)
            )
            rows = session.query(models.Feed.id).filter(
                models.Feed.created >= cutoff
            ).all()

        if not rows:
            rows = session.query(models.Feed.id).order_by(
                models.Feed.created.desc()
            ).limit(1).all()

        return [row.id for row in rows]
    finally:
        session.close()


def all_period_post(session, post_id):
    """One post's details plus its best per-feed numbers over all history.

    Deliberately omits website: the deepest-tree endpoint never returned it.
    """
    worst_rank = 2147483647

    row = session.execute(
        text("""
            SELECT p.created, p.id, p.link, p.title, p.type, p.username,
                   GREATEST(COALESCE(ps.max_comment_count, 0),
                            COALESCE(MAX(fp.comment_count), 0)
                           ) AS comment_count,
                   LEAST(COALESCE(ps.best_feed_rank, :worst),
                         COALESCE(MIN(fp.feed_rank), :worst)
                        ) AS feed_rank,
                   GREATEST(COALESCE(ps.max_point_count, 0),
                            COALESCE(MAX(fp.point_count), 0)
                           ) AS point_count
              FROM post p
                   LEFT JOIN post_stat ps ON ps.post_id = p.id
                   LEFT JOIN feed_post fp ON fp.post_id = p.id
             WHERE p.id = :post_id
          GROUP BY p.id, ps.max_comment_count, ps.max_point_count,
                   ps.best_feed_rank
        """), {'post_id': post_id, 'worst': worst_rank}).one()

    return dict(row._mapping)


def all_period_users(session, order, count):
    """Per-user comment totals over all history.

    user_total holds deleted comments, the live comment table holds the rest,
    and the two never overlap -- a comment reaches user_total only as it is
    deleted. Summing the union is therefore exact.
    """
    try:
        rows = session.execute(
            text("""
                SELECT username,
                       SUM(comment_count)::int AS comment_count,
                       SUM(word_count)::int AS word_count
                  FROM (SELECT username, comment_count, word_count
                          FROM user_total
                         UNION ALL
                        SELECT username, 1, total_word_count
                          FROM comment
                         WHERE username != ''
                       ) merged
              GROUP BY username
              ORDER BY SUM({order}) DESC
                 LIMIT :count
            """.format(order=USER_ORDERS[order])),
            {'count': count}).fetchall()

        return [dict(row._mapping) for row in rows]
    finally:
        session.close()


def all_period_posts(session, order, count):
    """Ranked posts over all history.

    Posts are never pruned, so titles and links always come from the live
    post table. Their per-feed numbers come from post_stat for pruned feeds
    and from the surviving feed_post rows for the rest, taking the better
    value of the two.

    One deliberate difference from the pre-rollup query: that one picked the
    single feed_post row with the highest count and reported that row's rank
    alongside it. post_stat keeps per-column extremes instead, so feed_rank is
    the best rank the post ever reached rather than its rank at peak comment
    count. For a post that climbed and then accumulated comments those are
    different rows. Best-ever rank is the more useful of the two, and it is
    what top_posts already wants.
    """
    # Rank 1 is the top of the front page, so a missing rank must lose every
    # comparison rather than win it
    worst_rank = 2147483647

    try:
        rows = session.execute(
            text("""
            SELECT p.created, p.id, p.link, p.title, p.type, p.username,
                   p.website,
                   GREATEST(COALESCE(ps.max_comment_count, 0),
                            COALESCE(MAX(fp.comment_count), 0)
                           ) AS comment_count,
                   GREATEST(COALESCE(ps.max_point_count, 0),
                            COALESCE(MAX(fp.point_count), 0)
                           ) AS point_count,
                   LEAST(COALESCE(ps.best_feed_rank, :worst),
                         COALESCE(MIN(fp.feed_rank), :worst)
                        ) AS feed_rank
              FROM post p
                   LEFT JOIN post_stat ps ON ps.post_id = p.id
                   LEFT JOIN feed_post fp ON fp.post_id = p.id
          GROUP BY p.id, ps.post_id, ps.max_comment_count, ps.max_point_count,
                   ps.best_feed_rank
            -- The pre-rollup query inner-joined feed_post, so a post that
            -- never appeared in a feed was excluded. Keep that.
            HAVING ps.post_id IS NOT NULL OR COUNT(fp.post_id) > 0
          ORDER BY {order}
             LIMIT :count
        """.format(order=POST_ORDERS[order])),
        {'count': count, 'worst': worst_rank}).fetchall()

        return [dict(row._mapping) for row in rows]
    finally:
        session.close()


def all_period_average(session, metric):
    """Average over all history: pruned rows from a rollup, the rest live.

    The two halves never overlap. A row is counted in the rollup only once it
    has been deleted from the live table, so adding them is exact rather than
    approximate.

    Returns a Decimal, so the caller's round() keeps the banker's rounding the
    plain func.avg() version used. Rounding in SQL instead would switch to
    half-up and shift results on exact .5 values.
    """
    row = session.execute(
        text("""
            SELECT (COALESCE((SELECT sum({rollup_sum}) FROM {rollup}), 0)
                    + COALESCE((SELECT sum({live_column}) FROM {live}), 0)
                   )::numeric
                   / NULLIF(COALESCE((SELECT sum({rollup_count})
                                        FROM {rollup}), 0)
                            + (SELECT count(*) FROM {live}), 0) AS average
        """.format(**AVERAGES[metric]))).one()

    return row.average if row.average is not None else 0


def get_average_comment_count(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average comment count, filtering by feed_ids if specified
    if feed_ids is not None:
        raw_average = session.query(
            func.avg(models.FeedPost.comment_count)).filter(
            models.FeedPost.feed_id.in_(feed_ids)).one()[0]
        average = round(raw_average) if raw_average is not None else 0

    else:
        average = round(all_period_average(session, 'comment_count'))

    session.close()

    return jsonify(average)


def get_average_comment_tree_depth(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average comment level, filtering by feed_ids if specified
    if feed_ids is not None:
        raw_average = session.query(func.avg(models.Comment.level)).join(
            models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).one()[0]
        average = round(raw_average) if raw_average is not None else 0

    else:
        average = round(all_period_average(session, 'comment_tree_depth'))

    session.close()

    return jsonify(average)


def get_average_comment_word_count(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average comment word count, filtering by feed_ids if specified
    if feed_ids is not None:
        raw_average = session.query(func.avg(
            models.Comment.total_word_count)).join(models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).one()[0]
        average = round(raw_average) if raw_average is not None else 0

    else:
        average = round(all_period_average(session, 'comment_word_count'))

    session.close()

    return jsonify(average)


def get_average_point_count(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average post point count, filtering by feed_ids if specified
    if feed_ids is not None:
        raw_average = session.query(func.avg(
            models.FeedPost.point_count)).filter(
            models.FeedPost.feed_id.in_(feed_ids)).one()[0]
        average = round(raw_average) if raw_average is not None else 0

    else:
        average = round(all_period_average(session, 'point_count'))

    session.close()

    return jsonify(average)


def get_comments_with_highest_word_counts(feed_ids):
    # Get number of requested comments from query parameter, using default if
    # null
    count = get_count(5)

    # Connect to database
    session = models.Session()

    # Get comments with highest word counts, filtering by feed_ids if specified
    if feed_ids is not None:
        subquery = session.query(models.Comment).with_entities(
            models.Comment.content, models.Comment.created, models.Comment.id,
            models.Comment.level, models.Comment.parent_comment,
            models.Comment.post_id, models.Comment.username,
            models.Comment.total_word_count).join(models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).order_by(
            models.Comment.id,
            models.Comment.total_word_count.desc()).distinct(
            models.Comment.id).subquery()

        query = session.query(subquery).order_by(
            subquery.columns.get('total_word_count').desc()).limit(count)

    else:
        query = session.query(models.Comment).with_entities(
            models.Comment.content, models.Comment.created, models.Comment.id,
            models.Comment.level, models.Comment.parent_comment,
            models.Comment.post_id, models.Comment.username,
            models.Comment.total_word_count).order_by(
            models.Comment.total_word_count.desc()).limit(count)

    return jsonify(serialize_query(query, session))


def get_most_frequent_comment_words(feed_ids):
    count = get_count(50)

    # Return sample data if there is no database connection
    if not has_database():
        with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) +
            '/sample_data/' + feed_ids + '_comment_words.json',
            'r') as sample_data:
                return jsonify(json.load(sample_data)[:count])

    # Connect to database
    session = models.Session()

    # Get highest frequency words used in comments, excluding stop words,
    # filtering by feed_ids if specified
    if feed_ids is not None:
        query = session.execute(
            text("""
              SELECT *
                FROM ts_stat(
                     $$SELECT word_counts
                         FROM (
                                 SELECT DISTINCT ON (id)
                                        id, feed_id, word_counts
                                   FROM comment
                                        JOIN feed_comment
                                          ON feed_comment.comment_id =
                                             comment.id
                                  WHERE feed_id = ANY(:feed_id)
                               ORDER BY id, word_counts DESC
                         ) comment_table$$
                )
               WHERE LENGTH (word) > 1
            ORDER BY nentry DESC
               LIMIT :count;
            """),
            {'feed_id': feed_ids,
            'count': count}
            ).fetchall()

    else:
        # word_total holds the words of deleted comments, ts_stat covers the
        # ones still live. A comment is in exactly one of the two, never both.
        query = session.execute(
            text("""
              SELECT word, SUM(ndoc)::int AS ndoc, SUM(nentry)::int AS nentry
                FROM (SELECT word, ndoc, nentry FROM word_total
                       UNION ALL
                      SELECT word, ndoc, nentry
                        FROM ts_stat($$SELECT word_counts FROM comment$$)
                     ) merged
               WHERE LENGTH (word) > 1
            GROUP BY word
            ORDER BY SUM(nentry) DESC
               LIMIT :count;
            """),
            {'count': count}
            ).fetchall()

    session.close()

    words = []

    for row in query:
        words.append(dict(row._mapping))

    return jsonify(words)


def deepest_comment_and_post(session, feed_ids):
    """The deepest comment and its post, or (None, None) if there is neither.

    Every lookup here uses one_or_none() rather than one(). A period whose
    feeds hold no comments, and a comment whose post appears in none of those
    feeds, are both empty results rather than errors; one() raises
    NoResultFound, which reaches the client as a 500.
    """
    if feed_ids is None:
        comment = session.query(models.Comment).with_entities(
            models.Comment.content, models.Comment.created, models.Comment.id,
            models.Comment.level, models.Comment.parent_comment,
            models.Comment.post_id, models.Comment.username).order_by(
            models.Comment.level.desc()).limit(1).one_or_none()

        if comment is None:
            return None, None

        comment = comment._asdict()

        # Get post information. The pre-rollup query read the most recent
        # feed_post row for this post; those rows are pruned, so the numbers
        # come from post_stat and any surviving rows instead.
        #
        # comment.post_id is NOT NULL and foreign-keyed to post, so the post
        # row is guaranteed to exist and all_period_post's one() is safe.
        return comment, all_period_post(session, comment['post_id'])

    subquery = session.query(models.Comment).with_entities(
        models.Comment.content, models.Comment.created, models.Comment.id,
        models.Comment.level, models.Comment.parent_comment,
        models.Comment.post_id, models.Comment.username).join(
        models.FeedComment).filter(
        models.FeedComment.feed_id.in_(feed_ids)).order_by(
        models.Comment.id, models.Comment.level.desc()).distinct(
        models.Comment.id).subquery()

    comment = session.query(subquery).order_by(
        subquery.columns.get('level').desc()).limit(1).one_or_none()

    if comment is None:
        return None, None

    # Get post information. Comments and posts are pruned on separate
    # schedules, so a comment can outlive its post's feed_post rows.
    post = session.query(models.Post).with_entities(models.Post.created,
        models.Post.id, models.Post.link, models.Post.title,
        models.Post.type, models.Post.username,
        models.FeedPost.comment_count, models.FeedPost.feed_rank,
        models.FeedPost.point_count).join(models.FeedPost).filter(
        models.Post.id == comment.post_id).filter(
        models.FeedPost.feed_id.in_(feed_ids)).order_by(
        models.FeedPost.post_id.desc()).limit(1).one_or_none()

    if post is None:
        return None, None

    return comment._asdict(), post._asdict()


def get_deepest_comment_tree(feed_ids):
    # Connect to database
    session = models.Session()

    # Get highest level comment (deepest in comment tree), filtering by
    # feed_ids if specified
    comment, post = deepest_comment_and_post(session, feed_ids)

    # An empty period has no deepest tree to report. Answer 200 with an empty
    # object rather than raising, matching the 0 the average endpoints return.
    if comment is None:
        session.close()

        return jsonify({})

    comment.pop('post_id')
    comment.pop('level')

    # Get parent comments of comment to get full comment tree
    while comment['parent_comment']:
        parent_comment = session.query(models.Comment).with_entities(
            models.Comment.content, models.Comment.created,
            models.Comment.id, models.Comment.parent_comment,
            models.Comment.username).filter(
            models.Comment.id == comment['parent_comment']).one()._asdict()

        comment.pop('parent_comment')

        # Set comment as child of parent
        parent_comment['child_comment'] = comment

        # Set next comment as current parent comment
        comment = parent_comment

    comment.pop('parent_comment')

    post['comment_tree'] = comment

    session.close()

    return jsonify(post)


def get_posts_with_highest_comment_counts(feed_ids):
    count = get_count(5)

    # Return sample data if there is no database connection
    if not has_database():
        with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) +
            '/sample_data/' + feed_ids + '_posts_highest_comment_count.json',
            'r') as sample_data:
                return jsonify(json.load(sample_data)[:count])

    # Connect to database
    session = models.Session()

    # Get posts with highest comment counts, filtering by feed_ids if specified
    if feed_ids is not None:
        subquery = session.query(models.Post).with_entities(
            models.Post.created, models.Post.id, models.Post.link,
            models.Post.title, models.Post.type, models.Post.username,
            models.Post.website, models.FeedPost.comment_count,
            models.FeedPost.feed_rank, models.FeedPost.point_count).join(
            models.FeedPost).filter(
            models.FeedPost.feed_id.in_(feed_ids)).order_by(
            models.Post.id, models.FeedPost.comment_count.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).order_by(
            subquery.columns.get('comment_count').desc()).limit(count)

    else:
        return jsonify(all_period_posts(session, 'comment_count', count))

    return jsonify(serialize_query(query, session))


def get_posts_with_highest_point_counts(feed_ids):
    # Get number of requested posts from query parameter, using default if
    # null
    count = get_count(5)

    # Connect to database
    session = models.Session()

    # Get posts with highest point counts, filtering by feed_ids if specified
    if feed_ids is not None:
        subquery = session.query(models.Post).with_entities(
            models.Post.created, models.Post.id, models.Post.link,
            models.Post.title, models.Post.type, models.Post.username,
            models.Post.website, models.FeedPost.comment_count,
            models.FeedPost.feed_rank, models.FeedPost.point_count).join(
            models.FeedPost).filter(
            models.FeedPost.feed_id.in_(feed_ids)).order_by(
            models.Post.id, models.FeedPost.point_count.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).order_by(
            subquery.columns.get('point_count').desc()).limit(count)

    else:
        return jsonify(all_period_posts(session, 'point_count', count))

    return jsonify(serialize_query(query, session))


def get_post_types(feed_ids):
    # Return sample data if there is no database connection
    if not has_database():
        with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) +
            '/sample_data/' + feed_ids + '_post_types.json',
            'r') as sample_data:
                return jsonify(json.load(sample_data))

    # Otherwise, connect to database
    session = models.Session()

    # Get count of types of posts ('article' vs. 'ask' vs. 'job' vs. 'show'),
    # filtering by feed_ids if specified
    if feed_ids is not None:
        subquery = session.query(models.Post).with_entities(
            models.Post.id, models.Post.type).join(
            models.FeedPost).filter(
            models.FeedPost.feed_id.in_(feed_ids)).order_by(
            models.Post.id, models.FeedPost.feed_id.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('type'),
            func.count('*').label("type_count")).group_by(
            subquery.columns.get('type')).order_by(desc('type_count'))

    else:
        subquery = session.query(models.Post).with_entities(
            models.Post.id, models.Post.type).subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('type'),
            func.count('*').label("type_count")).group_by(
            subquery.columns.get('type')).order_by(desc('type_count'))

    return jsonify(serialize_query(query, session))


def get_most_frequent_title_words(feed_ids):
    # Get number of requested words from query parameter, using default if
    # null
    count = get_count(50)

    # Connect to database
    session = models.Session()

    # Get highest-frequency words used in post titles, excluding stop words,
    # filtering by feed_ids if specified
    if feed_ids is not None:
        query = session.execute(
            text("""
              SELECT *
                FROM ts_stat(
                     $$SELECT to_tsvector('simple_english', LOWER(title))
                         FROM (
                                 SELECT DISTINCT ON (post.id)
                                        post.id, post.title, feed_post.feed_id
                                   FROM post
                                        JOIN feed_post
                                          ON feed_post.post_id = post.id
                                  WHERE feed_id = ANY(:feed_id)
                               ORDER BY post.id, feed_post.feed_id DESC
                         ) post_table$$
                )
               WHERE word NOT IN ('ask', 'hn', 'show')
                 AND LENGTH (word) > 1
            ORDER BY nentry DESC
               LIMIT :count;
            """),
            {'feed_id': feed_ids,
            'count': count}
            ).fetchall()

    else:
        query = session.execute(
            text("""
              SELECT *
                FROM ts_stat(
                     $$SELECT to_tsvector('simple_english', LOWER(title))
                         FROM post$$
                )
               WHERE word NOT IN ('ask', 'hn', 'show')
                 AND LENGTH (word) > 1
            ORDER BY nentry DESC
               LIMIT :count;
            """),
            {'feed_id': feed_ids,
            'count': count}
            ).fetchall()

    session.close()

    words = []

    for row in query:
        words.append(dict(row._mapping))

    return jsonify(words)


def get_top_posts(feed_ids):
    # Get number of requested posts from query parameter, using default if
    # null
    count = get_count(3)

    # Connect to database
    session = models.Session()

    # Get posts in order of rank, filtering by feed_ids if specified
    if feed_ids is not None:
        subquery = session.query(models.Post).with_entities(
            models.Post.created, models.Post.id, models.Post.link,
            models.Post.title, models.Post.type, models.Post.username,
            models.Post.website, models.FeedPost.comment_count,
            models.FeedPost.feed_rank, models.FeedPost.point_count).join(
            models.FeedPost).filter(
            models.FeedPost.feed_id.in_(feed_ids)).order_by(
            models.Post.id, models.FeedPost.feed_rank,
            models.FeedPost.point_count.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).order_by(
            subquery.columns.get('feed_rank'),
            subquery.columns.get('point_count').desc()).limit(count)

    else:
        return jsonify(all_period_posts(session, 'feed_rank', count))

    return jsonify(serialize_query(query, session))


def get_top_websites(feed_ids):
    # Get number of requested websites from query parameter, using default if
    # null
    count = get_count(5)

    # Connect to database
    session = models.Session()

    # Get websites that highest number of posts are from, filtering by feed_ids
    # if specified
    if feed_ids is not None:
        subquery = session.query(models.Post).with_entities(
            models.Post.id, models.Post.website).join(
            models.FeedPost).filter(
            models.FeedPost.feed_id.in_(feed_ids)).filter(
            models.Post.website != '').order_by(
            models.Post.id, models.FeedPost.feed_id.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('website'),
            func.count('*').label("link_count")).group_by(
            subquery.columns.get('website')).order_by(
            desc('link_count')).limit(count)

    else:
        subquery = session.query(models.Post).with_entities(
            models.Post.id, models.Post.website).filter(
            models.Post.website != '').subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('website'),
            func.count('*').label("link_count")).group_by(
            subquery.columns.get('website')).order_by(
            desc('link_count')).limit(count)

    return jsonify(serialize_query(query, session))


def get_users_with_most_comments(feed_ids):
    count = get_count(5)

    # Return sample data if there is no database connection
    if not has_database():
        with open(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) +
            '/sample_data/' + feed_ids + '_users_most_comments.json',
            'r') as sample_data:
                return jsonify(json.load(sample_data)[:count])

    # Connect to database
    session = models.Session()

    # Get users who posted the most comments, filtering by feed_ids if
    # specified
    if feed_ids is not None:
        subquery = session.query(models.Comment).with_entities(
            models.Comment.id, models.Comment.total_word_count,
            models.Comment.username).join(models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).filter(
            models.Comment.username != '').order_by(models.Comment.id,
            models.FeedComment.feed_id.desc()).distinct(
            models.Comment.id).subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('username'),
            func.count('*').label("comment_count"), func.sum(
                subquery.columns.get('total_word_count')
            ).label("word_count")).group_by(
            subquery.columns.get('username')).order_by(
            desc('comment_count')).limit(count)

    else:
        return jsonify(all_period_users(session, 'comment_count', count))

    return jsonify(serialize_query(query, session))


def get_users_with_most_posts(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = get_count(5)

    # Connect to database
    session = models.Session()

    # Get users who posted the most posts, filtering by feed_ids if specified
    if feed_ids is not None:
        subquery = session.query(models.Post).with_entities(
            models.Post.id, models.Post.username).join(models.FeedPost).filter(
            models.FeedPost.feed_id.in_(feed_ids)).filter(
            models.Post.username != '').order_by(models.Post.id,
            models.FeedPost.feed_id.desc()).distinct(models.Post.id).subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('username'),
            func.count('*').label("post_count")).group_by(
            subquery.columns.get('username')).order_by(
            desc('post_count')).limit(count)

    else:
        subquery = session.query(models.Post).with_entities(
            models.Post.id, models.Post.username).filter(
            models.Post.username != '').subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('username'),
            func.count('*').label("post_count")).group_by(
            subquery.columns.get('username')).order_by(
            desc('post_count')).limit(count)

    return jsonify(serialize_query(query, session))


def get_users_with_most_words_in_comments(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = get_count(5)

    # Connect to database
    session = models.Session()

    # Get users who posted the most words in comments, filtering by feed_ids if
    # specified
    if feed_ids is not None:
        subquery = session.query(models.Comment).with_entities(
            models.Comment.id, models.Comment.total_word_count,
            models.Comment.username).join(models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).filter(
            models.Comment.username != '').order_by(models.Comment.id,
            models.FeedComment.feed_id.desc()).distinct(
            models.Comment.id).subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('username'),
            func.count('*').label("comment_count"), func.sum(
                subquery.columns.get('total_word_count')
            ).label("word_count")).group_by(
            subquery.columns.get('username')).order_by(
            desc('word_count')).limit(count)

    else:
        return jsonify(all_period_users(session, 'word_count', count))

    return jsonify(serialize_query(query, session))
