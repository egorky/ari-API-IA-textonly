import pytest
from sqlalchemy.orm import Session
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import crud # from app.crud
import schemas # from app.schemas
from models import Tool # from app.models.tool

# Test data for Tools
TOOL_NAME_1 = "Test Crud Tool 1"
TOOL_DESC_1 = "Description for test crud tool 1"
TOOL_PARAMS_1 = {"param1": {"type": "string"}, "param2": {"type": "integer"}}
TOOL_API_CONFIG_1 = {"url": "http://example.com/api/crudtool1", "method": "POST"}

TOOL_NAME_2 = "Test Crud Tool 2 for Update"
TOOL_DESC_2 = "Initial description for crud tool 2"

def test_create_tool(db_session: Session):
    tool_in = schemas.ToolCreate(
        name=TOOL_NAME_1,
        description=TOOL_DESC_1,
        parameters=TOOL_PARAMS_1,
        api_config=TOOL_API_CONFIG_1
    )
    db_tool = crud.create_tool(db=db_session, tool=tool_in)
    assert db_tool.id is not None
    assert db_tool.name == TOOL_NAME_1
    assert db_tool.description == TOOL_DESC_1
    assert db_tool.parameters == TOOL_PARAMS_1
    assert db_tool.api_config == TOOL_API_CONFIG_1

def test_get_tool(db_session: Session):
    tool_in = schemas.ToolCreate(name="GetCrudTestTool", description="Content for get crud test")
    created_tool = crud.create_tool(db=db_session, tool=tool_in)

    retrieved_tool = crud.get_tool(db=db_session, tool_id=created_tool.id)
    assert retrieved_tool is not None
    assert retrieved_tool.id == created_tool.id
    assert retrieved_tool.name == "GetCrudTestTool"

def test_get_tool_by_name(db_session: Session):
    tool_in = schemas.ToolCreate(name="GetByNameCrudTool", description="Content for get by name crud test")
    crud.create_tool(db=db_session, tool=tool_in)

    retrieved_tool = crud.get_tool_by_name(db=db_session, name="GetByNameCrudTool")
    assert retrieved_tool is not None
    assert retrieved_tool.name == "GetByNameCrudTool"

def test_get_tools(db_session: Session):
    db_session.query(Tool).delete() # Clear table
    db_session.commit()

    tool1_in = schemas.ToolCreate(name="ListCrudTestTool1", description="DescCrud1")
    tool2_in = schemas.ToolCreate(name="ListCrudTestTool2", description="DescCrud2")
    crud.create_tool(db=db_session, tool=tool1_in)
    crud.create_tool(db=db_session, tool=tool2_in)

    tools = crud.get_tools(db=db_session, limit=10)
    assert len(tools) >= 2
    tool_names = [t.name for t in tools]
    assert "ListCrudTestTool1" in tool_names
    assert "ListCrudTestTool2" in tool_names

def test_update_tool(db_session: Session):
    tool_in = schemas.ToolCreate(name=TOOL_NAME_2, description=TOOL_DESC_2)
    created_tool = crud.create_tool(db=db_session, tool=tool_in)

    updated_description = "Updated description for crud tool 2."
    updated_api_config = {"url": "http://newcrud.example.com/api", "method": "PUT"}
    tool_update_data = schemas.ToolUpdate(description=updated_description, api_config=updated_api_config)

    updated_tool = crud.update_tool(db=db_session, tool_id=created_tool.id, tool_update=tool_update_data)
    assert updated_tool is not None
    assert updated_tool.id == created_tool.id
    assert updated_tool.name == TOOL_NAME_2
    assert updated_tool.description == updated_description
    assert updated_tool.api_config == updated_api_config

def test_delete_tool(db_session: Session):
    tool_in = schemas.ToolCreate(name="DeleteCrudTestTool", description="Tool to be deleted crud")
    created_tool = crud.create_tool(db=db_session, tool=tool_in)
    tool_id = created_tool.id

    deleted_tool = crud.delete_tool(db=db_session, tool_id=tool_id)
    assert deleted_tool is not None

    retrieved_tool_after_delete = crud.get_tool(db=db_session, tool_id=tool_id)
    assert retrieved_tool_after_delete is None
