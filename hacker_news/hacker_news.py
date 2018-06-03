import asyncio
import os
import requests
import time

from bs4 import BeautifulSoup, UnicodeDammit
from datetime import date, datetime, timedelta
from flask import jsonify, make_response, request
from sqlalchemy import desc, inspect
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import func

from hacker_news import models


def scrape_loop():
    # Connect to database
    session = models.Session()

    # Add feed to database
    new_feed = models.Feed()

    session.add(new_feed)

    session.commit()

    feed_id = new_feed.id

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

    session.close()

    print('Scrape completed for first three pages of Hacker News.')

    return


async def scrape_page(page, feed_id, loop):
    # Connect to database
    session = models.Session()

    print('Scrape initiated for page ' + str(page) + ' of Hacker News.')

    # Get current UTC time in seconds
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

        # Check if post exists in database
        post_exists = session.query(models.Post.id).filter_by(
            id=post_id).scalar()

        # Get core post data if it is not in database already
        if not post_exists:
            # Get UTC timestamp for post's posting time by subtracting the
            # number of days/hours/minutes ago given on the webpage from the
            # current UTC timestamp
            time_unit = subtext_row.find('span', 'age').a.get_text().split()[1]

            if 'day' in time_unit:
                created = now - 86400 * int(subtext_row.find(
                    'span', 'age').a.get_text().split()[0])

            elif 'hour' in time_unit:
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
            post = models.Post(created=created, id=post_id, link=link,
                title=title, type=type, username=username, website=website)

            session.add(post)

        # Get post's comment count if it is listed (otherwise, set to 0)
        if 'comment' in subtext_row.find_all(
            href='item?id=' + post_id)[-1].get_text():
                unicode_count = UnicodeDammit(subtext_row.find_all(
                    href='item?id=' + post_id)[-1].get_text())
                comment_count = unicode_count.unicode_markup.split()[0]
        else:
            comment_count = 0

        # Get post's rank on feed page
        feed_rank = post_row.find('span', 'rank').get_text()[:-1]

        # Get post's score if it is listed (otherwise, post is job posting)
        if subtext_row.find('span', 'score'):
            point_count = subtext_row.find(
                'span', 'score').get_text().split()[0]
        else:
            point_count = 0
            type = 'job'

        # Add feed-based post data to database
        feed_post = models.FeedPost(comment_count=comment_count,
            feed_id=feed_id, feed_rank=feed_rank, point_count=point_count,
            post_id=post_id)

        session.add(feed_post)

        session.commit()

        # Create asynchronous task to scrape post page for its comments
        loop.create_task(scrape_post(post_id, feed_id, loop, None))

    return


