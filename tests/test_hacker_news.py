import json
import re

from utils.tests import HackerNewsTestCase


# Test /api/hacker_news/comment endpoint [GET]
class TestComment(HackerNewsTestCase):
    def test_comment_get(self):
        # Arrange
        comment_id = '1'

        # Act
        response = self.client.get(
            '/api/hacker_news/comment/' + comment_id
            )
        comment = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(comment['content'], 'test')
        self.assertEqual(comment['feed_rank'], 1)
        self.assertEqual(comment['level'], 0)
        self.assertEqual(comment['parent_comment'], None)
        self.assertEqual(comment['post_id'], 1)
        self.assertEqual(comment['username'], 'test')

        # Ensure created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(bool(timestamp_pattern.match(
            comment['created'])), True)

    def test_comment_get_error(self):
        # Arrange
        comment_id = '100000'

        # Act
        response = self.client.get(
            '/api/hacker_news/comment/' + comment_id
            )
        error = response.get_data(as_text=True)

        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(error, 'Comment not found')


# Test /api/hacker_news/post endpoint [GET]
class TestPost(HackerNewsTestCase):
    def test_post_get(self):
        # Arrange
        post_id = '1'

        # Act
        response = self.client.get(
            '/api/hacker_news/post/' + post_id
            )
        post = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post['comment_count'], 1)
        self.assertEqual(post['feed_rank'], 1)
        self.assertEqual(post['link'], 'https://test.com')
        self.assertEqual(post['point_count'], 1)
        self.assertEqual(post['title'], 'Show HN: Test')
        self.assertEqual(post['type'], 'show')
        self.assertEqual(post['username'], 'test')
        self.assertEqual(post['website'], 'test.com')

        # Ensure created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(bool(timestamp_pattern.match(
            post['created'])), True
            )

    def test_post_get_error(self):
        # Arrange
        post_id = '100000'

        # Act
        response = self.client.get(
            '/api/hacker_news/post/' + post_id
            )
        error = response.get_data(as_text=True)

        # Assert
        self.assertEqual(response.status_code, 404)
        self.assertEqual(error, 'Post not found')


# Test /api/hacker_news/stats/<time_period>/average_comment_count endpoint
# [GET]
class TestAverageCommentCount(HackerNewsTestCase):
    def test_average_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_comment_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_comment_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_comment_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_comment_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)


# Test /api/hacker_news/stats/<time_period>/average_comment_tree_depth endpoint
# [GET]
class TestAverageCommentTreeDepth(HackerNewsTestCase):
    def test_average_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_tree_depth'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_tree_depth'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_tree_depth'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_tree_depth'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)


# Test /api/hacker_news/stats/<time_period>/average_comment_word_count endpoint
# [GET]
class TestAverageCommentWordCount(HackerNewsTestCase):
    def test_average_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_word_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_word_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_word_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/average_comment_word_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)


# Test /api/hacker_news/stats/<time_period>/average_point_count endpoint [GET]
class TestAveragePointCount(HackerNewsTestCase):
    def test_average_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_point_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_point_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_point_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)

    def test_average_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/average_point_count'
            )
        average = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(isinstance(average, int), True)


