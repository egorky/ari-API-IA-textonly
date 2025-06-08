import logging
import uuid
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app import crud, schemas
from app.core.database import get_db
from app.core.security import get_current_username
from app.services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/testing",
    tags=["Testing Utilities"],
    dependencies=[Depends(get_current_username)] # Secure all routes in this router
)

# --- Schemas for Testing Endpoints ---
class PromptTestExecutionPayload(BaseModel):
    prompt_content: str = Field(..., description="The full content of the prompt to test.")
    user_input: str = Field(..., description="The user input for the AI.")
    ai_model: str = Field(..., description="The AI model to use (e.g., 'openai', 'gemini').")
    session_id: Optional[str] = Field(None, description="Optional session ID for conversation history. If None, a new one will be generated.")

class PromptTestExecutionResponse(BaseModel):
    ai_response: str
    session_id_used: str

class SimplePromptInfo(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


# --- Testing API Endpoints ---

@router.get("/list-prompts", response_model=List[SimplePromptInfo], summary="List all available prompts (ID and Name)")
async def list_all_prompts(db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    """
    Retrieves a simplified list of all prompts (ID and name only)
    to populate selectors in the UI.
    """
    try:
        db_prompts = crud.get_prompts(db=db, limit=1000) # Adjust limit as needed
        # Convert to SimplePromptInfo to send only necessary data
        return [SimplePromptInfo.model_validate(p) for p in db_prompts]
    except Exception as e:
        logger.error(f"Error fetching list of prompts for user {username}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch prompt list.")


@router.get("/get-prompt-content/{prompt_id}", response_model=Dict[str, Optional[str]], summary="Get content of a specific prompt")
async def get_prompt_content_by_id(prompt_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    """
    Retrieves the full content of a specific prompt by its ID.
    """
    logger.info(f"User '{username}' fetching content for prompt ID: {prompt_id}")
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not db_prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return {"content": db_prompt.content}


@router.post("/execute-test-prompt", response_model=PromptTestExecutionResponse, summary="Execute a prompt test")
async def execute_prompt_test(
    payload: PromptTestExecutionPayload,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username)
):
    """
    Executes a test of a given prompt (custom or existing) with user input and a chosen AI model.
    """
    logger.info(f"User '{username}' executing prompt test. Model: {payload.ai_model}, SessionID: {payload.session_id or 'New'}")

    session_id_to_use = payload.session_id
    if not session_id_to_use:
        session_id_to_use = f"test_session_{uuid.uuid4()}"
        logger.info(f"No session_id provided, generated new one: {session_id_to_use}")

    try:
        ai_response_text = await ai_service.get_ai_response(
            text_input=payload.user_input,
            session_id=session_id_to_use,
            db=db,
            model_preference=payload.ai_model,
            prompt_content_override=payload.prompt_content,
            prompt_name=None  # Explicitly None because we are using override
        )
        logger.info(f"Prompt test for user '{username}' completed. Response length: {len(ai_response_text)}")
        return PromptTestExecutionResponse(ai_response=ai_response_text, session_id_used=session_id_to_use)
    except Exception as e:
        logger.error(f"Error during prompt test execution for user '{username}': {e}", exc_info=True)
        # Consider if more specific error handling/status codes are needed based on ai_service exceptions
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

# Placeholder for future testing utilities if needed
# e.g., testing specific tools, etc.