async def scrape_post(post_id, feed_id, loop, page_number):
    # Connect to database
    session = models.Session()

    # Get current UTC time in seconds
    now = int(datetime.utcnow().strftime('%s'))

    # Get HTML tree from post's webpage, specifying page number if given
    if page_number:
        post_html = requests.get(
            'https://news.ycombinator.com/item?id=' + str(post_id) + '&p=' +
            str(page_number))

    else:
        post_html = requests.get(
            'https://news.ycombinator.com/item?id=' + str(post_id))

    post_content = post_html.content

    post_soup = BeautifulSoup(post_content, 'html.parser')

    # If post page contains a "More" link to more comments, create asynchronous
    # task to scrape that page for its comments
    if (post_soup.find('a', 'morelink')):
        page_number = post_soup.find('a', 'morelink').get(
            'href').split('&p=')[1]

        loop.create_task(scrape_post(post_id, feed_id, loop, page_number))

    # Get all comment rows from HTML tree
    comment_rows = post_soup.select('tr.athing.comtr')

    # Set starting comment feed rank to 0
    comment_feed_rank = 0

    for comment_row in comment_rows:
        # Get comment id
        comment_id = comment_row.get('id')

        # Check if comment exists in database
        comment_exists = session.query(models.Comment.id).filter_by(
            id=comment_id).scalar()

        # Get core comment data if it is not in database already
        if not comment_exists:
            # If comment has content span, get text from span
            if comment_row.find('div', 'comment').find_all('span'):
                comment_content = comment_row.find(
                    'div', 'comment').find_all('span')[0].get_text()

                # Remove the last word ('reply') from the comment content
                # and strip trailing whitespace
                comment_content = comment_content.rsplit(' ', 1)[0].strip()

                total_word_count = len(comment_content.split())

            # Otherwise, comment is flagged, so get flagged message as text
            # and strip trailing whitespace
            else:
                comment_content = comment_row.find(
                    'div', 'comment').get_text().strip()

                total_word_count = 0

            # Get UTC timestamp for comment's posting time by subtracting
            # the number of days/hours/minutes ago given on the webpage from
            # the current UTC timestamp
            comment_time_unit = comment_row.find(
                'span', 'age').a.get_text().split()[1]

            if 'day' in comment_time_unit:
                comment_created = now - 86400 * int(comment_row.find(
                    'span', 'age').a.get_text().split()[0])

            elif 'hour' in comment_time_unit:
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
                parent_comment = session.query(models.Comment).with_entities(
                    models.Comment.id).join(models.FeedComment).filter(
                    models.Comment.level == (level - 1)).filter(
                    models.FeedComment.feed_id == feed_id).filter(
                    models.Comment.post_id == post_id).order_by(
                    models.FeedComment.feed_rank).limit(1).one()[0]

            # Get username of user who posted comment
            try:
                comment_username = comment_row.find('a', 'hnuser').get_text()

            except AttributeError:
                comment_username = ''

            # Add scraped comment data to database
            comment = models.Comment(content=comment_content,
                created=comment_created, id=comment_id, level=level,
                parent_comment=parent_comment, post_id=post_id,
                total_word_count=total_word_count, username=comment_username,
                word_counts=func.to_tsvector('simple_english',
                comment_content.lower()))

            session.add(comment)

        # Increment comment feed rank to get current comment's rank
        comment_feed_rank += 1

        # Add feed-based comment data to database
        feed_comment = models.FeedComment(comment_id=comment_id,
            feed_id=feed_id, feed_rank=comment_feed_rank)

        session.add(feed_comment)

    session.commit()

    # Print message if there are no more pages of comments to scrape
    if not post_soup.find('a', 'morelink'):
        print('Post ' + str(post_id) + ' and its comments scraped')

    return


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
    # Connect to database
    session = models.Session()

    # Get requested feed(s) from database based on passed time value
    if time_period == 'day':
        feed_ids = [row.id for row in session.query(models.Feed).filter(
            models.Feed.created > date.today()).all()]

    # Get one feed per day in past week if 'week' is specified
    elif time_period == 'week':
        feed_ids = []

        for i in range(7):
            feed_ids.append(session.query(models.Feed.id).filter(
                models.Feed.created > date.today() - timedelta(days=i)).limit(
                1).one()[0])

    # Return no feed_ids if 'all' is specified so all data can be queried
    elif time_period == 'all':
        feed_ids = None

    # Return most recent feed_id if time_period is 'hour' or unspecified
    else:
        feed_ids = [row.id for row in session.query(models.Feed).order_by(
            models.Feed.created.desc()).limit(1)]

    return feed_ids


