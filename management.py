#!/usr/bin/env python3
import argparse
import boto3
import getpass
import os
import pathlib
import subprocess

from crontab import CronTab
from datetime import datetime, timezone

from hacker_news import hacker_news, models


def initialize_database():
    # Connect to database
    session = models.Session()

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


def backup_database():
    # Define backup file path
    now = str(datetime.now().isoformat())
    file_path = pathlib.Path(f'{os.environ["BACKUP_DIR"]}/{now}')
    file_path.parent.mkdir(parents=True, exist_ok=True)

    # Define command to run to back up database
    command = f'pg_dump {os.environ["DB_CONNECTION"]} -Fc -f {file_path}'

    # Dump database backup to file path
    ps = subprocess.check_output(
        command, shell=True,
        cwd=os.path.dirname(os.path.realpath(__file__))
    )
    print(f'Backup saved to {str(file_path)}')

    # Upload file to s3 backup bucket
    s3 = boto3.client(
        's3',
        aws_access_key_id=os.environ['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=os.environ['AWS_SECRET_ACCESS_KEY']
    )
    bucket_name = os.environ['S3_BUCKET']
    bucket_folder = os.environ['S3_BACKUP_DIR']

    data = open(file_path, 'rb')

    s3.put_object(Bucket=bucket_name, Key=bucket_folder + now, Body=data)

    print(f'Backup saved to S3 {bucket_name}/{bucket_folder} bucket')

    return


def schedule_weekly_backup():
    # Initiate CronTab instance for current user
    user = getpass.getuser()
    cron = CronTab(user)

    # Create weekly job to back up database
    job = cron.new(
        command='export WORKON_HOME=~/.virtualenvs; ' +
        'VIRTUALENVWRAPPER_PYTHON=/usr/local/bin/python3; ' +
        'source /usr/local/bin/virtualenvwrapper.sh; ' +
        'workon ' + os.environ['VIRTUAL_ENV_NAME'] + '; ' +
        'source ~/.virtualenvs/' + os.environ['VIRTUAL_ENV_NAME'] +
        '/bin/postactivate; python ' + os.path.abspath(__file__) + ' backup_db'
        )
    job.minute.on(0)
    job.hour.on(0)
    job.dow.on(0)

    cron.write()

    print(
        'Weekly backup scheduled for ' + os.environ['DB_NAME'] + ' database.'
        )

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
if args.action == 'backup_db':
    # Only backup database on Sunday
    if datetime.now(timezone.utc).weekday() == 6:
        backup_database()
if args.action == 'sched_backup':
    schedule_weekly_backup()
