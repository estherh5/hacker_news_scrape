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


@app.route('/api/hacker_news/stats/<time_period>/comment_highest_word_count',
    methods=['GET'])
def highest_word_count(time_period):
    # Retrieve comment with highest word count from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_comment_highest_word_count(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/comment_word',
    methods=['GET'])
def comment_word(time_period):
    # Retrieve highest-frequency word used in comments from specified Hacker
    # News scrapes ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_most_frequent_comment_word(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/deepest_comment_tree',
    methods=['GET'])
def deepest_comment_tree(time_period):
    # Retrieve deepest comment tree from specified Hacker News scrapes ('hour',
    # 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_deepest_comment_tree(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/highest_comment_count',
    methods=['GET'])
def highest_comment_count(time_period):
    # Retrieve post with highest comment count from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_highest_comment_count(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/highest_point_count',
    methods=['GET'])
def highest_point_count(time_period):
    # Retrieve post with highest point count from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_highest_point_count(hacker_news.get_feeds(
            time_period))


@app.route('/api/hacker_news/stats/<time_period>/post_types',
    methods=['GET'])
def post_types(time_period):
    # Retrieve count of each type of post from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_post_types(hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/title_word',
    methods=['GET'])
def title_word(time_period):
    # Retrieve highest-frequency word used in post titles from specified
    # Hacker News scrapes ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_most_frequent_title_word(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/top_five_posts',
    methods=['GET'])
def top_five_posts(time_period):
    # Retrieve top five ranked posts from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_top_five_posts(hacker_news.get_feeds(
            time_period))


@app.route('/api/hacker_news/stats/<time_period>/top_website',
    methods=['GET'])
def top_website(time_period):
    # Retrieve top website that posts were posted from from specified Hacker
    # News scrapes ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_top_website(hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/user_most_comments',
    methods=['GET'])
def user_most_comments(time_period):
    # Retrieve user with most comments from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_user_with_most_comments(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/user_most_posts',
    methods=['GET'])
def user_most_posts(time_period):
    # Retrieve user with most posts from specified Hacker News scrapes
    # ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_user_with_most_posts(
            hacker_news.get_feeds(time_period))


@app.route('/api/hacker_news/stats/<time_period>/user_most_words',
    methods=['GET'])
def user_most_words(time_period):
    # Retrieve user with most words in comments from specified Hacker News
    # scrapes ('hour', 'day', 'week', 'all')
    if request.method == 'GET':
        return hacker_news.get_user_with_most_words_in_comments(
            hacker_news.get_feeds(time_period))
