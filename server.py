import os

from flask import Flask, request
from flask_cors import CORS

from hacker_news import hacker_news

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
if os.environ['ENV_TYPE'] == 'Dev':
    app.config['DEBUG'] = True


@app.route('/api/hacker_news/comment/<comment_id>', methods=['GET'])
def comment(comment_id):
    # Retrieve latest version of comment from Hacker News scrapes
    if request.method == 'GET':
        return hacker_news.get_comment(comment_id)


@app.route('/api/hacker_news/post/<post_id>', methods=['GET'])
def post(post_id):
    # Retrieve latest version of post from Hacker News scrapes
    if request.method == 'GET':
        return hacker_news.get_post(post_id)


@app.route('/api/hacker_news/stats/<time_period>/average_comment_count',
    methods=['GET'])
def average_comment_count(time_period):
    # Retrieve average comment count from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_average_comment_count(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/average_comment_tree_depth',
    methods=['GET'])
def average_comment_tree_depth(time_period):
    # Retrieve average comment tree depth from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_average_comment_tree_depth(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/average_comment_word_count',
    methods=['GET'])
def average_word_count(time_period):
    # Retrieve average comment word count from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_average_comment_word_count(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/average_point_count',
    methods=['GET'])
def average_point_count(time_period):
    # Retrieve average point count from specified Hacker News scrapes ('hour',
    # 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_average_point_count(hacker_news.get_feeds(
            time_period))


@app.route('/api/hacker_news/stats/<time_period>/comments_highest_word_count',
    methods=['GET'])
def highest_word_count(time_period):
    # Retrieve comments with highest word counts from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all'); optional count query param
    # specifies number of comments to return
    if request.method == 'GET':
        return hacker_news.get_comments_with_highest_word_counts(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/comment_words',
    methods=['GET'])
def comment_word(time_period):
    # Retrieve highest-frequency words used in comments from specified Hacker
    # News scrapes ('hour', 'day', 'week', 'all'); optional count query param
    # specifies number of highest-frequency words to return
    if request.method == 'GET':
        return hacker_news.get_most_frequent_comment_words(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/deepest_comment_tree',
    methods=['GET'])
def deepest_comment_tree(time_period):
    # Retrieve deepest comment tree from specified Hacker News scrapes ('hour',
    # 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_deepest_comment_tree(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/posts_highest_comment_count',
    methods=['GET'])
def highest_comment_count(time_period):
    # Retrieve posts with highest comment counts from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all'); optional count query param
    # specifies number of posts to return
    if request.method == 'GET':
        return hacker_news.get_posts_with_highest_comment_counts(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/posts_highest_point_count',
    methods=['GET'])
def highest_point_count(time_period):
    # Retrieve posts with highest point count from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all'); optional count query param
    # specifies number of posts to return
    if request.method == 'GET':
        return hacker_news.get_posts_with_highest_point_counts(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/post_types',
    methods=['GET'])
def post_types(time_period):
    # Retrieve count of each type of post from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_post_types(hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/title_words',
    methods=['GET'])
def title_word(time_period):
    # Retrieve highest frequency word useds in post titles from specified
    # Hacker News scrapes ('hour', 'day', 'week', 'all'); optional count query
    # param specifies number of words to return
    if request.method == 'GET':
        return hacker_news.get_most_frequent_title_words(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/top_posts', methods=['GET'])
def top_posts(time_period):
    # Retrieve top ranked posts from specified Hacker News scrapes ('hour',
    # 'day', 'week', 'all'); optional count query param specifies number of
    # posts to return
    if request.method == 'GET':
        return hacker_news.get_top_posts(hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/top_websites',
    methods=['GET'])
def top_website(time_period):
    # Retrieve top websites that posts were posted from from specified Hacker
    # News scrapes ('hour', 'day', 'week', 'all'); optional count query param
    # specifies number of websites to return
    if request.method == 'GET':
        return hacker_news.get_top_websites(hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/users_most_comments',
    methods=['GET'])
def user_most_comments(time_period):
    # Retrieve users with most comments from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all'); optional count query param specifies
    # number of users to return
    if request.method == 'GET':
        return hacker_news.get_users_with_most_comments(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/users_most_posts',
    methods=['GET'])
def user_most_posts(time_period):
    # Retrieve users with most posts from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all'); optional count query param specifies
    # number of users to return
    if request.method == 'GET':
        return hacker_news.get_users_with_most_posts(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/users_most_words',
    methods=['GET'])
def user_most_words(time_period):
    # Retrieve users with most words in comments from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all'); optional count query param
    # specifies number of users to return
    if request.method == 'GET':
        return hacker_news.get_users_with_most_words_in_comments(
            hacker_news.get_feeds(time_period))
