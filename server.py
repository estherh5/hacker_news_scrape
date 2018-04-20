import os

from flask import Flask, request
from flask_cors import CORS

from hacker_news import hacker_news

app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}})
if os.environ['ENV_TYPE'] == 'Dev':
    app.config['DEBUG'] = True


@app.route('/api/hacker_news/post/<post_id>', methods=['GET'])
def post(post_id):
    # Retrieve latest version of post from Hacker News scrapes
    if request.method == 'GET':
        return hacker_news.get_post(post_id)


@app.route('/api/hacker_news/comment/<comment_id>', methods=['GET'])
def comment(comment_id):
    # Retrieve latest version of comment from Hacker News scrapes
    if request.method == 'GET':
        return hacker_news.get_comment(comment_id)


@app.route('/api/hacker_news/stats/hour', methods=['GET'])
def last_hour():
    # Retrieve stats from last hourly Hacker News scrape
    if request.method == 'GET':
        return hacker_news.get_last_hour_stats()


@app.route('/api/hacker_news/stats/day', methods=['GET'])
def last_day():
    # Retrieve stats from last day's Hacker News scrapes
    if request.method == 'GET':
        return hacker_news.get_last_day_stats()


@app.route('/api/hacker_news/stats/all', methods=['GET'])
def all_time():
    # Retrieve stats from all past Hacker News scrapes
    if request.method == 'GET':
        return hacker_news.get_all_time_stats()
