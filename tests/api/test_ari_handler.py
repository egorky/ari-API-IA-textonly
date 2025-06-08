import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys # For sys.modules monkeypatching
from pathlib import Path

# Ensure app is discoverable for imports
APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from api import ari_handler # app.api.ari_handler
from core.config import settings # app.core.config
# from services import ai_service # app.services.ai_service, will be mocked

# Mock the vendored ari_py library at the source of its import in ari_handler
@pytest.fixture(autouse=True)
def mock_vendored_ari_py(monkeypatch):
    mock_ari_module = MagicMock()
    # Mock the connect function (no longer async at this level based on prior fixes)
    mock_ari_module.connect = MagicMock()
    mock_ari_module.AriException = type('AriException', (Exception,), {}) # Create a mock AriException class

    mock_client_instance = MagicMock() # This is what connect returns
    mock_client_instance.on_channel_event = MagicMock()
    mock_client_instance.run = MagicMock() # Synchronous run, will be run in executor
    mock_ari_module.connect.return_value = mock_client_instance

    # Patch where ari_handler looks for 'ari_py'
    # Based on ari_handler: from app.vendor import ari_py as ari
    # So we need to patch 'app.vendor.ari_py' if it were a real module being imported.
    # However, since it's 'from app.vendor import ari_py as ari',
    # we patch 'ari' within the 'app.api.ari_handler' module.
    monkeypatch.setattr(ari_handler, 'ari', mock_ari_module, raising=False)
    return mock_ari_module

@pytest.fixture
def mock_db_session_fixture(monkeypatch): # Renamed to avoid conflict with db_session from conftest
    mock_db = MagicMock(spec=Session)
    mock_session_local = MagicMock(return_value=mock_db)
    monkeypatch.setattr(ari_handler, 'SessionLocal', mock_session_local)
    return mock_db


@pytest.mark.asyncio
async def test_on_stasis_start_basic_flow(mock_db_session_fixture, mock_vendored_ari_py):
    mock_channel = AsyncMock() # Methods called on channel should be async
    mock_channel.get.side_effect = lambda key, default=None: {
        'id': 'channel-123',
        'name': 'SIP/test-00000001',
    }.get(key, default)

    # Mock ai_service.get_ai_response
    with patch('app.api.ari_handler.ai_service.get_ai_response', AsyncMock(return_value="Mocked AI Response")) as mock_get_ai_response:
        event_obj_wrapper = {'channel': mock_channel, 'args': ['USER_INPUT=Hello AI', 'UNIQUEID=channel-123']}

        await ari_handler.on_stasis_start(event_obj_wrapper, event_obj_wrapper)

        mock_channel.answer.assert_called_once()
        mock_get_ai_response.assert_called_once()
        call_args = mock_get_ai_response.call_args[1]
        assert call_args['text_input'] == 'Hello AI'
        assert call_args['session_id'] == 'channel-123'
        assert call_args['db'] == mock_db_session_fixture

        mock_channel.setChannelVar.assert_called_once_with(variable='AI_RESPONSE', value="Mocked AI Response")
        mock_db_session_fixture.close.assert_called_once()


@pytest.mark.asyncio
async def test_start_ari_listener(mock_vendored_ari_py): # Renamed from start_ari_listener_task
    ari_handler.ari_client_task = None

    with patch('asyncio.create_task') as mock_create_task:
        ari_handler.start_ari_listener() # Call the corrected function name
        mock_create_task.assert_called_once()

    if ari_handler.ari_client_task and hasattr(ari_handler.ari_client_task, 'cancel'): # Check if it's a task
        if not ari_handler.ari_client_task.done():
            ari_handler.ari_client_task.cancel()
            try:
                await ari_handler.ari_client_task
            except asyncio.CancelledError:
                pass
    ari_handler.ari_client_task = None

@pytest.mark.asyncio
async def test_run_ari_client_with_retry_connects_and_runs(mock_vendored_ari_py):
    mock_client_instance = mock_vendored_ari_py.connect.return_value

    # Mock loop.run_in_executor to run the client.run immediately for the test
    with patch('asyncio.get_event_loop') as mock_get_loop:
        mock_loop_instance = mock_get_loop.return_value
        # Make run_in_executor just call the function directly
        mock_loop_instance.run_in_executor = AsyncMock(side_effect=lambda _, func, *args: func(*args)) # Simplified: runs sync

        task = asyncio.create_task(ari_handler._run_ari_client_with_retry())
        await asyncio.sleep(0.01) # Allow task to start and run one iteration

        mock_vendored_ari_py.connect.assert_called_with(
            settings.ASTERISK_ARI_URL,
            settings.ASTERISK_APP_NAME,
            settings.ASTERISK_ARI_USERNAME,
            settings.ASTERISK_ARI_PASSWORD
        )
        mock_client_instance.on_channel_event.assert_called_with('StasisStart', ari_handler.on_stasis_start)
        # mock_client_instance.run.assert_called_once() # This will be called by run_in_executor

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    ari_handler.ari_client_instance = None
