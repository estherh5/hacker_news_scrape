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

    # Create 'post_type' type, database tables, and custom text dictionary for
    # detecting stop words without word stemming
    cursor.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS
                          (SELECT 1
                             FROM pg_type
                            WHERE typname = 'post_type')
                     THEN CREATE TYPE post_type
                       AS ENUM ('article', 'ask', 'job', 'show');
            END IF;
        END
        $$;

        CREATE TABLE IF NOT EXISTS feed (
            PRIMARY KEY (id),
            created TIMESTAMP DEFAULT (now() at time zone 'utc') NOT NULL,
            id      SERIAL    NOT NULL
        );

        CREATE INDEX IF NOT EXISTS feed_id_index
               ON feed (id);

        CREATE TABLE IF NOT EXISTS post (
            PRIMARY KEY (id),
            created  TIMESTAMP NOT NULL,
            id       INT       NOT NULL,
            link     TEXT      NOT NULL,
            title    TEXT      NOT NULL,
            type     POST_TYPE NOT NULL,
            username TEXT,
            website  TEXT
        );

        CREATE INDEX IF NOT EXISTS post_index
               ON post (id, username);

        CREATE TABLE IF NOT EXISTS feed_post (
            comment_count INT DEFAULT 0           NOT NULL,
            feed_id       INT REFERENCES feed(id) ON DELETE CASCADE,
            feed_rank     INT NOT NULL,
            point_count   INT DEFAULT 0           NOT NULL,
            post_id       INT REFERENCES post(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS feed_post_index
               ON feed_post (comment_count, feed_id, feed_rank, point_count,
                             post_id);

        CREATE TABLE IF NOT EXISTS comment (
            PRIMARY KEY (id),
            content        TEXT      NOT NULL,
            created        TIMESTAMP NOT NULL,
            id             INT       NOT NULL,
            level          INT       NOT NULL,
            parent_comment INT       REFERENCES comment(id) ON DELETE CASCADE,
            post_id        INT       REFERENCES post(id)    ON DELETE CASCADE,
            username       TEXT      NOT NULL,
            word_count     INT       DEFAULT 0              NOT NULL
        );

        CREATE INDEX IF NOT EXISTS comment_index
               ON comment (id, level, parent_comment, post_id, username,
                           word_count);

        CREATE TABLE IF NOT EXISTS feed_comment (
            comment_id INT REFERENCES comment(id) ON DELETE CASCADE,
            feed_id    INT REFERENCES feed(id)    ON DELETE CASCADE,
            feed_rank  INT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS feed_comment_index
               ON feed_comment (comment_id, feed_id, feed_rank);

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
    hacker_news.scrape_loop()
