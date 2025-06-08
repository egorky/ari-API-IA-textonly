import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import crud, schemas, models # Ensure models is imported
from app.core.config import settings
import base64
import json

def basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('ascii')
    return f'Basic {token}'

DEFAULT_HEADERS = {
    "Authorization": basic_auth(settings.WEB_UI_USERNAME, settings.WEB_UI_PASSWORD)
}

TOOL_NAME_API = "api_test_tool"
TOOL_DESC_API = "API test description"
TOOL_PARAMS_API = {"type": "object", "properties": {"query": {"type": "string"}}}
TOOL_CONFIG_API = {"url": "https://api.example.com/search", "method": "GET"}

def test_create_tool_api(client: TestClient, db_session: Session):
    existing_tool = crud.get_tool_by_name(db_session, name=TOOL_NAME_API)
    if existing_tool:
        crud.delete_tool(db_session, tool_id=existing_tool.id)

    tool_data = {
        "name": TOOL_NAME_API,
        "description": TOOL_DESC_API,
        "parameters": TOOL_PARAMS_API,
        "api_config": TOOL_CONFIG_API
    }
    response = client.post(
        "/ui/tools/api",
        json=tool_data,
        headers=DEFAULT_HEADERS,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == TOOL_NAME_API
    assert data["description"] == TOOL_DESC_API
    assert data["parameters"] == TOOL_PARAMS_API
    assert data["api_config"] == TOOL_CONFIG_API
    assert "id" in data

    crud.delete_tool(db_session, tool_id=data["id"])

def test_create_tool_api_duplicate_name(client: TestClient, db_session: Session):
    tool_name = "api_test_tool_duplicate"
    tool_data = {"name": tool_name, "description": "Initial tool"}

    existing_tool = crud.get_tool_by_name(db_session, name=tool_name)
    if existing_tool:
        crud.delete_tool(db_session, tool_id=existing_tool.id)

    response1 = client.post("/ui/tools/api", json=tool_data, headers=DEFAULT_HEADERS)
    assert response1.status_code == 201
    created_tool_id = response1.json()["id"]

    response2 = client.post("/ui/tools/api", json=tool_data, headers=DEFAULT_HEADERS)
    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"]

    crud.delete_tool(db_session, tool_id=created_tool_id)

def test_read_tools_api(client: TestClient, db_session: Session):
    db_session.query(models.Tool).delete()
    db_session.commit()

    crud.create_tool(db_session, schemas.ToolCreate(name="api_t1", description="d1"))
    crud.create_tool(db_session, schemas.ToolCreate(name="api_t2", description="d2"))

    response = client.get("/ui/tools/api", headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    names = [t["name"] for t in data]
    assert "api_t1" in names
    assert "api_t2" in names

def test_read_tool_api_detail(client: TestClient, db_session: Session):
    tool_in = schemas.ToolCreate(name="api_detail_tool", description="Detail content for tool")
    created_tool = crud.create_tool(db=db_session, tool=tool_in)

    response = client.get(f"/ui/tools/api/{created_tool.id}", headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "api_detail_tool"
    assert data["id"] == created_tool.id

    response_not_found = client.get("/ui/tools/api/99999", headers=DEFAULT_HEADERS)
    assert response_not_found.status_code == 404

    crud.delete_tool(db_session, tool_id=created_tool.id)

def test_update_tool_api(client: TestClient, db_session: Session):
    tool_in = schemas.ToolCreate(name="api_update_tool_orig", description="Original desc")
    created_tool = crud.create_tool(db=db_session, tool=tool_in)

    update_data = {"name": "api_update_tool_new", "description": "Updated desc", "api_config": {"url": "http://new.url"}}
    response = client.put(
        f"/ui/tools/api/{created_tool.id}",
        json=update_data,
        headers=DEFAULT_HEADERS,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "api_update_tool_new"
    assert data["description"] == "Updated desc"
    assert data["api_config"]["url"] == "http://new.url"

    response_not_found = client.put("/ui/tools/api/99999", json=update_data, headers=DEFAULT_HEADERS)
    assert response_not_found.status_code == 404

    tool_other = crud.create_tool(db_session, schemas.ToolCreate(name="another_tool_name_api", description="other tool")) # Ensure unique name
    update_data_conflict = {"name": "another_tool_name_api"}
    response_conflict = client.put(
        f"/ui/tools/api/{created_tool.id}",
        json=update_data_conflict,
        headers=DEFAULT_HEADERS,
    )
    assert response_conflict.status_code == 400
    assert "already exists" in response_conflict.json()["detail"]

    crud.delete_tool(db_session, tool_id=created_tool.id)
    crud.delete_tool(db_session, tool_id=tool_other.id)


def test_delete_tool_api(client: TestClient, db_session: Session):
    tool_in = schemas.ToolCreate(name="api_delete_tool", description="Tool to delete")
    created_tool = crud.create_tool(db=db_session, tool=tool_in)

    response = client.delete(f"/ui/tools/api/{created_tool.id}", headers=DEFAULT_HEADERS)
    assert response.status_code == 204

    check_response = client.get(f"/ui/tools/api/{created_tool.id}", headers=DEFAULT_HEADERS)
    assert check_response.status_code == 404

    response_not_found = client.delete("/ui/tools/api/99999", headers=DEFAULT_HEADERS)
    assert response_not_found.status_code == 404

def test_tool_api_unauthorized(client: TestClient):
    response = client.get("/ui/tools/api")
    assert response.status_code == 401

    response = client.post("/ui/tools/api", json={"name": "fail_tool", "description": "fail"}, headers={"Authorization": "Basic YmFkYXV0aA=="})
    assert response.status_code == 401
