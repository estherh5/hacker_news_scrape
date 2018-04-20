#!/usr/bin/env python3
import argparse
import getpass
import os
import psycopg2 as pg

from crontab import CronTab

from hacker_news import hacker_news


def initialize_database():
    # Set up database connection with environment variable
    conn = pg.connect(os.environ['DB_CONNECTION'])

    cursor = conn.cursor()

    # Create 'post_type' type and database tables
    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'post_type')
                THEN CREATE TYPE post_type
                AS ENUM ('article', 'ask', 'job', 'show');
            END IF;
        END
        $$;

        CREATE TABLE IF NOT EXISTS feed (
        id SERIAL PRIMARY KEY,
        created timestamp NOT NULL DEFAULT (now() at time zone 'utc'));

        CREATE TABLE IF NOT EXISTS post (
        id SERIAL PRIMARY KEY,
        created timestamp NOT NULL,
        feed_id int REFERENCES feed(id) ON DELETE CASCADE,
        feed_rank int NOT NULL,
        link text NOT NULL,
        point_count int NOT NULL DEFAULT 0,
        post_id int NOT NULL,
        title text NOT NULL,
        type post_type NOT NULL,
        username text,
        website text);

        CREATE TABLE IF NOT EXISTS comment (
        id SERIAL PRIMARY KEY,
        comment_id int NOT NULL,
        content text NOT NULL,
        created timestamp NOT NULL,
        feed_id int REFERENCES feed(id) ON DELETE CASCADE,
        feed_rank int NOT NULL,
        level int NOT NULL,
        parent int NOT NULL,
        post_id int REFERENCES post(id) ON DELETE CASCADE,
        username text NOT NULL);
        """
        )

    conn.commit()

    cursor.close()
    conn.close()

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
    hacker_news.scrape()
