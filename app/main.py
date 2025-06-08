import asyncio
import logging
import sys # Import sys for logging to stdout
from fastapi import FastAPI
from app.core.config import settings
from app.api import ari_handler
# from app.api import web_ui # Will be enabled later

logging.basicConfig(stream=sys.stdout, level=logging.INFO) # Configure logging to stdout
logger = logging.getLogger(__name__)

app = FastAPI(title="Asterisk AI Integration")

@app.on_event("startup")
async def startup_event():
    logger.info("Application startup: Initializing ARI connection...")
    ari_handler.start_ari_listener()
    logger.info("ARI connection listener started.")

@app.get("/")
async def root():
    return {"message": "Asterisk AI Integration running"}

if __name__ == "__main__":
    import uvicorn
    # Add import sys for logging to stdout
    import sys
    uvicorn.run(app, host="0.0.0.0", port=8000)
