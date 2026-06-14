import unittest

from hacker_news.models import normalize_database_url


class NormalizeDatabaseUrlTest(unittest.TestCase):
    def test_converts_legacy_heroku_postgres_scheme(self):
        self.assertEqual(
            normalize_database_url(
                'postgres://user:password@example.com:5432/database'
            ),
            'postgresql://user:password@example.com:5432/database',
        )

    def test_preserves_modern_postgresql_scheme(self):
        database_url = (
            'postgresql://user:password@example.com:5432/database'
        )
        self.assertEqual(normalize_database_url(database_url), database_url)

    def test_preserves_empty_value(self):
        self.assertIsNone(normalize_database_url(None))
