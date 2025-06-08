import secrets
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings

logger = logging.getLogger(__name__)
security = HTTPBasic()

def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    # Log the username being attempted, but NOT the password
    logger.debug(f"Attempting login for username: {credentials.username}")

    # Ensure settings are loaded and have the attributes
    if not hasattr(settings, 'WEB_UI_USERNAME') or not settings.WEB_UI_USERNAME or \
       not hasattr(settings, 'WEB_UI_PASSWORD') or not settings.WEB_UI_PASSWORD:
        logger.error("Web UI username or password not configured in settings.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server authentication configuration error.",
            headers={"WWW-Authenticate": "Basic"}, # Keep to prompt client
        )

    correct_username = secrets.compare_digest(credentials.username, settings.WEB_UI_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, settings.WEB_UI_PASSWORD)

    if not (correct_username and correct_password):
        logger.warning(f"Failed login attempt for username: {credentials.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Basic"},
        )
    logger.info(f"User '{credentials.username}' authenticated successfully.")
    return credentials.username
