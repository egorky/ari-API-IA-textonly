import asyncio
import logging
from app.core.config import settings
from app.core.database import SessionLocal
from app.vendor import ari_py as ari # Using the established vendored path

from app.services import ai_service

logger = logging.getLogger(__name__)

ari_client_task = None
ari_client_instance = None

async def on_stasis_start(channel_obj, ev):
    """Handle StasisStart event."""
    channel = channel_obj.get('channel')
    if not channel:
        logger.error("No channel object in StasisStart event.")
        return

    channel_id = channel.get('id')
    channel_name = channel.get('name')
    logger.info(f"Channel {channel_name} ({channel_id}) entered Stasis app '{settings.ASTERISK_APP_NAME}'")

    args = ev.get('args', [])
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
    unique_id = dialplan_vars.get('UNIQUEID', channel_id)
    prompt_name_from_dialplan = dialplan_vars.get('AI_PROMPT_NAME', None)

    logger.info(f"Channel {channel_id}: User Input: '{user_input}', AI Model: '{ai_model_choice}', UniqueID: '{unique_id}', Prompt: '{prompt_name_from_dialplan}'")

    db = SessionLocal()
    try:
        await channel.answer()
        logger.info(f"Channel {channel_id} answered.")

        ai_response_text = await ai_service.get_ai_response(
            text_input=user_input,
            session_id=unique_id,
            db=db,
            model_preference=ai_model_choice,
            prompt_name=prompt_name_from_dialplan
        )

        logger.info(f"AI response for {channel_id}: {ai_response_text}")

        await channel.setChannelVar(variable='AI_RESPONSE', value=ai_response_text)
        logger.info(f"Set channel variable AI_RESPONSE='{ai_response_text}' on channel {channel_id}")

    except ari.AriException as e:
        logger.error(f"ARI Error on channel {channel_id}: {e}")
        try:
            await channel.setChannelVar(variable='AI_RESPONSE', value=f"ARI_ERROR: {str(e)}")
        except Exception as set_var_e:
            logger.error(f"Failed to set error variable on channel {channel_id}: {set_var_e}")
    except Exception as e:
        logger.error(f"Unexpected error processing channel {channel_id}: {e}", exc_info=True)
        try:
            await channel.setChannelVar(variable='AI_RESPONSE', value=f"SYSTEM_ERROR: {str(e)}")
        except Exception as set_var_e:
            logger.error(f"Failed to set system error variable on channel {channel_id}: {set_var_e}")
    finally:
        db.close()
        logger.info(f"Finished Stasis processing for channel {channel_id}. Channel will exit Stasis and continue in dialplan.")


async def _run_ari_client_with_retry():
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

            client.on_channel_event('StasisStart', on_stasis_start)
            logger.info(f"Listening for StasisStart events on app '{settings.ASTERISK_APP_NAME}'")

            # The client.run() method of the original ari-py was synchronous and blocking.
            # To integrate with asyncio, it needs to be run in an executor.
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.run) # Run the blocking client.run() in a thread pool

        except ari.AriException as e: # Vendored ari_py.client.AriException
            logger.error(f"ARI Library Error: {e}")
        except ConnectionRefusedError as e: # Standard Python error
            logger.error(f"ARI Connection Refused: {e}. Ensure Asterisk is running and ARI is configured correctly.")
        except Exception as e: # Catch-all for other unexpected errors
            logger.error(f"Unexpected error in ARI client run loop: {e}", exc_info=True)

        if ari_client_instance and hasattr(ari_client_instance, 'closed') and ari_client_instance.closed: # Check 'closed' if attribute exists
            logger.info("ARI client was closed.")
        elif ari_client_instance:
             logger.info("ARI client connection lost or not gracefully closed.")
        ari_client_instance = None

        logger.info("ARI client disconnected. Attempting to reconnect in 10 seconds...")
        await asyncio.sleep(10)

def start_ari_listener(): # Renamed from start_ari_listener_task for consistency with main.py
    global ari_client_task
    if ari_client_task is None or ari_client_task.done():
        if ari_client_task and ari_client_task.done():
            try:
                ari_client_task.result()
            except asyncio.CancelledError:
                logger.info("ARI task was cancelled.")
            except Exception as e:
                logger.error(f"ARI client task ended with exception: {e}", exc_info=True)
        logger.info("Creating new ARI client listener task.")
        ari_client_task = asyncio.create_task(_run_ari_client_with_retry())
    else:
        logger.info("ARI client listener task is already running or pending.")

def get_ari_client(): # Renamed from get_ari_client_instance for consistency
    return ari_client_instance
