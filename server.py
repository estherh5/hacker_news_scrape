import os

from flask import Flask, abort
from flask_cors import CORS

from hacker_news import hacker_news

VALID_TIME_PERIODS = {'hour', 'day', 'week', 'all'}


def create_app(config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        DEBUG=os.getenv('ENV_TYPE', '').lower() == 'dev',
        JSON_SORT_KEYS=False,
    )
    if config:
        app.config.update(config)

    CORS(app, resources={r'/api/*': {'origins': '*'}})

    def feeds_for(time_period):
        if time_period not in VALID_TIME_PERIODS:
            abort(404, description='Unknown time period')
        return hacker_news.get_feeds(time_period)

    @app.get('/api/hacker_news/comment/<int:comment_id>')
    def comment(comment_id):
        return hacker_news.get_comment(comment_id)

    @app.get('/api/hacker_news/post/<int:post_id>')
    def post(post_id):
        return hacker_news.get_post(post_id)

    @app.get(
        '/api/hacker_news/stats/<time_period>/average_comment_count'
    )
    def average_comment_count(time_period):
        return hacker_news.get_average_comment_count(feeds_for(time_period))

    @app.get(
        '/api/hacker_news/stats/<time_period>/average_comment_tree_depth'
    )
    def average_comment_tree_depth(time_period):
        return hacker_news.get_average_comment_tree_depth(
            feeds_for(time_period)
        )

    @app.get(
        '/api/hacker_news/stats/<time_period>/average_comment_word_count'
    )
    def average_word_count(time_period):
        return hacker_news.get_average_comment_word_count(
            feeds_for(time_period)
        )

    @app.get('/api/hacker_news/stats/<time_period>/average_point_count')
    def average_point_count(time_period):
        return hacker_news.get_average_point_count(feeds_for(time_period))

    @app.get(
        '/api/hacker_news/stats/<time_period>/comments_highest_word_count'
    )
    def highest_word_count(time_period):
        return hacker_news.get_comments_with_highest_word_counts(
            feeds_for(time_period)
        )

    @app.get('/api/hacker_news/stats/<time_period>/comment_words')
    def comment_words(time_period):
        return hacker_news.get_most_frequent_comment_words(
            feeds_for(time_period)
        )

    @app.get('/api/hacker_news/stats/<time_period>/deepest_comment_tree')
    def deepest_comment_tree(time_period):
        return hacker_news.get_deepest_comment_tree(feeds_for(time_period))

    @app.get(
        '/api/hacker_news/stats/<time_period>/posts_highest_comment_count'
    )
    def highest_comment_count(time_period):
        return hacker_news.get_posts_with_highest_comment_counts(
            feeds_for(time_period)
        )

    @app.get(
        '/api/hacker_news/stats/<time_period>/posts_highest_point_count'
    )
    def highest_point_count(time_period):
        return hacker_news.get_posts_with_highest_point_counts(
            feeds_for(time_period)
        )

    @app.get('/api/hacker_news/stats/<time_period>/post_types')
    def post_types(time_period):
        return hacker_news.get_post_types(feeds_for(time_period))

    @app.get('/api/hacker_news/stats/<time_period>/title_words')
    def title_words(time_period):
        return hacker_news.get_most_frequent_title_words(
            feeds_for(time_period)
        )

    @app.get('/api/hacker_news/stats/<time_period>/top_posts')
    def top_posts(time_period):
        return hacker_news.get_top_posts(feeds_for(time_period))

    @app.get('/api/hacker_news/stats/<time_period>/top_websites')
    def top_websites(time_period):
        return hacker_news.get_top_websites(feeds_for(time_period))

    @app.get('/api/hacker_news/stats/<time_period>/users_most_comments')
    def users_most_comments(time_period):
        return hacker_news.get_users_with_most_comments(
            feeds_for(time_period)
        )

    @app.get('/api/hacker_news/stats/<time_period>/users_most_posts')
    def users_most_posts(time_period):
        return hacker_news.get_users_with_most_posts(feeds_for(time_period))

    @app.get('/api/hacker_news/stats/<time_period>/users_most_words')
    def users_most_words(time_period):
        return hacker_news.get_users_with_most_words_in_comments(
            feeds_for(time_period)
        )

    return app


app = create_app()
