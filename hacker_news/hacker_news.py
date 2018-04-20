import os
import psycopg2 as pg
import psycopg2.extras
import requests
import time

from bs4 import BeautifulSoup
from datetime import datetime
from flask import jsonify


def scrape():
    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor()

    # Add feed to database
    cursor.execute(
        """
        INSERT INTO feed DEFAULT VALUES
        RETURNING id;
        """
        )

    feed_id = cursor.fetchone()[0]

    # Get data from first 3 feed pages of Hacker News
    for i in range(1, 4):
        # Current UTC time in seconds
        now = int(datetime.utcnow().strftime('%s'))

        # Get HTML tree from feed page
        feed_html = requests.get(
            'https://news.ycombinator.com/news?p=' + str(i))

        feed_content = feed_html.content

        feed_soup = BeautifulSoup(feed_content, 'html.parser')

        # Get all post rows from HTML tree
        post_rows = feed_soup.find_all('tr', 'athing')

        for post_row in post_rows:
            # Get subtext row with additional post data
            subtext_row = post_row.next_sibling

            # Get post id
            post_id = post_row.get('id')

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
                '%Y-%m-%d %H:%M:%S', time.localtime(created))

            # Get post's rank on feed page
            feed_rank = post_row.find('span', 'rank').get_text()[:-1]

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

            # Get post's score if it is listed (otherwise, post is job
            # posting)
            if subtext_row.find('span', 'score'):
                point_count = subtext_row.find(
                    'span', 'score').get_text().split()[0]
            else:
                point_count = 0
                type = 'job'

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
                INSERT INTO post (post_id, created, feed_id, feed_rank, link,
                point_count, title, type, username, website)
                VALUES (%(post_id)s, %(created)s, %(feed_id)s, %(feed_rank)s,
                %(link)s, %(point_count)s, %(title)s, %(type)s, %(username)s,
                %(website)s)
                RETURNING id;
                """,
                {'post_id': post_id,
                'created': created,
                'feed_id': feed_id,
                'feed_rank': feed_rank,
                'link': link,
                'point_count': point_count,
                'title': title,
                'type': type,
                'username': username,
                'website': website}
                )

            # Serial identifier for post in database
            post_primary_id = cursor.fetchone()[0]

            # Current UTC time in seconds
            now = int(datetime.utcnow().strftime('%s'))

            # Get HTML tree from post's webpage
            post_html = requests.get(
                'https://news.ycombinator.com/item?id=' + post_id)

            post_content = post_html.content

            post_soup = BeautifulSoup(post_content, 'html.parser')

            # Get all comment rows from HTML tree
            comment_rows = post_soup.select('tr.athing.comtr')

            # Set starting comment feed rank to 0
            comment_feed_rank = 0

            for comment_row in comment_rows:
                # Get comment id
                comment_id = comment_row.get('id')

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
                    '%Y-%m-%d %H:%M:%S', time.localtime(comment_created))

                # Increment comment feed rank to get current comment's rank
                comment_feed_rank += 1

                # Get comment's level in tree by getting indentation width
                # value divided by value of one indent (40px)
                level = int(comment_row.find(
                    'td', 'ind').contents[0].get('width')) / 40

                # Set parent comment list as blank if comment is the top-level
                # comment
                if level == 0:
                    parent_comments = []

                # Get username of user who posted comment
                try:
                    comment_username = comment_row.find(
                        'a', 'hnuser').get_text()
                except:
                    comment_username = ''

                # Add scraped comment data to database
                cursor.execute(
                    """
                    INSERT INTO comment (post_id, comment_id, content, created,
                    feed_id, feed_rank, level, parent_comments, username)
                    VALUES (%(post_id)s, %(comment_id)s, %(content)s,
                    %(created)s, %(feed_id)s, %(feed_rank)s, %(level)s,
                    %(parent_comments)s, %(username)s);
                    """,
                    {'post_id': post_primary_id,
                    'comment_id': comment_id,
                    'content': comment_content,
                    'created': comment_created,
                    'feed_id': feed_id,
                    'feed_rank': comment_feed_rank,
                    'level': level,
                    'parent_comments': parent_comments,
                    'username': comment_username}
                    )

                # Add comment to parent list for the next comment
                parent_comments.append(comment_id)

    conn.commit()

    cursor.close()
    conn.close()

    print('Successfully scraped first three pages of Hacker News.')

    return


def get_post(post_id):
    return


def get_comment(comment_id):
    return


def get_last_hour_stats():
    stats = {}

    # Set up database connection wtih environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor(cursor_factory=pg.extras.DictCursor)

    # Get latest feed from database
    cursor.execute(
        """
        SELECT last_value FROM feed_id_seq;
        """
        )

    feed_id = cursor.fetchone()[0]

    # Get post with highest comment count
    cursor.execute(
        """
        SELECT post.created, post.link, post.point_count, post.post_id,
        post.title, COUNT(*) AS comment_count FROM comment
        JOIN post ON post.id = comment.post_id
        WHERE comment.feed_id = %(feed_id)s
        GROUP BY post.created, post.link, post.point_count, post.post_id,
        post.title
        ORDER BY comment_count DESC
        LIMIT 1;
        """,
        {'feed_id': feed_id}
        )

    stats['post_highest_comment_count'] = dict(cursor.fetchone())

    # Get average comment count
    cursor.execute(
        """
        SELECT avg(comment_count)
        FROM (
        SELECT post.post_id, COUNT(*) AS comment_count FROM comment
        JOIN post ON post.id = comment.post_id
        WHERE comment.feed_id = %(feed_id)s
        GROUP BY post.post_id
        ) comment_count_table;
        """,
        {'feed_id': feed_id}
        )

    stats['average_comment_count'] = round(cursor.fetchone()[0])

    # Get post with highest point count
    cursor.execute(
        """
        SELECT created, link, point_count, post_id, title FROM post
        WHERE feed_id = %(feed_id)s
        ORDER BY point_count DESC
        LIMIT 1;
        """,
        {'feed_id': feed_id}
        )

    stats['post_highest_point_count'] = dict(cursor.fetchone())

    # Get average point count for posts
    cursor.execute(
        """
        SELECT avg(point_count) FROM post
        WHERE feed_id = %(feed_id)s;
        """,
        {'feed_id': feed_id}
        )

    stats['average_post_point_count'] = round(cursor.fetchone()[0])

    # Get top 5 posts in order of rank
    cursor.execute(
        """
        SELECT post_id, feed_rank, link, point_count, title FROM post
        WHERE feed_id = %(feed_id)s
        ORDER BY feed_rank
        LIMIT 5;
        """,
        {'feed_id': feed_id}
        )

    stats['top_five_ranked_posts'] = []

    for row in cursor.fetchall():
        stats['top_five_ranked_posts'].append(dict(row))

    # Get website that highest number of posts are posted from
    cursor.execute(
        """
        SELECT website, COUNT(*) AS link_count FROM post
        WHERE feed_id = %(feed_id)s AND website != ''
        GROUP BY website
        ORDER BY link_count DESC
        LIMIT 1;
        """,
        {'feed_id': feed_id}
        )

    stats['website_highest_count'] = dict(cursor.fetchone())

    # Get count of type of posts ('article' vs. 'ask' vs. 'job' vs. 'show')
    cursor.execute(
        """
        SELECT type, COUNT(*) AS type_count FROM post
        WHERE feed_id = %(feed_id)s
        GROUP BY type
        ORDER BY type_count DESC;
        """,
        {'feed_id': feed_id}
        )

    stats['type_counts'] = []

    for row in cursor.fetchall():
        stats['type_counts'].append(dict(row))

    # Get highest-frequency word used in post titles
    cursor.execute(
        """
        SELECT word, COUNT(*) AS word_frequency
        FROM (
          SELECT regexp_split_to_table(LOWER(title), '\s+') AS word
          FROM post
          WHERE feed_id = %(feed_id)s
        ) word_table
        GROUP BY word
        ORDER BY word_frequency DESC
        LIMIT 1;
        """,
        {'feed_id': feed_id}
        )

    stats['post_title_highest_word_frequency'] = dict(cursor.fetchone())

    # Get comment with highest word count
    cursor.execute(
        """
        SELECT comment.comment_id, comment.content, comment.created,
        comment.feed_rank, comment.level, comment.parent, comment.username,
        post.post_id,
        array_length(regexp_split_to_array(comment.content, '\s+'), 1)
        AS word_count FROM comment
        JOIN post ON post.id = comment.post_id
        WHERE comment.feed_id = %(feed_id)s
        ORDER BY word_count DESC
        LIMIT 1;
        """,
        {'feed_id': feed_id}
        )

    stats['comment_highest_word_count'] = dict(cursor.fetchone())

    # Get average comment word count
    cursor.execute(
        """
        SELECT avg(word_count)
        FROM (
        SELECT comment_id,
        array_length(regexp_split_to_array(content, '\s+'), 1)
        AS word_count
        FROM comment
        WHERE feed_id = %(feed_id)s
        ) word_count_table;
        """,
        {'feed_id': feed_id}
        )

    stats['average_comment_word_count'] = round(cursor.fetchone()[0])

    # Get highest level comment (deepest in comment tree)
    cursor.execute(
        """
        SELECT comment.comment_id, comment.content, comment.created,
        comment.feed_rank, comment.level, comment.parent, comment.username,
        post.post_id FROM comment
        JOIN post ON post.id = comment.post_id
        WHERE comment.feed_id = %(feed_id)s
        ORDER BY level DESC
        LIMIT 1;
        """,
        {'feed_id': feed_id}
        )

    stats['comment_highest_level'] = dict(cursor.fetchone())

    # Get average comment level
    cursor.execute(
        """
        SELECT avg(level) FROM comment
        WHERE feed_id = %(feed_id)s;
        """,
        {'feed_id': feed_id}
        )

    stats['average_comment_level'] = round(cursor.fetchone()[0])

    # Get highest-frequency word used in comments
    cursor.execute(
        """
        SELECT word, COUNT(*) AS word_frequency
        FROM (
          SELECT regexp_split_to_table(LOWER(content), '\s+') AS word
          FROM comment
          WHERE feed_id = %(feed_id)s
        ) word_table
        GROUP BY word
        ORDER BY word_frequency DESC
        LIMIT 1;
        """,
        {'feed_id': feed_id}
        )

    stats['comment_highest_word_frequency'] = dict(cursor.fetchone())

    cursor.close()
    conn.close()

    return jsonify(stats)


def get_last_day_stats():
    return


def get_all_time_stats():
    return
