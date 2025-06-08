import pytest
from sqlalchemy.orm import Session
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import crud # from app.crud
import schemas # from app.schemas
from models import Prompt # from app.models.prompt

# Test data
PROMPT_NAME_1 = "Test Crud Prompt 1"
PROMPT_CONTENT_1 = "This is the first crud test prompt."
PROMPT_METADATA_1 = {"version": 1.0, "category": "crud_test"}

PROMPT_NAME_2 = "Test Crud Prompt 2 for Update"
PROMPT_CONTENT_2 = "Initial content for crud prompt 2"

def test_create_prompt(db_session: Session):
    prompt_in = schemas.PromptCreate(name=PROMPT_NAME_1, content=PROMPT_CONTENT_1, metadata=PROMPT_METADATA_1)
    db_prompt = crud.create_prompt(db=db_session, prompt=prompt_in)
    assert db_prompt.id is not None
    assert db_prompt.name == PROMPT_NAME_1
    assert db_prompt.content == PROMPT_CONTENT_1
    assert db_prompt.metadata == PROMPT_METADATA_1

def test_get_prompt(db_session: Session):
    prompt_in = schemas.PromptCreate(name="GetCrudTestPrompt", content="Content for get crud test")
    created_prompt = crud.create_prompt(db=db_session, prompt=prompt_in)

    retrieved_prompt = crud.get_prompt(db=db_session, prompt_id=created_prompt.id)
    assert retrieved_prompt is not None
    assert retrieved_prompt.id == created_prompt.id
    assert retrieved_prompt.name == "GetCrudTestPrompt"

def test_get_prompt_by_name(db_session: Session):
    prompt_in = schemas.PromptCreate(name="GetByNameCrudPrompt", content="Content for get by name crud test")
    crud.create_prompt(db=db_session, prompt=prompt_in)

    retrieved_prompt = crud.get_prompt_by_name(db=db_session, name="GetByNameCrudPrompt")
    assert retrieved_prompt is not None
    assert retrieved_prompt.name == "GetByNameCrudPrompt"

def test_get_prompts(db_session: Session):
    db_session.query(Prompt).delete() # Clear table for this test
    db_session.commit()

    prompt1_in = schemas.PromptCreate(name="ListCrudTestPrompt1", content="Content1")
    prompt2_in = schemas.PromptCreate(name="ListCrudTestPrompt2", content="Content2")
    crud.create_prompt(db=db_session, prompt=prompt1_in)
    crud.create_prompt(db=db_session, prompt=prompt2_in)

    prompts = crud.get_prompts(db=db_session, limit=10)
    assert len(prompts) >= 2 # GTE in case other tests left data, though we tried to clear
    prompt_names = [p.name for p in prompts]
    assert "ListCrudTestPrompt1" in prompt_names
    assert "ListCrudTestPrompt2" in prompt_names

def test_update_prompt(db_session: Session):
    prompt_in = schemas.PromptCreate(name=PROMPT_NAME_2, content=PROMPT_CONTENT_2)
    created_prompt = crud.create_prompt(db=db_session, prompt=prompt_in)

    updated_content = "Updated content for crud prompt 2."
    updated_metadata = {"version": 2.0, "status": "updated_crud"}
    prompt_update_data = schemas.PromptUpdate(content=updated_content, metadata=updated_metadata)

    updated_prompt = crud.update_prompt(db=db_session, prompt_id=created_prompt.id, prompt_update=prompt_update_data)
    assert updated_prompt is not None
    assert updated_prompt.id == created_prompt.id
    assert updated_prompt.name == PROMPT_NAME_2
    assert updated_prompt.content == updated_content
    assert updated_prompt.metadata == updated_metadata

def test_delete_prompt(db_session: Session):
    prompt_in = schemas.PromptCreate(name="DeleteCrudTestPrompt", content="Content to be deleted crud")
    created_prompt = crud.create_prompt(db=db_session, prompt=prompt_in)
    prompt_id = created_prompt.id

    deleted_prompt = crud.delete_prompt(db=db_session, prompt_id=prompt_id)
    assert deleted_prompt is not None # crud.delete_prompt returns the object

    retrieved_prompt_after_delete = crud.get_prompt(db=db_session, prompt_id=prompt_id)
    assert retrieved_prompt_after_delete is None
