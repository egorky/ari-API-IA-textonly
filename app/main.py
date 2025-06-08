import asyncio
import logging
import sys # Ensure sys is imported for logging config
from pathlib import Path

from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session # Added for get_db type hint in ui_home_page

from app.core.config import settings
from app.core.database import engine, get_db
from app import models as app_models
from app.api import ari_handler, prompts_router, tools_router, testing_router # Added testing_router
from app.core.security import get_current_username
from app.services.redis_service import get_redis_client
from app.services.ai_service import PY_MINI_RACER_AVAILABLE, JS_CONTEXT # For JS Processor status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)] # Explicitly log to stdout
)
logger = logging.getLogger(__name__)

# Create database tables on startup
try:
    app_models.Base.metadata.create_all(bind=engine)
    logger.info("Database tables created or verified successfully.")
except Exception as e:
    logger.error(f"Error creating database tables: {e}", exc_info=True)
    # Depending on the severity, you might want to exit or handle this.
    # For now, just log it.

app = FastAPI(
    title="Asterisk AI Integration Service",
    version="0.1.0",
    description="Service to integrate Asterisk with AI models and provide a web UI for management."
)

# --- Web UI Setup ---
APP_BASE_DIR = Path(__file__).resolve().parent
static_dir_for_app = APP_BASE_DIR / "static"

if not static_dir_for_app.is_dir():
    logger.info(f"Main static directory not found at {static_dir_for_app}, creating it.")
    static_dir_for_app.mkdir(parents=True, exist_ok=True)
else:
    logger.info(f"Main static directory confirmed at: {static_dir_for_app}")

app.mount("/static", StaticFiles(directory=str(static_dir_for_app)), name="static")

# Include the specific routers for UI sections
app.include_router(prompts_router.router)
app.include_router(tools_router.router)
app.include_router(testing_router.router) # Include the testing router

templates_main = Jinja2Templates(directory=str(APP_BASE_DIR / "templates"))

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: Initializing ARI listener...")
    ari_handler.start_ari_listener() # Corrected function name from previous subtask's prompt
    logger.info("ARI listener task initiated.")
    get_redis_client()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutdown: Cleaning up resources.")
    if ari_handler.ari_client_task and not ari_handler.ari_client_task.done():
        logger.info("Cancelling ARI client task.")
        ari_handler.ari_client_task.cancel()
        try:
            await ari_handler.ari_client_task
        except asyncio.CancelledError:
            logger.info("ARI client task cancelled successfully.")
        except Exception as e:
            logger.error(f"Error during ARI task cancellation: {e}")

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Asterisk AI Integration Service. Visit /docs for API documentation or /ui for the web interface."}

@app.get("/ui", name="ui_home", response_class=HTMLResponse, tags=["Web UI Home"], include_in_schema=False)
async def ui_home_page(request: Request, username: str = Depends(get_current_username), db: Session = Depends(get_db)):
    ari_instance = ari_handler.get_ari_client() # Corrected function name
    ari_status = "Connected" if ari_instance and hasattr(ari_instance, 'closed') and not ari_instance.closed else "Disconnected"

    redis_c = get_redis_client()
    redis_status = "Not Initialized"
    if redis_c:
        try:
            ping_success = await asyncio.to_thread(redis_c.ping) # Ensure ping is run in a thread for async
            if ping_success:
                 redis_status = "Connected"
            else:
                 redis_status = "Ping Failed" # Or "Disconnected"
        except Exception as e:
            logger.warning(f"Redis ping failed for UI status check: {e}")
            redis_status = "Connection Failed" # Or "Disconnected"

    py_mini_racer_status = "No Disponible"
    if PY_MINI_RACER_AVAILABLE and JS_CONTEXT is not None:
        py_mini_racer_status = "Disponible"
    elif PY_MINI_RACER_AVAILABLE and JS_CONTEXT is None: # Indicates an issue during MiniRacer init
        py_mini_racer_status = "Error de Inicialización"
    # If PY_MINI_RACER_AVAILABLE is False, it remains "No Disponible"

    return templates_main.TemplateResponse("index.html", {
        "request": request,
        "username": username,
        "ari_status": ari_status,
        "default_ai_model": settings.DEFAULT_AI_MODEL,
        "redis_status": redis_status,
        "py_mini_racer_status": py_mini_racer_status,
        "ASTERISK_APP_NAME": settings.ASTERISK_APP_NAME,
        "OPENAI_MODEL_NAME": settings.OPENAI_MODEL_NAME,
        "GEMINI_MODEL_NAME": settings.GEMINI_MODEL_NAME,
        "DEBUG_MODE": settings.DEBUG_MODE,
    })

@app.get("/ui/test-prompt", name="ui_test_prompt", response_class=HTMLResponse, tags=["Web UI Testing"], include_in_schema=False)
async def ui_prompt_tester_page(request: Request, username: str = Depends(get_current_username)):
    """Serves the prompt testing page."""
    return templates_main.TemplateResponse("testing/test_prompt.html", {"request": request, "username": username})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
