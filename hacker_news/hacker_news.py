import asyncio
import os
import psycopg2 as pg
import psycopg2.extras
import requests
import time

from bs4 import BeautifulSoup
from datetime import datetime
from flask import jsonify, make_response, request


def scrape_loop():
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor()

    # Add feed to database
    cursor.execute(
        """
           INSERT INTO feed
        DEFAULT VALUES
             RETURNING id;
        """
        )

    feed_id = cursor.fetchone()[0]

    conn.commit()

    cursor.close()
    conn.close()

    # Create asynchronous tasks to scrape first three pages of Hacker News
    loop = asyncio.get_event_loop()

    tasks = [
        loop.create_task(scrape_page(1, feed_id, loop)),
        loop.create_task(scrape_page(2, feed_id, loop)),
        loop.create_task(scrape_page(3, feed_id, loop))
        ]

    wait_tasks = asyncio.wait(tasks)

    loop.run_until_complete(wait_tasks)

    loop.close()

    print('Scrape completed for first three pages of Hacker News.')

    return


async def scrape_page(page, feed_id, loop):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor()

    print('Scrape initiated for page ' + str(page) + ' of Hacker News.')

    # Current UTC time in seconds
    now = int(datetime.utcnow().strftime('%s'))

    # Get HTML tree from feed page
    feed_html = requests.get(
        'https://news.ycombinator.com/news?p=' + str(page))

    feed_content = feed_html.content

    feed_soup = BeautifulSoup(feed_content, 'html.parser')

    # Get all post rows from HTML tree
    post_rows = feed_soup.find_all('tr', 'athing')

    for post_row in post_rows:
        # Get subtext row with additional post data
        subtext_row = post_row.next_sibling

        # Get post id
        post_id = post_row.get('id')

        # Check if post already exists in database
        cursor.execute(
            """
            SELECT exists (
                           SELECT 1
                             FROM post
                            WHERE id = %(id)s
                            LIMIT 1
            );
            """,
            {'id': post_id}
            )

        # Get core post data if it is not in database already
        if not cursor.fetchone()[0]:
            # Get UTC timestamp for post's posting time by subtracting the
            # number of hours/minutes ago given on the webpage from the current
            # UTC timestamp
            time_unit = subtext_row.find('span', 'age').a.get_text().split()[1]

            if time_unit == 'hours':
                created = now - 3600 * int(subtext_row.find(
                    'span', 'age').a.get_text().split()[0])

            else:
                created = now - 60 * int(subtext_row.find(
                    'span', 'age').a.get_text().split()[0])

            created = time.strftime(
                '%Y-%m-%d %H:%M', time.localtime(created))

            # Get post's link
            link = post_row.find('a', 'storylink').get('href')

            # Get post's title
            title = post_row.find('a', 'storylink').get_text()

            # Set post's type based on title
            if 'Show HN:' in title:
                type = 'show'
            elif 'Ask HN:' in title:
                type = 'ask'
            else:
                type = 'article'

            # Get username of user who posted post or set as blank for job
            # posting
            if subtext_row.find('a', 'hnuser'):
                username = subtext_row.find('a', 'hnuser').get_text()
            else:
                username = ''

            # Get website that post is from or set as blank for ask posting
            if post_row.find('span', 'sitestr'):
                website = post_row.find('span', 'sitestr').get_text()
            else:
                website = ''

            # Add post data to database
            cursor.execute(
                """
                INSERT INTO post
                            (id, created, link, title, type, username, website)
                     VALUES (%(id)s, %(created)s, %(link)s, %(title)s,
                            %(type)s, %(username)s, %(website)s);
                """,
                {'id': post_id,
                'created': created,
                'link': link,
                'title': title,
                'type': type,
                'username': username,
                'website': website}
                )

        # Get post's rank on feed page
        feed_rank = post_row.find('span', 'rank').get_text()[:-1]

        # Get post's score if it is listed (otherwise, post is job
        # posting)
        if subtext_row.find('span', 'score'):
            point_count = subtext_row.find(
                'span', 'score').get_text().split()[0]
        else:
            point_count = 0
            type = 'job'

        # Add feed-based post data to database
        cursor.execute(
            """
            INSERT INTO feed_post
                        (feed_id, feed_rank, point_count, post_id)
                 VALUES (%(feed_id)s, %(feed_rank)s, %(point_count)s,
                        %(post_id)s);
            """,
            {'feed_id': feed_id,
            'feed_rank': feed_rank,
            'point_count': point_count,
            'post_id': post_id}
            )

        conn.commit()

        # Create asynchronous task to scrape post page for its comments
        loop.create_task(scrape_post(post_id, feed_id))

    cursor.close()
    conn.close()

    return


