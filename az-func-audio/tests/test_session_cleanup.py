import datetime
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture(autouse=True)
def freeze_now(monkeypatch):
    # Freeze utcnow for deterministic tests
    fixed = datetime.datetime(2025, 8, 23, 15, 0, 0)
    class FixedDatetime(datetime.datetime):
        @classmethod
        def utcnow(cls):
            return fixed

    monkeypatch.setattr('services.session_cleanup.datetime', FixedDatetime)
    yield


def make_fake_container(items):
    container = MagicMock()
    # query_items returns an iterator over items
    container.query_items.return_value = iter(items)
    container.upsert_item = MagicMock()
    return container


def test_session_cleanup_no_items(monkeypatch, caplog):
    # Setup fake cosmos structure: client -> database -> container
    fake_container = make_fake_container([])
    fake_database = MagicMock()
    fake_database.get_container_client.return_value = fake_container
    fake_client = MagicMock()
    fake_client.get_database_client.return_value = fake_database

    # Patch the factory in cosmos_service (session_cleanup imports it lazily)
    monkeypatch.setattr('services.cosmos_service.get_cosmos_client', lambda: fake_client)

    # Ensure AppConfig provides a known database name (session_cleanup imports from config)
    class DummyConfig:
        cosmos_database = 'VoiceDB'
        cosmos_sessions_container = 'voice_user_sessions'

    monkeypatch.setattr('config.AppConfig', DummyConfig)

    from services import session_cleanup

    caplog.clear()
    session_cleanup.main(None)

    # No upserts should have been called
    assert fake_container.upsert_item.call_count == 0
    assert 'no stale sessions found' in caplog.text.lower()


def test_session_cleanup_closes_items(monkeypatch, caplog):
    # Create two fake session documents
    items = [
        {'id': 's1', 'status': 'open', 'event_type': 'session_start', 'last_heartbeat': '2025-08-23T14:40:00'},
        {'id': 's2', 'status': 'open', 'event_type': 'session_start', 'last_heartbeat': '2025-08-23T14:30:00'},
    ]

    fake_container = make_fake_container(items)
    fake_database = MagicMock()
    fake_database.get_container_client.return_value = fake_container
    fake_client = MagicMock()
    fake_client.get_database_client.return_value = fake_database

    monkeypatch.setattr('services.cosmos_service.get_cosmos_client', lambda: fake_client)

    class DummyConfig:
        cosmos_database = 'VoiceDB'
        cosmos_sessions_container = 'voice_user_sessions'

    monkeypatch.setattr('config.AppConfig', DummyConfig)

    from services import session_cleanup

    caplog.clear()
    session_cleanup.main(None)

    # upsert_item should have been called twice
    assert fake_container.upsert_item.call_count == 2
    assert 'closed stale session: s1' in caplog.text.lower()
    assert 'closed stale session: s2' in caplog.text.lower()
