import asyncio
# import sys # No longer needed for sys.path manipulation
# import os # No longer needed
from app.vendor import ari_py as ari # Use the vendored library
import logging
from app.core.config import settings
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
    logger.info(f"Channel {channel_name} ({channel_id}) entered Stasis app {settings.ASTERISK_APP_NAME}")

    args = ev.get('args', [])
    dialplan_vars = {}

    logger.info(f"StasisStart event args for channel {channel_id}: {args}")
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            dialplan_vars[key] = value.strip() # Ensure no leading/trailing whitespace
        else:
            logger.info(f"Received non key-value arg: '{arg}' for channel {channel_id}")

    logger.info(f"Parsed Dialplan variables for channel {channel_id}: {dialplan_vars}")

    user_input = dialplan_vars.get('USER_INPUT', dialplan_vars.get('user_input', 'N/A'))
    ai_model_choice = dialplan_vars.get('AI_MODEL', dialplan_vars.get('ai_model', settings.DEFAULT_AI_MODEL))
    unique_id = dialplan_vars.get('UNIQUEID', dialplan_vars.get('uniqueid', channel_id))

    logger.info(f"Channel {channel_id}: Effective User Input: '{user_input}', AI Model: '{ai_model_choice}', UniqueID for session: '{unique_id}'")

    try:
        await channel.answer()
        logger.info(f"Channel {channel_id} answered.")

        # Call the AI service (currently synchronous)
        # If ai_service.get_ai_response becomes truly async (e.g. using chain.arun), then add 'await'
        ai_response_text = ai_service.get_ai_response(
            text_input=user_input,
            session_id=unique_id,
            model_preference=ai_model_choice,
            initial_prompt_str=None # Later this will come from DB or other config
        )
        logger.info(f"AI response for {channel_id}: {ai_response_text}")

        await channel.setChannelVar(variable='AI_RESPONSE', value=ai_response_text)
        logger.info(f"Set AI_RESPONSE='{ai_response_text}' on channel {channel_id}")

    except ari.AriException as e: # Make sure 'ari' is correctly imported (from app.vendor.ari_py)
        logger.error(f"ARI Error processing channel {channel_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error processing channel {channel_id}: {e}", exc_info=True)
    finally:
        logger.info(f"Finished Stasis processing for channel {channel_id}. Channel will exit Stasis and continue in dialplan.")


async def _run_ari_client_with_retry():
    global ari_client_instance
    while True:
        try:
            logger.info(f"Attempting ARI connection: {settings.ASTERISK_ARI_URL}, App: {settings.ASTERISK_APP_NAME}")
            client = ari.connect( # Removed await
                settings.ASTERISK_ARI_URL,
                settings.ASTERISK_APP_NAME,
                settings.ASTERISK_ARI_USERNAME,
                settings.ASTERISK_ARI_PASSWORD
            )
            ari_client_instance = client
            logger.info("ARI client connected successfully.")

            client.on_channel_event('StasisStart', on_stasis_start)
            logger.info(f"Listening for StasisStart on app {settings.ASTERISK_APP_NAME}")

            await client.run() # This blocks until the client disconnects or is closed.

        except ari.AriException as e:
            logger.error(f"ARI Connection Error: {e}")
        except ConnectionRefusedError as e:
            logger.error(f"ARI Connection Refused: {e}. Check Asterisk & ARI configuration.")
        except Exception as e:
            logger.error(f"Unexpected ARI client error: {e}", exc_info=True)

        if ari_client_instance and ari_client_instance.closed:
            logger.info("ARI client disconnected.")
        ari_client_instance = None # Reset client instance

        logger.info("Attempting to reconnect ARI client in 10 seconds...")
        await asyncio.sleep(10)

def start_ari_listener():
    global ari_client_task
    if ari_client_task is None or ari_client_task.done():
        logger.info("Creating new ARI client task.")
        ari_client_task = asyncio.create_task(_run_ari_client_with_retry())
    else:
        logger.info("ARI client task already running.")

def get_ari_client():
    return ari_client_instance
