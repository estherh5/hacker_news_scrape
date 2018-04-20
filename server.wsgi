import os
import sys


sys.path.insert(0, '/var/www/html/hacker_news_scrape')  # Server path


def application(environ, start_response):
    os.environ['ENV_TYPE'] = environ.get('ENV_TYPE', '')
    os.environ['VIRTUAL_ENV_NAME'] = environ.get('VIRTUAL_ENV_NAME', '')
    os.environ['DB_CONNECTION'] = environ.get('DB_CONNECTION', '')
    os.environ['DB_NAME'] = environ.get('DB_NAME', '')
    os.environ['DB_USER'] = environ.get('DB_USER', '')
    from server import app as _application

    return _application(environ, start_response)