async def scrape_post(post_id, feed_id):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor()

    # Current UTC time in seconds
    now = int(datetime.utcnow().strftime('%s'))

    # Get HTML tree from post's webpage
    post_html = requests.get(
        'https://news.ycombinator.com/item?id=' + str(post_id))

    post_content = post_html.content

    post_soup = BeautifulSoup(post_content, 'html.parser')

    # Get all comment rows from HTML tree
    comment_rows = post_soup.select('tr.athing.comtr')

    # Set starting comment feed rank to 0
    comment_feed_rank = 0

    for comment_row in comment_rows:
        # Get comment id
        comment_id = comment_row.get('id')

        # Check if comment already exists in database
        cursor.execute(
            """
            SELECT exists (
                           SELECT 1
                             FROM comment
                            WHERE id = %(id)s
                            LIMIT 1
            );
            """,
            {'id': comment_id}
            )

        # Get core comment data if it is not in database already
        if not cursor.fetchone()[0]:
            # If comment has content span, get text from span
            if comment_row.find('div', 'comment').find_all('span'):
                comment_content = comment_row.find(
                    'div', 'comment').find_all('span')[0].get_text()

                # Remove the last word ('reply') from the comment content
                # and strip trailing whitespace
                comment_content = comment_content.rsplit(' ', 1)[0].strip()

            # Otherwise, comment is flagged, so get flagged message as text
            # and strip trailing whitespace
            else:
                comment_content = comment_row.find(
                    'div', 'comment').get_text().strip()

            # Get UTC timestamp for comment's posting time by subtracting
            # the number of hours/minutes ago given on the webpage from the
            # current UTC timestamp
            comment_time_unit = comment_row.find(
                'span', 'age').a.get_text().split()[1]

            if comment_time_unit == 'hours':
                comment_created = now - 3600 * int(comment_row.find(
                    'span', 'age').a.get_text().split()[0])

            else:
                comment_created = now - 60 * int(comment_row.find(
                    'span', 'age').a.get_text().split()[0])

            comment_created = time.strftime(
                '%Y-%m-%d %H:%M', time.localtime(comment_created))

            # Get comment's level in tree by getting indentation width
            # value divided by value of one indent (40px)
            level = int(comment_row.find(
                'td', 'ind').contents[0].get('width')) / 40

            # Set parent comment as blank if comment is the top-level
            # comment
            if level == 0:
                parent_comment = None

            # Otherwise, get preceding comment in comment tree
            else:
                cursor.execute(
                    """
                      SELECT id
                        FROM comment
                             JOIN feed_comment
                               ON feed_comment.comment_id = comment.id
                       WHERE level = %(level)s
                         AND feed_id = %(feed_id)s
                    ORDER BY feed_rank
                       LIMIT 1;
                    """,
                    {'level': level - 1,
                    'feed_id': feed_id}
                )

                parent_comment = cursor.fetchone()[0]

            # Get username of user who posted comment
            try:
                comment_username = comment_row.find('a', 'hnuser').get_text()
            except AttributeError:
                comment_username = ''

            # Add scraped comment data to database
            cursor.execute(
                """
                INSERT INTO comment
                            (id, content, created, level, parent_comment,
                            post_id, username)
                     VALUES (%(id)s, %(content)s, %(created)s, %(level)s,
                            %(parent_comment)s, %(post_id)s, %(username)s);
                """,
                {'id': comment_id,
                'content': comment_content,
                'created': comment_created,
                'level': level,
                'parent_comment': parent_comment,
                'post_id': post_id,
                'username': comment_username}
                )

        # Increment comment feed rank to get current comment's rank
        comment_feed_rank += 1

        # Add feed-based comment data to database
        cursor.execute(
            """
            INSERT INTO feed_comment
                        (comment_id, feed_id, feed_rank)
                 VALUES (%(comment_id)s, %(feed_id)s, %(feed_rank)s);
            """,
            {'comment_id': comment_id,
            'feed_id': feed_id,
            'feed_rank': comment_feed_rank}
            )

    conn.commit()

    cursor.close()
    conn.close()

    print('Post ' + str(post_id) + ' and its comments scraped')

    return


def get_comment(comment_id):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get comment from database
    cursor.execute(
        """
          SELECT comment.content, comment.created, comment.level,
                 comment.parent_comment, comment.post_id, comment.username,
                 feed_comment.feed_rank
            FROM comment
                 JOIN feed_comment
                   ON feed_comment.comment_id = comment.id
           WHERE comment.id = %(comment_id)s
        ORDER BY feed_id
           LIMIT 1;
        """,
        {'comment_id': comment_id}
        )

    comment = cursor.fetchone()

    if not comment:
        return make_response('Comment not found', 404)

    else:
        comment = dict(comment)

    cursor.close()
    conn.close()

    return jsonify(comment)