# Test /api/hacker_news/stats/<time_period>/comments_highest_word_count
# endpoint [GET]
class TestCommentsHighestWordCount(HackerNewsTestCase):
    def test_comments_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/comments_highest_word_count'
            )
        comments = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(comments), 1)

        # Ensure each comment's content is a string
        self.assertEqual(all(isinstance(
            comment['content'], str) for comment in comments), True)

        # Ensure each comment's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            comment['created'])) for comment in comments), True)

        # Ensure each comment's id is an integer
        self.assertEqual(all(
            isinstance(comment['id'], int) for comment in comments), True)

        # Ensure each comment's level is an integer
        self.assertEqual(all(
            isinstance(comment['level'], int) for comment in comments), True)

        # Ensure each comment's parent comment is an integer
        self.assertEqual(all(isinstance(
            comment['parent_comment'],
            (int, type(None))) for comment in comments), True)

        # Ensure each comment's post id is an integer
        self.assertEqual(all(
            isinstance(comment['post_id'], int) for comment in comments), True)

        # Ensure each comment's total word count is the length of the words in
        # the comment's content
        self.assertEqual(all(
            comment['total_word_count'] == len(comment['content'].split())
            for comment in comments), True)

        # Ensure each comment's username is a string
        self.assertEqual(all(isinstance(
            comment['username'], str) for comment in comments), True)

    def test_comments_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/comments_highest_word_count'
            )
        comments = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(comments), 1)

        # Ensure each comment's content is a string
        self.assertEqual(all(isinstance(
            comment['content'], str) for comment in comments), True)

        # Ensure each comment's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            comment['created'])) for comment in comments), True)

        # Ensure each comment's id is an integer
        self.assertEqual(all(
            isinstance(comment['id'], int) for comment in comments), True)

        # Ensure each comment's level is an integer
        self.assertEqual(all(
            isinstance(comment['level'], int) for comment in comments), True)

        # Ensure each comment's parent comment is an integer
        self.assertEqual(all(isinstance(
            comment['parent_comment'],
            (int, type(None))) for comment in comments), True)

        # Ensure each comment's post id is an integer
        self.assertEqual(all(
            isinstance(comment['post_id'], int) for comment in comments), True)

        # Ensure each comment's total word count is the length of the words in
        # the comment's content
        self.assertEqual(all(
            comment['total_word_count'] == len(comment['content'].split())
            for comment in comments), True)

        # Ensure each comment's username is a string
        self.assertEqual(all(isinstance(
            comment['username'], str) for comment in comments), True)

    def test_comments_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/comments_highest_word_count'
            )
        comments = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(comments), 1)

        # Ensure each comment's content is a string
        self.assertEqual(all(isinstance(
            comment['content'], str) for comment in comments), True)

        # Ensure each comment's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            comment['created'])) for comment in comments), True)

        # Ensure each comment's id is an integer
        self.assertEqual(all(
            isinstance(comment['id'], int) for comment in comments), True)

        # Ensure each comment's level is an integer
        self.assertEqual(all(
            isinstance(comment['level'], int) for comment in comments), True)

        # Ensure each comment's parent comment is an integer
        self.assertEqual(all(isinstance(
            comment['parent_comment'],
            (int, type(None))) for comment in comments), True)

        # Ensure each comment's post id is an integer
        self.assertEqual(all(
            isinstance(comment['post_id'], int) for comment in comments), True)

        # Ensure each comment's total word count is the length of the words in
        # the comment's content
        self.assertEqual(all(
            comment['total_word_count'] == len(comment['content'].split())
            for comment in comments), True)

        # Ensure each comment's username is a string
        self.assertEqual(all(isinstance(
            comment['username'], str) for comment in comments), True)

    def test_comments_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/comments_highest_word_count'
            )
        comments = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(comments), 1)

        # Ensure each comment's content is a string
        self.assertEqual(all(isinstance(
            comment['content'], str) for comment in comments), True)

        # Ensure each comment's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            comment['created'])) for comment in comments), True)

        # Ensure each comment's id is an integer
        self.assertEqual(all(
            isinstance(comment['id'], int) for comment in comments), True)

        # Ensure each comment's level is an integer
        self.assertEqual(all(
            isinstance(comment['level'], int) for comment in comments), True)

        # Ensure each comment's parent comment is an integer
        self.assertEqual(all(isinstance(
            comment['parent_comment'],
            (int, type(None))) for comment in comments), True)

        # Ensure each comment's post id is an integer
        self.assertEqual(all(
            isinstance(comment['post_id'], int) for comment in comments), True)

        # Ensure each comment's total word count is the length of the words in
        # the comment's content
        self.assertEqual(all(
            comment['total_word_count'] == len(comment['content'].split())
            for comment in comments), True)

        # Ensure each comment's username is a string
        self.assertEqual(all(isinstance(
            comment['username'], str) for comment in comments), True)

    def test_comments_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/comments_highest_word_count',
            query_string=query
            )
        comments = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(comments), 2)


