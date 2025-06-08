import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app import schemas, crud, models # Ensure models is imported to access Prompt model for delete query
from app.core.config import settings
import base64
import json

# Helper to create basic auth header
def basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode('utf-8')).decode('ascii')
    return f'Basic {token}'

DEFAULT_HEADERS = {
    "Authorization": basic_auth(settings.WEB_UI_USERNAME, settings.WEB_UI_PASSWORD)
}

def test_create_prompt_api(client: TestClient, db_session: Session):
    prompt_name = "api_test_prompt"
    # Ensure prompt doesn't exist
    existing_prompt = crud.get_prompt_by_name(db_session, name=prompt_name)
    if existing_prompt:
        crud.delete_prompt(db_session, prompt_id=existing_prompt.id)

    response = client.post(
        "/ui/prompts/api",
        json={"name": prompt_name, "content": "API test content", "metadata": {"source": "api_test"}},
        headers=DEFAULT_HEADERS,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == prompt_name
    assert data["content"] == "API test content"
    assert data["metadata"]["source"] == "api_test"
    assert "id" in data

    # Clean up
    crud.delete_prompt(db_session, prompt_id=data["id"])

def test_create_prompt_api_duplicate_name(client: TestClient, db_session: Session):
    prompt_name = "api_test_prompt_duplicate"
    prompt_data = {"name": prompt_name, "content": "Initial content", "metadata": {}}

    # Ensure prompt doesn't exist from a previous failed run
    existing_prompt = crud.get_prompt_by_name(db_session, name=prompt_name)
    if existing_prompt:
        crud.delete_prompt(db_session, prompt_id=existing_prompt.id)

    response1 = client.post("/ui/prompts/api", json=prompt_data, headers=DEFAULT_HEADERS)
    assert response1.status_code == 201
    created_prompt_id = response1.json()["id"]

    # Attempt to create another with the same name
    response2 = client.post("/ui/prompts/api", json=prompt_data, headers=DEFAULT_HEADERS)
    assert response2.status_code == 400
    assert "already registered" in response2.json()["detail"]

    # Clean up
    crud.delete_prompt(db_session, prompt_id=created_prompt_id)


def test_read_prompts_api(client: TestClient, db_session: Session):
    # Clear existing and add a couple
    db_session.query(models.Prompt).delete() # Use actual model for delete
    db_session.commit()

    crud.create_prompt(db_session, schemas.PromptCreate(name="api_p1", content="c1"))
    crud.create_prompt(db_session, schemas.PromptCreate(name="api_p2", content="c2"))

    response = client.get("/ui/prompts/api", headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    names = [p["name"] for p in data]
    assert "api_p1" in names
    assert "api_p2" in names

def test_read_prompt_api_detail(client: TestClient, db_session: Session):
    prompt_in = schemas.PromptCreate(name="api_detail_prompt", content="Detail content")
    created_prompt = crud.create_prompt(db=db_session, prompt=prompt_in)

    response = client.get(f"/ui/prompts/api/{created_prompt.id}", headers=DEFAULT_HEADERS)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "api_detail_prompt"
    assert data["id"] == created_prompt.id

    # Test not found
    response_not_found = client.get("/ui/prompts/api/99999", headers=DEFAULT_HEADERS)
    assert response_not_found.status_code == 404

    # Clean up
    crud.delete_prompt(db_session, prompt_id=created_prompt.id)

def test_update_prompt_api(client: TestClient, db_session: Session):
    prompt_in = schemas.PromptCreate(name="api_update_prompt_orig", content="Original content")
    created_prompt = crud.create_prompt(db=db_session, prompt=prompt_in)

    update_data = {"name": "api_update_prompt_new", "content": "Updated content", "metadata": {"status": "updated"}}
    response = client.put(
        f"/ui/prompts/api/{created_prompt.id}",
        json=update_data,
        headers=DEFAULT_HEADERS,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "api_update_prompt_new"
    assert data["content"] == "Updated content"
    assert data["metadata"]["status"] == "updated"

    # Test update non-existent
    response_not_found = client.put("/ui/prompts/api/99999", json=update_data, headers=DEFAULT_HEADERS)
    assert response_not_found.status_code == 404

    prompt_other = crud.create_prompt(db_session, schemas.PromptCreate(name="another_prompt_name", content="other"))
    update_data_conflict = {"name": "another_prompt_name"}
    response_conflict = client.put(
        f"/ui/prompts/api/{created_prompt.id}",
        json=update_data_conflict,
        headers=DEFAULT_HEADERS,
    )
    assert response_conflict.status_code == 400
    assert "already exists" in response_conflict.json()["detail"]

    # Clean up
    crud.delete_prompt(db_session, prompt_id=created_prompt.id)
    crud.delete_prompt(db_session, prompt_id=prompt_other.id)


def test_delete_prompt_api(client: TestClient, db_session: Session):
    prompt_in = schemas.PromptCreate(name="api_delete_prompt", content="Content to delete")
    created_prompt = crud.create_prompt(db=db_session, prompt=prompt_in)

    response = client.delete(f"/ui/prompts/api/{created_prompt.id}", headers=DEFAULT_HEADERS)
    assert response.status_code == 204

    # Verify it's deleted
    check_response = client.get(f"/ui/prompts/api/{created_prompt.id}", headers=DEFAULT_HEADERS)
    assert check_response.status_code == 404

    # Test delete non-existent
    response_not_found = client.delete("/ui/prompts/api/99999", headers=DEFAULT_HEADERS)
    assert response_not_found.status_code == 404

def test_prompt_api_unauthorized(client: TestClient):
    response = client.get("/ui/prompts/api")
    assert response.status_code == 401

    response = client.post("/ui/prompts/api", json={"name": "fail", "content": "fail"}, headers={"Authorization": "Basic YmFkYXV0aA=="}) # "badauth"
    assert response.status_code == 401