def get_post(post_id):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get post from database
    cursor.execute(
        """
          SELECT post.created, post.link, post.title, post.type, post.username,
                 post.website, feed_post.feed_rank, feed_post.point_count,
                 (SELECT COUNT(*)
                    FROM comment
                   WHERE comment.post_id = post.id) AS comment_count
            FROM post
                 JOIN feed_post
                   ON feed_post.post_id = post.id
           WHERE post.id = %(post_id)s
        ORDER BY feed_id
           LIMIT 1;
        """,
        {'post_id': post_id}
        )

    post = cursor.fetchone()

    if not post:
        return make_response('Post not found', 404)

    else:
        post = dict(post)

    cursor.close()
    conn.close()

    return jsonify(post)


def get_feeds(time_period):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get requested feed(s) from database based on passed time value
    if time_period == 'day':
        cursor.execute(
            """
            SELECT id
              FROM feed
             WHERE created > TIMESTAMP 'yesterday';
            """
            )

        feed_ids = [feed_id[0] for feed_id in cursor.fetchall()]

    elif time_period == 'week':
        cursor.execute(
            """
            SELECT id
              FROM feed
             WHERE created BETWEEN
                   now()::DATE-EXTRACT(DOW FROM now())::INT-7
                   AND now()::DATE-EXTRACT(DOW from now())::INT;
            """
            )

        feed_ids = [feed_id[0] for feed_id in cursor.fetchall()]

    elif time_period == 'all':
        cursor.execute(
            """
            SELECT id
              FROM feed;
            """
            )

        feed_ids = [feed_id[0] for feed_id in cursor.fetchall()]

    else:
        cursor.execute(
            """
              SELECT id
                FROM feed
            ORDER BY id DESC
               LIMIT 1;
            """
            )

        feed_ids = [feed_id[0] for feed_id in cursor.fetchall()]

    cursor.close()
    conn.close()

    return feed_ids


def get_average_comment_count(feed_ids):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get average comment count
    cursor.execute(
        """
        SELECT avg(comment_count)
          FROM (
                  SELECT post_id,
                         COUNT(*) AS comment_count
                    FROM comment
                         JOIN feed_comment
                           ON feed_comment.comment_id = comment.id
                   WHERE feed_id = ANY(%(feed_id)s)
                GROUP BY post_id
          ) comment_count_table;
        """,
        {'feed_id': feed_ids}
        )

    average = round(cursor.fetchone()[0])

    cursor.close()
    conn.close()

    return jsonify(average)


def get_average_comment_tree_depth(feed_ids):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get average comment level
    cursor.execute(
        """
        SELECT avg(level)
          FROM comment
               JOIN feed_comment
                 ON feed_comment.comment_id = comment.id
         WHERE feed_id = ANY(%(feed_id)s);
        """,
        {'feed_id': feed_ids}
        )

    depth = round(cursor.fetchone()[0])

    cursor.close()
    conn.close()

    return jsonify(depth)


def get_average_comment_word_count(feed_ids):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get average comment word count
    cursor.execute(
        """
        SELECT avg(word_count)
        FROM (
              SELECT id,
                     array_length(regexp_split_to_array(content, '\s+'), 1)
                        AS word_count
                FROM comment
                     JOIN feed_comment
                       ON feed_comment.comment_id = comment.id
               WHERE feed_id = ANY(%(feed_id)s)
        ) word_count_table;
        """,
        {'feed_id': feed_ids}
        )

    average = round(cursor.fetchone()[0])

    cursor.close()
    conn.close()

    return jsonify(average)


def get_average_point_count(feed_ids):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get average point count for posts
    cursor.execute(
        """
        SELECT avg(point_count)
          FROM post
               JOIN feed_post
                 ON feed_post.post_id = post.id
         WHERE feed_id = ANY(%(feed_id)s);
        """,
        {'feed_id': feed_ids}
        )

    average = round(cursor.fetchone()[0])

    cursor.close()
    conn.close()

    return jsonify(average)


