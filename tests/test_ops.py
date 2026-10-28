from unittest import mock

import pytest

import management
import server


@pytest.fixture
def client():
    with mock.patch.object(server.hacker_news, 'get_feeds', return_value=[]), \
         mock.patch.object(
             server.hacker_news, 'get_average_point_count', return_value={}
         ), \
         mock.patch.object(server.hacker_news, 'get_post', return_value={}):
        yield server.create_app({'TESTING': True}).test_client()


@pytest.mark.parametrize('period', ['hour', 'day', 'week'])
def test_rolling_periods_get_short_cache(client, period):
    r = client.get(f'/api/hacker_news/stats/{period}/average_point_count')
    assert r.status_code == 200
    assert r.headers['Cache-Control'] == (
        'public, s-maxage=300, stale-while-revalidate=3600'
    )


def test_all_period_and_lookups_keep_long_cache(client):
    for path in ('/api/hacker_news/stats/all/average_point_count',
                 '/api/hacker_news/post/1'):
        r = client.get(path)
        assert r.status_code == 200
        assert r.headers['Cache-Control'] == server.CACHE_CONTROL


def _size(mb):
    session = mock.Mock()
    session.execute.return_value.scalar.return_value = int(mb * 1024 * 1024)
    return mock.patch.object(management.models, 'Session',
                             return_value=session)


def test_check_db_size_ok_under_limit(capsys):
    assert management.DB_SIZE_LIMIT_MB == 400
    with _size(399):
        management.check_db_size()
    assert '399.0 MB' in capsys.readouterr().out


def test_check_db_size_exits_over_limit():
    with _size(401), pytest.raises(SystemExit) as e:
        management.check_db_size()
    assert e.value.code != 0
