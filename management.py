#!/usr/bin/env python3
import argparse
import getpass
import os

from crontab import CronTab
from datetime import datetime
from sqlalchemy import create_engine, Column, ForeignKey, Index, Integer, \
    MetaData, String, Table
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.types import Enum, TEXT, TIMESTAMP

from hacker_news import hacker_news, models


def initialize_database():
    # Connect to database
    session = models.Session()

    metadata = MetaData()

    # Create custom text dictionary for detecting stop words without word
    # stemming
    session.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS
                          (SELECT 1
                             FROM pg_ts_dict
                            WHERE dictname = 'simple_english')
                     THEN CREATE TEXT SEARCH DICTIONARY simple_english (
                        TEMPLATE = pg_catalog.simple,
                        STOPWORDS = english
                     );
            END IF;
        END
        $$;

        DO $$
        BEGIN
            IF NOT EXISTS
                          (SELECT 1
                             FROM pg_ts_config
                            WHERE cfgname = 'simple_english')
                     THEN CREATE TEXT SEARCH CONFIGURATION simple_english (
                        COPY = english
                     );
            END IF;
        END
        $$;

        ALTER TEXT SEARCH CONFIGURATION simple_english
            ALTER MAPPING FOR asciihword, asciiword, hword, hword_asciipart,
                              hword_part, word
                         WITH simple_english;
        """
        )

    session.commit()

    session.close()

    print('Database ' + os.environ['DB_NAME'] + ' initialized successfully.')

    return


def schedule_hourly_scrape():
    # Initiate CronTab instance for current user
    user = getpass.getuser()
    cron = CronTab(user)

    # Create hourly job to scrape Hacker News website
    job = cron.new(
        command='export WORKON_HOME=~/.virtualenvs; ' +
        'VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3; ' +
        'source /usr/local/bin/virtualenvwrapper.sh; ' +
        'workon ' + os.environ['VIRTUAL_ENV_NAME'] + '; ' +
        'source ~/.virtualenvs/' + os.environ['VIRTUAL_ENV_NAME'] +
        '/bin/postactivate; python ' + os.path.abspath(__file__) + ' scrape_hn'
        )
    job.minute.on(0)

    cron.write()

    print('Hourly scrape scheduled for Hacker News.')

    return


# Add arguments for initializing database in CLI
parser = argparse.ArgumentParser(description='Management commands')
parser.add_argument('action', type=str, help="an action for the database")
args = parser.parse_args()
if args.action == 'init_db':
    initialize_database()
if args.action == 'sched_scrape':
    schedule_hourly_scrape()
if args.action == 'scrape_hn':
    hacker_news.scrape_loop()