# Test /api/hacker_news/stats/<time_period>/comment_words endpoint [GET]
class TestCommentWords(HackerNewsTestCase):
    def test_words_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/comment_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/comment_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/comment_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/comment_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/comment_words',
            query_string=query
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(words), 2)


# Test /api/hacker_news/stats/<time_period>/deepest_comment_tree endpoint [GET]
class TestDeepestCommentTree(HackerNewsTestCase):
    def test_tree_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/deepest_comment_tree'
            )
        post = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)

        # Ensure the post's comment count is an integer
        self.assertEqual(isinstance(post['comment_count'], int), True)

        # Ensure the tree is a dictionary
        self.assertEqual(isinstance(post['comment_tree'], dict), True)

        # Ensure the top comment's child comment in the comment tree is a
        # dictionary
        self.assertEqual(isinstance(
            post['comment_tree']['child_comment'], (dict, type(None))), True)

        # Ensure the top comment's content in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['content'],
            (str, type(None))), True)

        # Ensure the top comment's timestamp in the comment tree matches GMT
        # format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(bool(
            timestamp_pattern.match(post['comment_tree']['created'])), True)

        # Ensure the top comment's id in the comment tree is an integer
        self.assertEqual(isinstance(post['comment_tree']['id'],
            (int, type(None))), True)

        # Ensure the top comment's username in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['username'],
            (str, type(None))), True)

        # Ensure the post's created timestamp matches GMT format
        self.assertEqual(bool(timestamp_pattern.match(post['created'])), True)

        # Ensure the post's feed rank is an integer
        self.assertEqual(isinstance(post['feed_rank'], int), True)

        # Ensure the post's id is an integer
        self.assertEqual(isinstance(post['id'], int), True)

        # Ensure the post's link is a string
        self.assertEqual(isinstance(post['link'], str), True)

        # Ensure the post's point count is an integer
        self.assertEqual(isinstance(post['point_count'], int), True)

        # Ensure the post's title is a string
        self.assertEqual(isinstance(post['title'], str), True)

        # Ensure the post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(any(type in post['type'] for type in types), True)

        # Ensure the post's username is a string
        self.assertEqual(isinstance(post['username'], str), True)

    def test_tree_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/deepest_comment_tree'
            )
        post = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)

        # Ensure the post's comment count is an integer
        self.assertEqual(isinstance(post['comment_count'], int), True)

        # Ensure the tree is a dictionary
        self.assertEqual(isinstance(post['comment_tree'], dict), True)

        # Ensure the top comment's child comment in the comment tree is a
        # dictionary
        self.assertEqual(isinstance(
            post['comment_tree']['child_comment'], (dict, type(None))), True)

        # Ensure the top comment's content in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['content'],
            (str, type(None))), True)

        # Ensure the top comment's timestamp in the comment tree matches GMT
        # format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(bool(
            timestamp_pattern.match(post['comment_tree']['created'])), True)

        # Ensure the top comment's id in the comment tree is an integer
        self.assertEqual(isinstance(post['comment_tree']['id'],
            (int, type(None))), True)

        # Ensure the top comment's username in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['username'],
            (str, type(None))), True)

        # Ensure the post's created timestamp matches GMT format
        self.assertEqual(bool(timestamp_pattern.match(post['created'])), True)

        # Ensure the post's feed rank is an integer
        self.assertEqual(isinstance(post['feed_rank'], int), True)

        # Ensure the post's id is an integer
        self.assertEqual(isinstance(post['id'], int), True)

        # Ensure the post's link is a string
        self.assertEqual(isinstance(post['link'], str), True)

        # Ensure the post's point count is an integer
        self.assertEqual(isinstance(post['point_count'], int), True)

        # Ensure the post's title is a string
        self.assertEqual(isinstance(post['title'], str), True)

        # Ensure the post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(any(type in post['type'] for type in types), True)

        # Ensure the post's username is a string
        self.assertEqual(isinstance(post['username'], str), True)

    def test_tree_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/deepest_comment_tree'
            )
        post = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)

        # Ensure the post's comment count is an integer
        self.assertEqual(isinstance(post['comment_count'], int), True)

        # Ensure the tree is a dictionary
        self.assertEqual(isinstance(post['comment_tree'], dict), True)

        # Ensure the top comment's child comment in the comment tree is a
        # dictionary
        self.assertEqual(isinstance(
            post['comment_tree']['child_comment'], (dict, type(None))), True)

        # Ensure the top comment's content in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['content'],
            (str, type(None))), True)

        # Ensure the top comment's timestamp in the comment tree matches GMT
        # format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(bool(
            timestamp_pattern.match(post['comment_tree']['created'])), True)

        # Ensure the top comment's id in the comment tree is an integer
        self.assertEqual(isinstance(post['comment_tree']['id'],
            (int, type(None))), True)

        # Ensure the top comment's username in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['username'],
            (str, type(None))), True)

        # Ensure the post's created timestamp matches GMT format
        self.assertEqual(bool(timestamp_pattern.match(post['created'])), True)

        # Ensure the post's feed rank is an integer
        self.assertEqual(isinstance(post['feed_rank'], int), True)

        # Ensure the post's id is an integer
        self.assertEqual(isinstance(post['id'], int), True)

        # Ensure the post's link is a string
        self.assertEqual(isinstance(post['link'], str), True)

        # Ensure the post's point count is an integer
        self.assertEqual(isinstance(post['point_count'], int), True)

        # Ensure the post's title is a string
        self.assertEqual(isinstance(post['title'], str), True)

        # Ensure the post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(any(type in post['type'] for type in types), True)

        # Ensure the post's username is a string
        self.assertEqual(isinstance(post['username'], str), True)

    def test_tree_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/deepest_comment_tree'
            )
        post = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)

        # Ensure the post's comment count is an integer
        self.assertEqual(isinstance(post['comment_count'], int), True)

        # Ensure the tree is a dictionary
        self.assertEqual(isinstance(post['comment_tree'], dict), True)

        # Ensure the top comment's child comment in the comment tree is a
        # dictionary
        self.assertEqual(isinstance(
            post['comment_tree']['child_comment'], (dict, type(None))), True)

        # Ensure the top comment's content in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['content'],
            (str, type(None))), True)

        # Ensure the top comment's timestamp in the comment tree matches GMT
        # format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(bool(
            timestamp_pattern.match(post['comment_tree']['created'])), True)

        # Ensure the top comment's id in the comment tree is an integer
        self.assertEqual(isinstance(post['comment_tree']['id'],
            (int, type(None))), True)

        # Ensure the top comment's username in the comment tree is a string
        self.assertEqual(isinstance(post['comment_tree']['username'],
            (str, type(None))), True)

        # Ensure the post's created timestamp matches GMT format
        self.assertEqual(bool(timestamp_pattern.match(post['created'])), True)

        # Ensure the post's feed rank is an integer
        self.assertEqual(isinstance(post['feed_rank'], int), True)

        # Ensure the post's id is an integer
        self.assertEqual(isinstance(post['id'], int), True)

        # Ensure the post's link is a string
        self.assertEqual(isinstance(post['link'], str), True)

        # Ensure the post's point count is an integer
        self.assertEqual(isinstance(post['point_count'], int), True)

        # Ensure the post's title is a string
        self.assertEqual(isinstance(post['title'], str), True)

        # Ensure the post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(any(type in post['type'] for type in types), True)

        # Ensure the post's username is a string
        self.assertEqual(isinstance(post['username'], str), True)


