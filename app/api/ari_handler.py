import asyncio
import logging
from app.core.config import settings
from app.core.database import SessionLocal
from app.vendor import ari_py as ari # Using the established vendored path

from app.services import ai_service

logger = logging.getLogger(__name__)

ari_client_task = None
ari_client_instance = None

async def on_stasis_start(ari_channel: ari.Channel, event: Dict[str, Any]):
    """Handles the StasisStart event from Asterisk ARI.

    This coroutine is invoked when a new channel enters the Stasis application.
    It performs the following steps:
    1. Extracts channel information (ID, name) from `ari_channel`.
    2. Parses arguments passed from the Asterisk dialplan via `event['args']`
       (e.g., `USER_INPUT`, `UNIQUEID`, `AI_MODEL`, `AI_PROMPT_NAME`).
       `UNIQUEID` defaults to the channel ID if not explicitly provided.
    3. Answers the channel using `ari_channel.answer()`.
    4. Calls `ai_service.get_ai_response` with the extracted user input, session ID
       (UNIQUEID), a new database session, AI model preference, and prompt name.
    5. Sets the AI's response as a channel variable (`AI_RESPONSE`) on the Asterisk
       channel using `ari_channel.setChannelVar()`.
    6. Handles potential errors during the process (ARI errors, AI service errors)
       by setting appropriate error variables on the channel (e.g., `ARI_ERROR`,
       `SYSTEM_ERROR`) and ensuring the channel continues in the dialplan.
    7. Closes the database session.

    Note on parameter names and structure:
        Standard `ari-py` event handlers receive `(channel, event_data)`.
        This function's parameters `ari_channel` and `event` align with this.
        The original code had `channel_obj` and `ev`, with a line
        `channel = channel_obj.get('channel')`. This docstring assumes
        `ari_channel` is the actual channel instance and `event` is the event data dictionary.

    Args:
        ari_channel: The ARI channel object that entered Stasis. This object is
                     provided by the `ari-py` library.
        event: A dictionary containing the event data for the StasisStart event.
               It includes `event['args']` for dialplan arguments and other
               event-specific details.
    """
    # The line `channel = channel_obj.get('channel')` from the original code
    # is assumed to be replaced by directly using `ari_channel` as the channel object.
    # All operations like `channel.get('id')` become `ari_channel.get('id')`.
    # The variable `channel` in the original code will be treated as `ari_channel` here.

    channel_id = ari_channel.get('id')
    channel_name = ari_channel.get('name')
    logger.info(f"Channel {channel_name} ({channel_id}) entered Stasis app '{settings.ASTERISK_APP_NAME}'")

    args = event.get('args', []) # Using `event` as the source of dialplan args
    dialplan_vars = {}

    logger.info(f"StasisStart event args for channel {channel_id}: {args}")
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            dialplan_vars[key.upper()] = value.strip()
        else:
            logger.info(f"Received non key-value arg: '{arg}' for channel {channel_id}")

    logger.info(f"Parsed Dialplan variables for channel {channel_id}: {dialplan_vars}")

    user_input = dialplan_vars.get('USER_INPUT', 'No input provided')
    ai_model_choice = dialplan_vars.get('AI_MODEL', settings.DEFAULT_AI_MODEL)
    unique_id = dialplan_vars.get('UNIQUEID', channel_id) # Fallback to channel_id for UNIQUEID
    prompt_name_from_dialplan = dialplan_vars.get('AI_PROMPT_NAME', None)

    logger.info(f"Channel {channel_id}: User Input: '{user_input}', AI Model: '{ai_model_choice}', UniqueID: '{unique_id}', Prompt: '{prompt_name_from_dialplan}'")

    db = SessionLocal()
    try:
        await ari_channel.answer() # Use ari_channel
        logger.info(f"Channel {channel_id} answered.")

        ai_response_text = await ai_service.get_ai_response(
            text_input=user_input,
            session_id=unique_id,
            db=db,
            model_preference=ai_model_choice,
            prompt_name=prompt_name_from_dialplan
        )

        logger.info(f"AI response for {channel_id}: {ai_response_text}")

        await ari_channel.setChannelVar(variable='AI_RESPONSE', value=ai_response_text) # Use ari_channel
        logger.info(f"Set channel variable AI_RESPONSE='{ai_response_text}' on channel {channel_id}")

    except ari.AriException as e:
        logger.error(f"ARI Error on channel {channel_id}: {e}")
        try:
            await ari_channel.setChannelVar(variable='AI_RESPONSE', value=f"ARI_ERROR: {str(e)}") # Use ari_channel
        except Exception as set_var_e:
            logger.error(f"Failed to set error variable on channel {channel_id}: {set_var_e}")
    except Exception as e:
        logger.error(f"Unexpected error processing channel {channel_id}: {e}", exc_info=True)
        try:
            await ari_channel.setChannelVar(variable='AI_RESPONSE', value=f"SYSTEM_ERROR: {str(e)}") # Use ari_channel
        except Exception as set_var_e:
            logger.error(f"Failed to set system error variable on channel {channel_id}: {set_var_e}")
    finally:
        db.close()
        logger.info(f"Finished Stasis processing for channel {channel_id}. Channel will exit Stasis and continue in dialplan.")