def get_comments_with_highest_word_counts(feed_ids):
    # Get number of requested comments from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get comments with highest word counts
    cursor.execute(
        """
          SELECT *
            FROM (
                    SELECT DISTINCT ON (comment.id)
                           comment.id, comment.content, comment.created,
                           comment.level, comment.parent_comment,
                           comment.post_id, comment.username,
                           feed_comment.feed_rank,
                           array_length(regexp_split_to_array(
                              comment.content, '\s+'), 1) AS word_count
                      FROM comment
                           JOIN feed_comment
                             ON feed_comment.comment_id = comment.id
                     WHERE feed_id = ANY(%(feed_id)s)
                  ORDER BY comment.id, word_count DESC
            ) comment_table
        ORDER BY word_count DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    comments = []

    for row in cursor.fetchall():
        comments.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(comments)


def get_most_frequent_comment_words(feed_ids):
    # Get number of requested words from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get highest-frequency words used in comments
    cursor.execute(
        """
          SELECT word, COUNT(*) AS word_frequency
            FROM (
                  SELECT regexp_split_to_table(LOWER(content), '\s+') AS word
                    FROM (
                            SELECT DISTINCT ON (id)
                                   comment.id, comment.content,
                                   feed_comment.feed_id
                              FROM comment
                                    JOIN feed_comment
                                      ON feed_comment.comment_id = comment.id
                             WHERE feed_id = ANY(%(feed_id)s)
                          ORDER BY comment.id, feed_id DESC
                    ) comment_table
            ) word_table
        GROUP BY word
        ORDER BY word_frequency DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    words = []

    for row in cursor.fetchall():
        words.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(words)


def get_deepest_comment_tree(feed_ids):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get highest level comment (deepest in comment tree)
    cursor.execute(
        """
          SELECT *
            FROM (
                  SELECT DISTINCT ON (comment.id)
                         comment.id, comment.content, comment.created,
                         comment.level, comment.parent_comment,
                         comment.post_id, comment.username,
                         feed_comment.feed_rank
                    FROM comment
                         JOIN feed_comment
                           ON feed_comment.comment_id = comment.id
                   WHERE feed_id = ANY(%(feed_id)s)
                ORDER BY comment.id, level DESC
            ) comment_table
        ORDER BY level DESC
           LIMIT 1;
        """,
        {'feed_id': feed_ids}
        )

    comment = dict(cursor.fetchone())

    comment['tree'] = []

    # Get parent comments of parent comment to get full comment tree
    while comment['parent_comment']:
        comment['tree'].append(comment['parent_comment'])

        cursor.execute(
            """
            SELECT parent_comment
              FROM comment
             WHERE id = %(id)s;
            """,
            {'id': comment['parent_comment']}
            )

        comment['parent_comment'] = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return jsonify(comment)


def get_posts_with_highest_comment_counts(feed_ids):
    # Get number of requested posts from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get posts with highest comment counts
    cursor.execute(
        """
          SELECT *
            FROM (
                  SELECT DISTINCT ON (post.id)
                         post.id, post.created, post.link, post.title,
                         post.type, post.username, post.website,
                         feed_post.feed_rank, feed_post.point_count,
                         (SELECT COUNT(*)
                            FROM comment
                           WHERE comment.post_id = post.id) AS comment_count
                    FROM post
                         JOIN feed_post
                           ON feed_post.post_id = post.id
                   WHERE feed_id = ANY(%(feed_id)s)
                ORDER BY post.id, comment_count DESC
            ) post_table
        ORDER BY comment_count DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    posts = []

    for row in cursor.fetchall():
        posts.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(posts)


def get_posts_with_highest_point_counts(feed_ids):
    # Get number of requested posts from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get posts with highest point counts
    cursor.execute(
        """
          SELECT *
            FROM (
                  SELECT DISTINCT ON (post.id)
                         post.id, post.created, post.link, post.title,
                         post.type, post.username, post.website,
                         feed_post.feed_rank, feed_post.point_count,
                         (SELECT COUNT(*)
                            FROM comment
                           WHERE comment.post_id = post.id) AS comment_count
                    FROM post
                         JOIN feed_post
                           ON feed_post.post_id = post.id
                   WHERE feed_id = ANY(%(feed_id)s)
                ORDER BY post.id, point_count DESC
            ) post_table
        ORDER BY point_count DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    posts = []

    for row in cursor.fetchall():
        posts.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(posts)


def get_post_types(feed_ids):
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get count of type of posts ('article' vs. 'ask' vs. 'job' vs. 'show')
    cursor.execute(
        """
          SELECT type, COUNT(*) AS type_count
            FROM (
                    SELECT DISTINCT ON (post.id)
                           post.id, post.type, feed_post.feed_id
                      FROM post
                           JOIN feed_post
                             ON feed_post.post_id = post.id
                     WHERE feed_id = ANY(%(feed_id)s)
                  ORDER BY post.id, feed_post.feed_id DESC
            ) post_table
        GROUP BY type
        ORDER BY type_count DESC;
        """,
        {'feed_id': feed_ids}
        )

    types = []

    for row in cursor.fetchall():
        types.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(types)


def get_most_frequent_title_words(feed_ids):
    # Get number of requested words from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get highest-frequency words used in post titles
    cursor.execute(
        """
          SELECT word, COUNT(*) AS word_frequency
            FROM (
                  SELECT regexp_split_to_table(LOWER(title), '\s+') AS word
                    FROM (
                            SELECT DISTINCT ON (post.id)
                              FROM post
                                   JOIN feed_post
                                     ON feed_post.post_id = post.id
                             WHERE feed_id = ANY(%(feed_id)s)
                          ORDER BY post.id, feed_post.feed_id DESC
                    ) post_table
            ) word_table
        GROUP BY word
        ORDER BY word_frequency DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    words = []

    for row in cursor.fetchall():
        words.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(words)


def get_top_posts(feed_ids):
    # Get number of requested posts from query parameter, using default if
    # null
    count = int(request.args.get('count', 3))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get posts in order of rank
    cursor.execute(
        """
          SELECT *
            FROM (
                  SELECT DISTINCT ON (post.id)
                         post.id, post.created, post.link, post.title,
                         post.type, post.username, post.website,
                         feed_post.feed_rank, feed_post.point_count,
                         (SELECT COUNT(*)
                            FROM comment
                           WHERE comment.post_id = post.id) AS comment_count
                    FROM post
                         JOIN feed_post
                           ON feed_post.post_id = post.id
                   WHERE feed_id = ANY(%(feed_id)s)
                ORDER BY post.id, feed_rank
            ) post_table
        ORDER BY feed_rank
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    posts = []

    for row in cursor.fetchall():
        posts.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(posts)


def get_top_websites(feed_ids):
    # Get number of requested websites from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get websites that highest number of posts are from
    cursor.execute(
        """
          SELECT website, COUNT(*) AS link_count
            FROM (
                    SELECT DISTINCT ON (post.id)
                           post.id, post.website, feed_post.feed_id
                      FROM post
                           JOIN feed_post
                             ON feed_post.post_id = post.id
                     WHERE feed_id = ANY(%(feed_id)s)
                           AND website != ''
                  ORDER BY post.id, feed_post.feed_id DESC
            ) post_table
        GROUP BY website
        ORDER BY link_count DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    websites = []

    for row in cursor.fetchall():
        websites.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(websites)


def get_users_with_most_comments(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get users who posted the most comments
    cursor.execute(
        """
          SELECT username, COUNT(username) AS comment_count
            FROM (
                    SELECT DISTINCT ON (comment.id)
                           comment.id, comment.username, feed_comment.feed_id
                      FROM comment
                           JOIN feed_comment
                             ON feed_comment.comment_id = comment.id
                     WHERE feed_id = ANY(%(feed_id)s)
                  ORDER BY comment.id, feed_comment.feed_id DESC
            ) comment_table
        GROUP BY username
        ORDER BY comment_count DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    usernames = []

    for row in cursor.fetchall():
        usernames.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(usernames)


def get_users_with_most_posts(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get users who posted the most posts
    cursor.execute(
        """
          SELECT username, COUNT(username) AS post_count
            FROM (
                    SELECT DISTINCT ON (post.id)
                           post.id, post.username, feed_post.feed_id
                      FROM post
                           JOIN feed_post
                             ON feed_post.post_id = post.id
                     WHERE feed_id = ANY(%(feed_id)s)
                           AND username != ''
                  ORDER BY post.id, feed_post.feed_id DESC
            ) post_table
        GROUP BY username
        ORDER BY post_count DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    usernames = []

    for row in cursor.fetchall():
        usernames.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(usernames)


def get_users_with_most_words_in_comments(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get users who posted the most words in comments
    cursor.execute(
        """
          SELECT username,
                 SUM(array_length(regexp_split_to_array(content, '\s+'), 1))
                     AS word_count
            FROM (
                    SELECT DISTINCT ON (comment.id)
                           comment.id, comment.username, feed_comment.feed_id
                      FROM comment
                           JOIN feed_comment
                             ON feed_comment.comment_id = comment.id
                     WHERE feed_id = ANY(%(feed_id)s)
                  ORDER BY comment.id, feed_comment.feed_id DESC
            ) comment_table
        GROUP BY username
        ORDER BY word_count DESC
           LIMIT %(count)s;
        """,
        {'feed_id': feed_ids,
        'count': count}
        )

    usernames = []

    for row in cursor.fetchall():
        usernames.append(dict(row))

    cursor.close()
    conn.close()

    return jsonify(usernames)
