from sqlalchemy.orm import Session
from typing import List, Optional
from . import models, schemas

# --- Prompt CRUD operations ---

def get_prompt(db: Session, prompt_id: int) -> Optional[models.Prompt]:
    """
    Retrieves a single prompt from the database by its ID.

    Args:
        db: The SQLAlchemy database session.
        prompt_id: The ID of the prompt to retrieve.

    Returns:
        The Prompt model instance if found, otherwise None.
    """
    return db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()

def get_prompt_by_name(db: Session, name: str) -> Optional[models.Prompt]:
    """
    Retrieves a single prompt from the database by its unique name.

    Args:
        db: The SQLAlchemy database session.
        name: The unique name of the prompt to retrieve.

    Returns:
        The Prompt model instance if found, otherwise None.
    """
    return db.query(models.Prompt).filter(models.Prompt.name == name).first()

def get_prompts(db: Session, skip: int = 0, limit: int = 100) -> List[models.Prompt]:
    """
    Retrieves a list of prompts from the database, with pagination.

    Args:
        db: The SQLAlchemy database session.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        A list of Prompt model instances.
    """
    return db.query(models.Prompt).offset(skip).limit(limit).all()

def create_prompt(db: Session, prompt: schemas.PromptCreate) -> models.Prompt:
    """
    Creates a new prompt in the database.

    Args:
        db: The SQLAlchemy database session.
        prompt: A PromptCreate schema object containing the data for the new prompt.

    Returns:
        The newly created Prompt model instance.
    """
    db_prompt = models.Prompt(**prompt.model_dump())
    db.add(db_prompt)
    db.commit()
    db.refresh(db_prompt)
    return db_prompt

def update_prompt(db: Session, prompt_id: int, prompt_update: schemas.PromptUpdate) -> Optional[models.Prompt]:
    """
    Updates an existing prompt in the database.

    Args:
        db: The SQLAlchemy database session.
        prompt_id: The ID of the prompt to update.
        prompt_update: A PromptUpdate schema object containing the data to update.
                       Only fields present in prompt_update will be modified.

    Returns:
        The updated Prompt model instance if found and updated, otherwise None.
    """
    db_prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if db_prompt:
        update_data = prompt_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_prompt, key, value)
        db.commit()
        db.refresh(db_prompt)
    return db_prompt

def delete_prompt(db: Session, prompt_id: int) -> Optional[models.Prompt]:
    """
    Deletes a prompt from the database.

    Args:
        db: The SQLAlchemy database session.
        prompt_id: The ID of the prompt to delete.

    Returns:
        The Prompt model instance that was deleted if found, otherwise None.
    """
    db_prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if db_prompt:
        db.delete(db_prompt)
        db.commit()
    return db_prompt

# --- Tool CRUD operations ---

def get_tool(db: Session, tool_id: int) -> Optional[models.Tool]:
    """
    Retrieves a single tool from the database by its ID.

    Args:
        db: The SQLAlchemy database session.
        tool_id: The ID of the tool to retrieve.

    Returns:
        The Tool model instance if found, otherwise None.
    """
    return db.query(models.Tool).filter(models.Tool.id == tool_id).first()

def get_tool_by_name(db: Session, name: str) -> Optional[models.Tool]:
    """
    Retrieves a single tool from the database by its unique name.

    Args:
        db: The SQLAlchemy database session.
        name: The unique name of the tool to retrieve.

    Returns:
        The Tool model instance if found, otherwise None.
    """
    return db.query(models.Tool).filter(models.Tool.name == name).first()

def get_tools(db: Session, skip: int = 0, limit: int = 100) -> List[models.Tool]:
    """
    Retrieves a list of tools from the database, with pagination.

    Args:
        db: The SQLAlchemy database session.
        skip: The number of records to skip (for pagination).
        limit: The maximum number of records to return.

    Returns:
        A list of Tool model instances.
    """
    return db.query(models.Tool).offset(skip).limit(limit).all()

def create_tool(db: Session, tool: schemas.ToolCreate) -> models.Tool:
    """
    Creates a new tool in the database.

    Args:
        db: The SQLAlchemy database session.
        tool: A ToolCreate schema object containing the data for the new tool.

    Returns:
        The newly created Tool model instance.
    """
    db_tool = models.Tool(**tool.model_dump())
    db.add(db_tool)
    db.commit()
    db.refresh(db_tool)
    return db_tool

def update_tool(db: Session, tool_id: int, tool_update: schemas.ToolUpdate) -> Optional[models.Tool]:
    """
    Updates an existing tool in the database.

    Args:
        db: The SQLAlchemy database session.
        tool_id: The ID of the tool to update.
        tool_update: A ToolUpdate schema object containing the data to update.
                       Only fields present in tool_update will be modified.

    Returns:
        The updated Tool model instance if found and updated, otherwise None.
    """
    db_tool = db.query(models.Tool).filter(models.Tool.id == tool_id).first()
    if db_tool:
        update_data = tool_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_tool, key, value)
        db.commit()
        db.refresh(db_tool)
    return db_tool

def delete_tool(db: Session, tool_id: int) -> Optional[models.Tool]:
    """
    Deletes a tool from the database.

    Args:
        db: The SQLAlchemy database session.
        tool_id: The ID of the tool to delete.

    Returns:
        The Tool model instance that was deleted if found, otherwise None.
    """
    db_tool = db.query(models.Tool).filter(models.Tool.id == tool_id).first()
    if db_tool:
        db.delete(db_tool)
        db.commit()
    return db_tool