async def _run_ari_client_with_retry():
    """Runs the ARI client with an automatic retry mechanism.

    This function enters an infinite loop to:
    1. Attempt to connect to the Asterisk ARI using `ari.connect` with
       configuration from `settings`.
    2. If successful, it registers `on_stasis_start` as the handler for
       'StasisStart' events on the configured `settings.ASTERISK_APP_NAME`.
    3. It then runs the client's main event loop (`client.run()`) in a separate
       thread using `asyncio.get_event_loop().run_in_executor()` because
       the vendored `ari-py` client's `run()` method is blocking.
    4. If any `ari.AriException`, `ConnectionRefusedError`, or other unexpected
       exception occurs during connection or while the client is running,
       it logs the error.
    5. After a disconnection or failure, it waits for 10 seconds before
       attempting to reconnect, thus providing resilience.
    """
    global ari_client_instance
    while True:
        try:
            logger.info(f"Attempting ARI connection to {settings.ASTERISK_ARI_URL} for app '{settings.ASTERISK_APP_NAME}'")
            # The vendored ari.connect is synchronous.
            client = ari.connect(
                settings.ASTERISK_ARI_URL,
                settings.ASTERISK_APP_NAME,
                settings.ASTERISK_ARI_USERNAME,
                settings.ASTERISK_ARI_PASSWORD
            )
            ari_client_instance = client
            logger.info("ARI client connected successfully.")

            client.on_channel_event('StasisStart', on_stasis_start) # Pass the event handler
            logger.info(f"Listening for StasisStart events on app '{settings.ASTERISK_APP_NAME}'")

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.run)

        except ari.AriException as e:
            logger.error(f"ARI Library Error: {e}")
        except ConnectionRefusedError as e:
            logger.error(f"ARI Connection Refused: {e}. Ensure Asterisk is running and ARI is configured correctly.")
        except Exception as e:
            logger.error(f"Unexpected error in ARI client run loop: {e}", exc_info=True)

        if ari_client_instance and hasattr(ari_client_instance, 'closed') and ari_client_instance.closed:
            logger.info("ARI client was closed.")
        elif ari_client_instance:
             logger.info("ARI client connection lost or not gracefully closed.")
        ari_client_instance = None # Reset global instance

        logger.info("ARI client disconnected. Attempting to reconnect in 10 seconds...")
        await asyncio.sleep(10)

def start_ari_listener():
    """Starts the ARI client listener task if not already running.

    This function checks if the global `ari_client_task` is None or has completed.
    If so, it creates a new asyncio task for `_run_ari_client_with_retry()`
    to ensure the ARI event listener is active. It also handles potential
    exceptions from a previously completed task.
    """
    global ari_client_task
    if ari_client_task is None or ari_client_task.done():
        if ari_client_task and ari_client_task.done():
            try:
                ari_client_task.result() # Retrieve result to raise exceptions if any
            except asyncio.CancelledError:
                logger.info("ARI task was cancelled.")
            except Exception as e:
                logger.error(f"ARI client task ended with exception: {e}", exc_info=True)
        logger.info("Creating new ARI client listener task.")
        ari_client_task = asyncio.create_task(_run_ari_client_with_retry())
    else:
        logger.info("ARI client listener task is already running or pending.")

def get_ari_client() -> Optional[ari.Client]:
    """Returns the current global ARI client instance.

    Returns:
        The `ari.Client` instance if connected, otherwise None.
    """
    return ari_client_instance