# Test /api/hacker_news/stats/<time_period>/posts_highest_comment_count
# endpoint [GET]
class TestPostsHighestCommentCount(HackerNewsTestCase):
    def test_posts_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_comment_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_comment_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_comment_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_comment_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_comment_count',
            query_string=query
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(posts), 2)


# Test /api/hacker_news/stats/<time_period>/posts_highest_point_count endpoint
# [GET]
class TestPostsHighestPointCount(HackerNewsTestCase):
    def test_posts_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_point_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_point_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_point_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_point_count'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 1)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period +
            '/posts_highest_point_count',
            query_string=query
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(posts), 2)


# Test /api/hacker_news/stats/<time_period>/post_types endpoint [GET]
class TestPostTypes(HackerNewsTestCase):
    def test_types_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/post_types'
            )
        post_types = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)

        # Ensure each type is one of the post types ('article', 'job', 'ask',
        # 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(any(type in post_type['type'] for type in types)
            for post_type in post_types), True)

        # Ensure each type count is an integer
        self.assertEqual(all(isinstance(
            post_type['type_count'], int) for post_type in post_types), True)

    def test_types_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/post_types'
            )
        post_types = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)

        # Ensure each type is one of the post types ('article', 'job', 'ask',
        # 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(any(type in post_type['type'] for type in types)
            for post_type in post_types), True)

        # Ensure each type count is an integer
        self.assertEqual(all(isinstance(
            post_type['type_count'], int) for post_type in post_types), True)

    def test_types_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/post_types'
            )
        post_types = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)

        # Ensure each type is one of the post types ('article', 'job', 'ask',
        # 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(any(type in post_type['type'] for type in types)
            for post_type in post_types), True)

        # Ensure each type count is an integer
        self.assertEqual(all(isinstance(
            post_type['type_count'], int) for post_type in post_types), True)

    def test_types_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/post_types'
            )
        post_types = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(post_types), 4)

        # Ensure each type is one of the post types ('article', 'job', 'ask',
        # 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(any(type in post_type['type'] for type in types)
            for post_type in post_types), True)

        # Ensure each type count is an integer
        self.assertEqual(all(isinstance(
            post_type['type_count'], int) for post_type in post_types), True)


