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
    tags=["Prompts Web UI"],
    dependencies=[Depends(get_current_username)]
)

template_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# HTML Routes for Prompts
@router.get("/", response_class=HTMLResponse, name="list_prompts_ui", summary="List all prompts - HTML")
async def list_prompts_page(request: Request, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    prompts = crud.get_prompts(db)
    return templates.TemplateResponse("prompts/list.html", {"request": request, "prompts": prompts, "username": username})

@router.get("/create", response_class=HTMLResponse, name="create_prompt_form", summary="Display form to create a new prompt - HTML")
async def create_prompt_form_page(request: Request, username: str = Depends(get_current_username), error: Optional[str] = None):
    return templates.TemplateResponse("prompts/create_or_edit.html", {"request": request, "prompt": None, "username": username, "error": error})

@router.get("/{prompt_id}/edit", response_class=HTMLResponse, name="edit_prompt_form", summary="Display form to edit an existing prompt - HTML")
async def edit_prompt_form_page(request: Request, prompt_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username), error: Optional[str] = None):
    prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return templates.TemplateResponse("prompts/create_or_edit.html", {"request": request, "prompt": prompt, "username": username, "error": error})

# API Routes (JSON based)
@router.post("/api", response_model=schemas.PromptInDB, status_code=status.HTTP_201_CREATED, name="create_prompt_api", summary="Create a new prompt", description="Creates a new prompt in the database.")
def create_prompt_api_route(prompt_in: schemas.PromptCreate, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    logger.info(f"User '{username}' creating prompt: {prompt_in.name}")
    db_prompt = crud.get_prompt_by_name(db, name=prompt_in.name)
    if db_prompt:
        logger.warning(f"Attempt to create prompt with existing name: {prompt_in.name}")
        raise HTTPException(status_code=400, detail=f"Prompt name '{prompt_in.name}' already registered")
    created_prompt = crud.create_prompt(db=db, prompt=prompt_in)
    logger.info(f"Prompt '{created_prompt.name}' created successfully with ID {created_prompt.id}.")
    return created_prompt

@router.get("/api", response_model=List[schemas.PromptInDB], name="get_prompts_api_list", summary="Read all prompts", description="Retrieves a list of all prompts.", include_in_schema=True)
def read_prompts_api_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    prompts = crud.get_prompts(db, skip=skip, limit=limit)
    return prompts

@router.get("/api/{prompt_id}", response_model=schemas.PromptInDB, name="get_prompt_api_detail", summary="Read a specific prompt by ID", description="Retrieves a single prompt by its ID.", include_in_schema=True)
def read_prompt_api_route(prompt_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return db_prompt

@router.put("/api/{prompt_id}", response_model=schemas.PromptInDB, name="update_prompt_api", summary="Update an existing prompt", description="Updates an existing prompt by its ID.")
def update_prompt_api_route(prompt_id: int, prompt_in: schemas.PromptUpdate, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
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

@router.delete("/api/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_prompt_api", summary="Delete a prompt", description="Deletes a prompt by its ID.")
def delete_prompt_api_route(prompt_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    logger.info(f"User '{username}' deleting prompt ID: {prompt_id}")
    db_prompt = crud.get_prompt(db, prompt_id=prompt_id)
    if db_prompt is None:
        raise HTTPException(status_code=404, detail="Prompt not found")
    crud.delete_prompt(db, prompt_id=prompt_id)
    logger.info(f"Prompt ID {prompt_id} ({db_prompt.name}) deleted successfully.")
    # No return needed for 204
