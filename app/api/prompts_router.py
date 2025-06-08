import logging
import json
from fastapi import APIRouter, Depends, HTTPException, Request, Form, status, Body
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pathlib import Path

from app import crud, schemas, models
from app.core.database import get_db, engine
from app.core.security import get_current_username

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ui/prompts",
    tags=["Prompts Web UI & API"], # Combined tag
    dependencies=[Depends(get_current_username)]
)

template_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# --- HTML Routes for Prompts ---
@router.get("/", response_class=HTMLResponse, name="list_prompts_ui", summary="List all prompts (HTML)")
async def list_prompts_page(request: Request, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    """Serves the HTML page that lists all configured prompts."""
    prompts = crud.get_prompts(db)
    return templates.TemplateResponse("prompts/list.html", {"request": request, "prompts": prompts, "username": username})

@router.get("/create", response_class=HTMLResponse, name="create_prompt_form", summary="Display form to create a new prompt (HTML)")
async def create_prompt_form_page(request: Request, username: str = Depends(get_current_username), error: Optional[str] = None):
    """Serves the HTML form for creating a new prompt.

    Args:
        request: The FastAPI request object.
        username: The currently authenticated username.
        error: An optional error message to display on the form.
    """
    return templates.TemplateResponse("prompts/create_or_edit.html", {"request": request, "prompt": None, "username": username, "error": error, "page_title": "Create New Prompt"})

@router.get("/{prompt_id}/edit", response_class=HTMLResponse, name="edit_prompt_form", summary="Display form to edit an existing prompt (HTML)")
async def edit_prompt_form_page(request: Request, prompt_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username), error: Optional[str] = None):
    """Serves the HTML form for editing an existing prompt, pre-filled with its current data.

    Args:
        request: The FastAPI request object.
        prompt_id: The ID of the prompt to edit.
        db: Database session dependency.
        username: The currently authenticated username.
        error: An optional error message to display on the form.
    """
    prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return templates.TemplateResponse("prompts/create_or_edit.html", {"request": request, "prompt": prompt, "username": username, "error": error, "page_title": f"Edit Prompt: {prompt.name}"})

# --- API Routes (JSON based) ---
@router.post("/api", response_model=schemas.PromptInDB, status_code=status.HTTP_201_CREATED, name="create_prompt_api", summary="Create a new prompt (API)")
def create_prompt_api_route(
    prompt_in: schemas.PromptCreate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username)
):
    """Creates a new prompt in the database via API.

    Args:
        prompt_in: The prompt data (name, content, metadata) from the request body.
        db: Database session dependency.
        username: The currently authenticated username.

    Raises:
        HTTPException 400: If a prompt with the same name already exists.

    Returns:
        The created prompt data including its ID.
    """
    logger.info(f"User '{username}' creating prompt: {prompt_in.name}")
    db_prompt = crud.get_prompt_by_name(db, name=prompt_in.name)
    if db_prompt:
        logger.warning(f"Attempt to create prompt with existing name: {prompt_in.name}")
        raise HTTPException(status_code=400, detail=f"Prompt name '{prompt_in.name}' already registered")
    created_prompt = crud.create_prompt(db=db, prompt=prompt_in)
    logger.info(f"Prompt '{created_prompt.name}' created successfully with ID {created_prompt.id}.")
    return created_prompt

@router.get("/api", response_model=List[schemas.PromptInDB], name="get_prompts_api_list", summary="Read all prompts (API)")
def read_prompts_api_route(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username)
):
    """Retrieves a list of all prompts from the database, with optional pagination.

    Args:
        skip: Number of prompts to skip.
        limit: Maximum number of prompts to return.
        db: Database session dependency.
        username: The currently authenticated username.

    Returns:
        A list of prompt objects.
    """
    prompts = crud.get_prompts(db, skip=skip, limit=limit)
    return prompts

@router.get("/api/{prompt_id}", response_model=schemas.PromptInDB, name="get_prompt_api_detail", summary="Read a specific prompt by ID (API)")
def read_prompt_api_route(
    prompt_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username)
):
    """Retrieves a single prompt by its unique ID.

    Args:
        prompt_id: The ID of the prompt to retrieve.
        db: Database session dependency.
        username: The currently authenticated username.

    Raises:
        HTTPException 404: If the prompt is not found.

    Returns:
        The prompt object.
    """
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return db_prompt

@router.put("/api/{prompt_id}", response_model=schemas.PromptInDB, name="update_prompt_api", summary="Update an existing prompt (API)")
def update_prompt_api_route(
    prompt_id: int,
    prompt_in: schemas.PromptUpdate,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username)
):
    """Updates an existing prompt in the database by its ID. Allows partial updates.

    Args:
        prompt_id: The ID of the prompt to update.
        prompt_in: The prompt data to update from the request body.
        db: Database session dependency.
        username: The currently authenticated username.

    Raises:
        HTTPException 404: If the prompt to update is not found.
        HTTPException 400: If the new prompt name conflicts with an existing one.

    Returns:
        The updated prompt object.
    """
    logger.info(f"User '{username}' updating prompt ID: {prompt_id} with data: {prompt_in.model_dump(exclude_unset=True)}")
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if prompt_in.name and prompt_in.name != db_prompt.name:
        existing_prompt_with_new_name = crud.get_prompt_by_name(db, name=prompt_in.name)
        if existing_prompt_with_new_name and existing_prompt_with_new_name.id != prompt_id:
            raise HTTPException(status_code=400, detail=f"Prompt name '{prompt_in.name}' already exists.")

    updated_prompt = crud.update_prompt(db, prompt_id=prompt_id, prompt_update=prompt_in)
    logger.info(f"Prompt ID {prompt_id} updated successfully.")
    return updated_prompt

@router.delete("/api/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_prompt_api", summary="Delete a prompt (API)")
def delete_prompt_api_route(
    prompt_id: int,
    db: Session = Depends(get_db),
    username: str = Depends(get_current_username)
):
    """Deletes a prompt from the database by its ID.

    Args:
        prompt_id: The ID of the prompt to delete.
        db: Database session dependency.
        username: The currently authenticated username.

    Raises:
        HTTPException 404: If the prompt to delete is not found.
    """
    logger.info(f"User '{username}' deleting prompt ID: {prompt_id}")
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    crud.delete_prompt(db, prompt_id=prompt_id)
    logger.info(f"Prompt ID {prompt_id} ({db_prompt.name}) deleted successfully.")
    # No content is returned for a 204 response