# Test /api/hacker_news/stats/<time_period>/title_words endpoint [GET]
class TestTitleWords(HackerNewsTestCase):
    def test_words_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/title_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/title_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/title_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/title_words'
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(words), 1)

        # Ensure each word is a string
        self.assertEqual(all(isinstance(
            word['word'], str) for word in words), True)

        # Ensure each word's ndoc is an integer
        self.assertEqual(all(
            isinstance(word['ndoc'], int) for word in words), True)

        # Ensure each word's nentry is an integer
        self.assertEqual(all(
            isinstance(word['nentry'], int) for word in words), True)

    def test_words_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/title_words',
            query_string=query
            )
        words = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(words), 2)


# Test /api/hacker_news/stats/<time_period>/top_posts endpoint [GET]
class TestTopPosts(HackerNewsTestCase):
    def test_posts_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_posts'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 3)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_posts'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 3)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_posts'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 3)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_posts'
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts), 3)

        # Ensure each post's comment count is an integer
        self.assertEqual(all(isinstance(
            post['comment_count'], int) for post in posts), True)

        # Ensure each post's created timestamp matches GMT format
        timestamp_pattern = re.compile(
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun), (?:[0-2][0-9]|3[01]) ' +
            '(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) \d{4} ' +
            '(?:[01][0-9]|2[0-3]):[012345][0-9]:[012345][0-9] GMT'
            )
        self.assertEqual(all(bool(timestamp_pattern.match(
            post['created'])) for post in posts), True)

        # Ensure each post's feed rank is an integer
        self.assertEqual(all(
            isinstance(post['feed_rank'], int) for post in posts), True)

        # Ensure each post's id is an integer
        self.assertEqual(all(
            isinstance(post['id'], int) for post in posts), True)

        # Ensure each post's link is a string
        self.assertEqual(all(
            isinstance(post['link'], str) for post in posts), True)

        # Ensure each post's point count is an integer
        self.assertEqual(all(
            isinstance(post['point_count'], int) for post in posts), True)

        # Ensure each post's title is a string
        self.assertEqual(all(
            isinstance(post['title'], str) for post in posts), True)

        # Ensure each post's type is one of the post types ('article', 'job',
        # 'ask', 'show')
        types = ['article', 'job', 'ask', 'show']

        self.assertEqual(all(
            any(type in post['type'] for type in types) for post in posts),
            True)

        # Ensure each post's username is a string
        self.assertEqual(all(isinstance(
            post['username'], str) for post in posts), True)

        # Ensure each post's website is a string
        self.assertEqual(all(isinstance(
            post['website'], str) for post in posts), True)

    def test_posts_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_posts',
            query_string=query
            )
        posts = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(posts), 2)


