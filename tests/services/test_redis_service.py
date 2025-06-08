import pytest
from unittest import mock
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services.redis_service import get_redis_client # Original import
from core.config import settings as app_settings # Alias to avoid conflict
import redis # Import for redis.exceptions.ConnectionError

@pytest.fixture(autouse=True)
def mock_redis_env_settings(monkeypatch): # Changed fixture name
    monkeypatch.setattr(app_settings, 'REDIS_HOST', 'mockhost') # Use different values to ensure patch works
    monkeypatch.setattr(app_settings, 'REDIS_PORT', 1234)
    monkeypatch.setattr(app_settings, 'REDIS_PASSWORD', 'mockpassword')

@mock.patch('redis.Redis') # Patch redis.Redis from the redis module
def test_get_redis_client_success(MockRedis):
    # Reset global redis_client before test for isolation
    from services import redis_service as rs_module # import the module itself
    rs_module.redis_client = None

    mock_instance = MockRedis.return_value
    mock_instance.ping.return_value = True

    client = rs_module.get_redis_client() # Call the function from the module
    assert client is not None
    MockRedis.assert_called_once_with(
        host=app_settings.REDIS_HOST, # Check against patched settings
        port=app_settings.REDIS_PORT,
        password=app_settings.REDIS_PASSWORD,
        db=0,
        decode_responses=True
    )
    mock_instance.ping.assert_called_once()

    client2 = rs_module.get_redis_client()
    assert client is client2 # Singleton behavior

    rs_module.redis_client = None # Cleanup


@mock.patch('redis.Redis')
def test_get_redis_client_connection_error(MockRedis):
    from services import redis_service as rs_module
    rs_module.redis_client = None

    MockRedis.return_value.ping.side_effect = redis.exceptions.ConnectionError("Test connection error")

    client = rs_module.get_redis_client()
    assert client is None
    MockRedis.assert_called_once()
    MockRedis.return_value.ping.assert_called_once()

    rs_module.redis_client = None
