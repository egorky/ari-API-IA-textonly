import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPBasicCredentials
from unittest.mock import patch
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core.security import get_current_username
from core.config import Settings # Import the actual Settings class

# Mock settings for testing
@pytest.fixture
def mock_settings_fixture(): # Renamed to avoid conflict with 'settings' import if any
    return Settings(
        WEB_UI_USERNAME="testuser",
        WEB_UI_PASSWORD="testpassword",
        DATABASE_URL="sqlite:///./test_temp_security.db" # Dummy value
        # Ensure all required fields for Settings are provided if it has more
    )

def test_get_current_username_valid(mock_settings_fixture):
    with patch('app.core.security.settings', mock_settings_fixture):
        credentials = HTTPBasicCredentials(username="testuser", password="testpassword")
        username = get_current_username(credentials)
        assert username == "testuser"

def test_get_current_username_invalid_password(mock_settings_fixture):
    with patch('app.core.security.settings', mock_settings_fixture):
        credentials = HTTPBasicCredentials(username="testuser", password="wrongpassword")
        with pytest.raises(HTTPException) as excinfo:
            get_current_username(credentials)
        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.detail == "Incorrect username or password."

def test_get_current_username_invalid_username(mock_settings_fixture):
    with patch('app.core.security.settings', mock_settings_fixture):
        credentials = HTTPBasicCredentials(username="wronguser", password="testpassword")
        with pytest.raises(HTTPException) as excinfo:
            get_current_username(credentials)
        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_username_missing_config():
    # Test case where settings are not configured (empty strings)
    # Create a Settings instance with empty strings for user/pass
    empty_auth_settings = Settings(WEB_UI_USERNAME="", WEB_UI_PASSWORD="", DATABASE_URL="sqlite:///./test_temp_empty.db")
    with patch('app.core.security.settings', empty_auth_settings):
        credentials = HTTPBasicCredentials(username="testuser", password="testpassword")
        with pytest.raises(HTTPException) as excinfo:
            get_current_username(credentials)
        assert excinfo.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert excinfo.value.detail == "Server authentication configuration error."