# Test /api/hacker_news/stats/<time_period>/top_websites endpoint [GET]
class TestTopWebsites(HackerNewsTestCase):
    def test_websites_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_websites'
            )
        websites = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(websites), 1)

        # Ensure each link count is an integer
        self.assertEqual(all(isinstance(
            website['link_count'], int) for website in websites), True)

        # Ensure each website is a string
        self.assertEqual(all(isinstance(
            website['website'], str) for website in websites), True)

    def test_websites_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_websites'
            )
        websites = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(websites), 1)

        # Ensure each link count is an integer
        self.assertEqual(all(isinstance(
            website['link_count'], int) for website in websites), True)

        # Ensure each website is a string
        self.assertEqual(all(isinstance(
            website['website'], str) for website in websites), True)

    def test_websites_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_websites'
            )
        websites = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(websites), 1)

        # Ensure each link count is an integer
        self.assertEqual(all(isinstance(
            website['link_count'], int) for website in websites), True)

        # Ensure each website is a string
        self.assertEqual(all(isinstance(
            website['website'], str) for website in websites), True)

    def test_websites_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_websites'
            )
        websites = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(websites), 1)

        # Ensure each link count is an integer
        self.assertEqual(all(isinstance(
            website['link_count'], int) for website in websites), True)

        # Ensure each website is a string
        self.assertEqual(all(isinstance(
            website['website'], str) for website in websites), True)

    def test_websites_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/top_websites',
            query_string=query
            )
        websites = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(websites), 2)


# Test /api/hacker_news/stats/<time_period>/users_most_comments endpoint [GET]
class TestUsersMostComments(HackerNewsTestCase):
    def test_users_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_comments'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_comments'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_comments'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_comments'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_comments',
            query_string=query
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(users), 2)


# Test /api/hacker_news/stats/<time_period>/users_most_posts endpoint [GET]
class TestUsersMostPosts(HackerNewsTestCase):
    def test_users_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_posts'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's post count is an integer
        self.assertEqual(all(isinstance(
            user['post_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

    def test_users_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_posts'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's post count is an integer
        self.assertEqual(all(isinstance(
            user['post_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

    def test_users_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_posts'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's post count is an integer
        self.assertEqual(all(isinstance(
            user['post_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

    def test_users_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_posts'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's post count is an integer
        self.assertEqual(all(isinstance(
            user['post_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

    def test_users_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_posts',
            query_string=query
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(users), 2)


# Test /api/hacker_news/stats/<time_period>/users_most_words endpoint [GET]
class TestUsersMostWords(HackerNewsTestCase):
    def test_users_get_hour(self):
        # Arrange
        time_period = 'hour'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_words'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_day(self):
        # Arrange
        time_period = 'day'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_words'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_week(self):
        # Arrange
        time_period = 'week'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_words'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_all(self):
        # Arrange
        time_period = 'all'

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_words'
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(users), 1)

        # Ensure each user's comment count is an integer
        self.assertEqual(all(isinstance(
            user['comment_count'], int) for user in users), True)

        # Ensure each user's username is a string
        self.assertEqual(all(isinstance(
            user['username'], str) for user in users), True)

        # Ensure each user's word count is an integer
        self.assertEqual(all(isinstance(
            user['word_count'], int) for user in users), True)

    def test_users_get_count(self):
        # Arrange
        time_period = 'all'
        query = {'count': 2}

        # Act
        response = self.client.get(
            '/api/hacker_news/stats/' + time_period + '/users_most_words',
            query_string=query
            )
        users = json.loads(response.get_data(as_text=True))

        # Assert
        self.assertEqual(len(users), 2)