def get_average_comment_count(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average comment count, filtering by feed_ids if specified
    if feed_ids:
        average = round(session.query(
            func.avg(models.FeedPost.comment_count)).filter(
            models.FeedPost.feed_id.in_(feed_ids)).one()[0])

    else:
        average = round(session.query(
            func.avg(models.FeedPost.comment_count)).one()[0])

    session.close()

    return jsonify(average)


def get_average_comment_tree_depth(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average comment level, filtering by feed_ids if specified
    if feed_ids:
        average = round(session.query(func.avg(models.Comment.level)).join(
            models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).one()[0])

    else:
        average = round(session.query(func.avg(models.Comment.level)).one()[0])

    session.close()

    return jsonify(average)


def get_average_comment_word_count(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average comment word count, filtering by feed_ids if specified
    if feed_ids:
        average = round(session.query(func.avg(
            models.Comment.total_word_count)).join(models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).one()[0])

    else:
        average = round(session.query(func.avg(
            models.Comment.total_word_count)).one()[0])

    session.close()

    return jsonify(average)


def get_average_point_count(feed_ids):
    # Connect to database
    session = models.Session()

    # Get average post point count, filtering by feed_ids if specified
    if feed_ids:
        average = round(session.query(func.avg(
            models.FeedPost.point_count)).filter(
            models.FeedPost.feed_id.in_(feed_ids)).one()[0])

    else:
        average = round(session.query(func.avg(
            models.FeedPost.point_count)).one()[0])

    session.close()

    return jsonify(average)


def get_comments_with_highest_word_counts(feed_ids):
    # Get number of requested comments from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get comments with highest word counts, filtering by feed_ids if specified
    if feed_ids:
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

    session.close()

    comments = []

    for row in query:
        comments.append(row._asdict())

    return jsonify(comments)


def get_most_frequent_comment_words(feed_ids):
    # Get number of requested words from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get highest frequency words used in comments, excluding stop words,
    # filtering by feed_ids if specified
    if feed_ids:
        query = session.execute(
            """
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
            """,
            {'feed_id': feed_ids,
            'count': count}
            ).fetchall()

    else:
        query = session.execute(
            """
              SELECT *
                FROM ts_stat(
                     $$SELECT word_counts
                         FROM comment$$
                )
               WHERE LENGTH (word) > 1
            ORDER BY nentry DESC
               LIMIT :count;
            """,
            {'feed_id': feed_ids,
            'count': count}
            ).fetchall()

    session.close()

    words = []

    for row in query:
        words.append(dict(row))

    return jsonify(words)


def get_deepest_comment_tree(feed_ids):
    # Connect to database
    session = models.Session()

    # Get highest level comment (deepest in comment tree), filtering by
    # feed_ids if specified
    if feed_ids:
        subquery = session.query(models.Comment).with_entities(
            models.Comment.content, models.Comment.created, models.Comment.id,
            models.Comment.level, models.Comment.parent_comment,
            models.Comment.post_id, models.Comment.username).join(
            models.FeedComment).filter(
            models.FeedComment.feed_id.in_(feed_ids)).order_by(
            models.Comment.id, models.Comment.level.desc()).distinct(
            models.Comment.id).subquery()

        comment = session.query(subquery).order_by(
            subquery.columns.get('level').desc()).limit(1).one()._asdict()

        # Get post information
        post = session.query(models.Post).with_entities(models.Post.created,
            models.Post.id, models.Post.link, models.Post.title,
            models.Post.type, models.Post.username,
            models.FeedPost.comment_count, models.FeedPost.feed_rank,
            models.FeedPost.point_count).join(models.FeedPost).filter(
            models.Post.id == comment['post_id']).filter(
            models.FeedPost.feed_id.in_(feed_ids)).order_by(
            models.FeedPost.post_id.desc()).limit(1).one()._asdict()

    else:
        comment = session.query(models.Comment).with_entities(
            models.Comment.content, models.Comment.created, models.Comment.id,
            models.Comment.level, models.Comment.parent_comment,
            models.Comment.post_id, models.Comment.username).order_by(
            models.Comment.level.desc()).limit(1).one()._asdict()

        # Get post information
        post = session.query(models.Post).with_entities(models.Post.created,
            models.Post.id, models.Post.link, models.Post.title,
            models.Post.type, models.Post.username,
            models.FeedPost.comment_count, models.FeedPost.feed_rank,
            models.FeedPost.point_count).join(models.FeedPost).filter(
            models.Post.id == comment['post_id']).order_by(
            models.FeedPost.feed_id.desc()).limit(1).one()._asdict()

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
    # Get number of requested posts from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get posts with highest comment counts, filtering by feed_ids if specified
    if feed_ids:
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
        subquery = session.query(models.Post).with_entities(
            models.Post.created, models.Post.id, models.Post.link,
            models.Post.title, models.Post.type, models.Post.username,
            models.Post.website, models.FeedPost.comment_count,
            models.FeedPost.feed_rank, models.FeedPost.point_count).join(
            models.FeedPost).order_by(
            models.Post.id, models.FeedPost.comment_count.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).order_by(
            subquery.columns.get('comment_count').desc()).limit(count)

    session.close()

    posts = []

    for row in query:
        posts.append(row._asdict())

    return jsonify(posts)


def get_posts_with_highest_point_counts(feed_ids):
    # Get number of requested posts from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get posts with highest point counts, filtering by feed_ids if specified
    if feed_ids:
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
        subquery = session.query(models.Post).with_entities(
            models.Post.created, models.Post.id, models.Post.link,
            models.Post.title, models.Post.type, models.Post.username,
            models.Post.website, models.FeedPost.comment_count,
            models.FeedPost.feed_rank, models.FeedPost.point_count).join(
            models.FeedPost).order_by(
            models.Post.id, models.FeedPost.point_count.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).order_by(
            subquery.columns.get('point_count').desc()).limit(count)

    session.close()

    posts = []

    for row in query:
        posts.append(row._asdict())

    return jsonify(posts)


def get_post_types(feed_ids):
    # Connect to database
    session = models.Session()

    # Get count of types of posts ('article' vs. 'ask' vs. 'job' vs. 'show'),
    # filtering by feed_ids if specified
    if feed_ids:
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

    session.close()

    types = []

    for row in query:
        types.append(row._asdict())

    return jsonify(types)


def get_most_frequent_title_words(feed_ids):
    # Get number of requested words from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get highest-frequency words used in post titles, excluding stop words,
    # filtering by feed_ids if specified
    if feed_ids:
        query = session.execute(
            """
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
            """,
            {'feed_id': feed_ids,
            'count': count}
            ).fetchall()

    else:
        query = session.execute(
            """
              SELECT *
                FROM ts_stat(
                     $$SELECT to_tsvector('simple_english', LOWER(title))
                         FROM post$$
                )
               WHERE word NOT IN ('ask', 'hn', 'show')
                 AND LENGTH (word) > 1
            ORDER BY nentry DESC
               LIMIT :count;
            """,
            {'feed_id': feed_ids,
            'count': count}
            ).fetchall()

    session.close()

    words = []

    for row in query:
        words.append(dict(row))

    return jsonify(words)


def get_top_posts(feed_ids):
    # Get number of requested posts from query parameter, using default if
    # null
    count = int(request.args.get('count', 3))

    # Connect to database
    session = models.Session()

    # Get posts in order of rank, filtering by feed_ids if specified
    if feed_ids:
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
        subquery = session.query(models.Post).with_entities(
            models.Post.created, models.Post.id, models.Post.link,
            models.Post.title, models.Post.type, models.Post.username,
            models.Post.website, models.FeedPost.comment_count,
            models.FeedPost.feed_rank, models.FeedPost.point_count).join(
            models.FeedPost).order_by(
            models.Post.id, models.FeedPost.feed_rank,
            models.FeedPost.point_count.desc()).distinct(
            models.Post.id).subquery()

        query = session.query(subquery).order_by(
            subquery.columns.get('feed_rank'),
            subquery.columns.get('point_count').desc()).limit(count)

    session.close()

    posts = []

    for row in query:
        posts.append(row._asdict())

    return jsonify(posts)


def get_top_websites(feed_ids):
    # Get number of requested websites from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get websites that highest number of posts are from, filtering by feed_ids
    # if specified
    if feed_ids:
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

    session.close()

    websites = []

    for row in query:
        websites.append(row._asdict())

    return jsonify(websites)


def get_users_with_most_comments(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get users who posted the most comments, filtering by feed_ids if
    # specified
    if feed_ids:
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
        subquery = session.query(models.Comment).with_entities(
            models.Comment.id, models.Comment.total_word_count,
            models.Comment.username).filter(
            models.Comment.username != '').subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('username'),
            func.count('*').label("comment_count"), func.sum(
                subquery.columns.get('total_word_count')
            ).label("word_count")).group_by(
            subquery.columns.get('username')).order_by(
            desc('comment_count')).limit(count)

    session.close()

    users = []

    for row in query:
        users.append(row._asdict())

    return jsonify(users)


def get_users_with_most_posts(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get users who posted the most posts, filtering by feed_ids if specified
    if feed_ids:
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

    session.close()

    users = []

    for row in query:
        users.append(row._asdict())

    return jsonify(users)


def get_users_with_most_words_in_comments(feed_ids):
    # Get number of requested users from query parameter, using default if
    # null
    count = int(request.args.get('count', 1))

    # Connect to database
    session = models.Session()

    # Get users who posted the most words in comments, filtering by feed_ids if
    # specified
    if feed_ids:
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
        subquery = session.query(models.Comment).with_entities(
            models.Comment.id, models.Comment.total_word_count,
            models.Comment.username).filter(
            models.Comment.username != '').subquery()

        query = session.query(subquery).with_entities(
            subquery.columns.get('username'),
            func.count('*').label("comment_count"), func.sum(
                subquery.columns.get('total_word_count')
            ).label("word_count")).group_by(
            subquery.columns.get('username')).order_by(
            desc('word_count')).limit(count)

    session.close()

    users = []

    for row in query:
        users.append(row._asdict())

    return jsonify(users)
