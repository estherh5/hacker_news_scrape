import unittest
from types import SimpleNamespace
from unittest import mock

from hacker_news import hacker_news


class SerializeQueryTest(unittest.TestCase):
    def test_materializes_rows_before_closing_session(self):
        events = []
        rows = [SimpleNamespace(_mapping={'id': 1})]
        query = mock.Mock()
        query.all.side_effect = lambda: events.append('query') or rows
        session = mock.Mock()
        session.close.side_effect = lambda: events.append('close')

        result = hacker_news.serialize_query(query, session)

        self.assertEqual(result, [{'id': 1}])
        self.assertEqual(events, ['query', 'close'])

    def test_closes_session_when_query_fails(self):
        query = mock.Mock()
        query.all.side_effect = RuntimeError('database error')
        session = mock.Mock()

        with self.assertRaises(RuntimeError):
            hacker_news.serialize_query(query, session)

        session.close.assert_called_once_with()


class GetFeedsTest(unittest.TestCase):
    def test_week_with_no_recent_feeds_returns_latest_feed(self):
        query = mock.Mock()
        latest_query = mock.Mock()
        query.filter.return_value = query
        query.all.return_value = []
        query.order_by.return_value = latest_query
        latest_query.limit.return_value = latest_query
        latest_query.all.return_value = [SimpleNamespace(id=42)]
        session = mock.Mock()
        session.query.return_value = query

        with (
            mock.patch.object(hacker_news.models, 'engine', object()),
            mock.patch.object(
                hacker_news.models, 'Session', return_value=session
            ),
        ):
            result = hacker_news.get_feeds('week')

        self.assertEqual(result, [42])
        session.close.assert_called_once_with()
