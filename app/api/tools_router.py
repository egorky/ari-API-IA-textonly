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
    prefix="/ui/tools",
    tags=["Tools Web UI"],
    dependencies=[Depends(get_current_username)]
)

template_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(template_dir))

# HTML Routes for Tools
@router.get("/", response_class=HTMLResponse, name="list_tools_ui", summary="List all tools - HTML")
async def list_tools_page(request: Request, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    tools = crud.get_tools(db)
    return templates.TemplateResponse("tools/list.html", {"request": request, "tools": tools, "username": username})

@router.get("/create", response_class=HTMLResponse, name="create_tool_form", summary="Display form to create a new tool - HTML")
async def create_tool_form_page(request: Request, username: str = Depends(get_current_username), error: Optional[str] = None):
    return templates.TemplateResponse("tools/create_or_edit.html", {"request": request, "tool": None, "username": username, "error": error})

@router.get("/{tool_id}/edit", response_class=HTMLResponse, name="edit_tool_form", summary="Display form to edit an existing tool - HTML")
async def edit_tool_form_page(request: Request, tool_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username), error: Optional[str] = None):
    tool = crud.get_tool(db, tool_id=tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return templates.TemplateResponse("tools/create_or_edit.html", {"request": request, "tool": tool, "username": username, "error": error})

# API Routes (JSON based) for Tools
@router.post("/api", response_model=schemas.ToolInDB, status_code=status.HTTP_201_CREATED, name="create_tool_api", summary="Create a new tool", description="Creates a new tool definition in the database.")
def create_tool_api_route(tool_in: schemas.ToolCreate, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    logger.info(f"User '{username}' creating tool: {tool_in.name}")
    db_tool = crud.get_tool_by_name(db, name=tool_in.name)
    if db_tool:
        raise HTTPException(status_code=400, detail=f"Tool name '{tool_in.name}' already registered")
    created_tool = crud.create_tool(db=db, tool=tool_in)
    logger.info(f"Tool '{created_tool.name}' created successfully with ID {created_tool.id}.")
    return created_tool

@router.get("/api", response_model=List[schemas.ToolInDB], name="get_tools_api_list", summary="Read all tools", description="Retrieves a list of all tools.", include_in_schema=True)
def read_tools_api_route(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    tools = crud.get_tools(db, skip=skip, limit=limit)
    return tools

@router.get("/api/{tool_id}", response_model=schemas.ToolInDB, name="get_tool_api_detail", summary="Read a specific tool by ID", description="Retrieves a single tool by its ID.", include_in_schema=True)
def read_tool_api_route(tool_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    db_tool = crud.get_tool(db, tool_id=tool_id)
    if db_tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    return db_tool

@router.put("/api/{tool_id}", response_model=schemas.ToolInDB, name="update_tool_api", summary="Update an existing tool", description="Updates an existing tool by its ID.")
def update_tool_api_route(tool_id: int, tool_in: schemas.ToolUpdate, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    logger.info(f"User '{username}' updating tool ID: {tool_id} with data: {tool_in.model_dump(exclude_unset=True)}")
    db_tool = crud.get_tool(db, tool_id=tool_id)
    if db_tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    if tool_in.name and tool_in.name != db_tool.name:
        existing_tool_with_new_name = crud.get_tool_by_name(db, name=tool_in.name)
        if existing_tool_with_new_name and existing_tool_with_new_name.id != tool_id:
            raise HTTPException(status_code=400, detail=f"Tool name '{tool_in.name}' already exists.")

    updated_tool = crud.update_tool(db, tool_id=tool_id, tool_update=tool_in)
    logger.info(f"Tool ID {tool_id} updated successfully.")
    return updated_tool

@router.delete("/api/{tool_id}", status_code=status.HTTP_204_NO_CONTENT, name="delete_tool_api", summary="Delete a tool", description="Deletes a tool by its ID.")
def delete_tool_api_route(tool_id: int, db: Session = Depends(get_db), username: str = Depends(get_current_username)):
    logger.info(f"User '{username}' deleting tool ID: {tool_id}")
    db_tool = crud.get_tool(db, tool_id=tool_id)
    if db_tool is None:
        raise HTTPException(status_code=404, detail="Tool not found")
    crud.delete_tool(db, tool_id=tool_id)
    logger.info(f"Tool ID {tool_id} ({db_tool.name}) deleted successfully.")
    # No return for 204
