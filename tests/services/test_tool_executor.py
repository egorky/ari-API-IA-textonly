import pytest
import httpx
import json
from app.services.tool_executor import execute_api_tool

@pytest.mark.asyncio
async def test_execute_api_tool_get_success(httpx_mock):
    mock_url = "http://test.com/api/data"
    mock_response_data = {"key": "value", "success": True}
    httpx_mock.add_response(url=mock_url, method="GET", json=mock_response_data)

    api_config = {"url": mock_url, "method": "GET", "name": "TestGET"}
    parameters_schema = {"type": "object", "properties": {"param1": {"type": "string"}}}
    tool_input = {"param1": "test_value"}

    result_str = await execute_api_tool(api_config, parameters_schema, tool_input)
    result = json.loads(result_str)

    assert result == mock_response_data
    request = httpx_mock.get_request()
    assert request.url == httpx.URL(mock_url, params=tool_input)
    assert request.method == "GET"

@pytest.mark.asyncio
async def test_execute_api_tool_post_success(httpx_mock):
    mock_url = "http://test.com/api/submit"
    mock_response_data = {"id": 123, "status": "created"}
    # Ensure httpx_mock is configured for the specific POST request if its content matters for the mock.
    # For this test, we are checking the response, so matching URL and method is enough.
    httpx_mock.add_response(url=mock_url, method="POST", json=mock_response_data, status_code=201)

    api_config = {"url": mock_url, "method": "POST", "name": "TestPOST"}
    parameters_schema = {"type": "object", "properties": {"data": {"type": "string"}}}
    tool_input = {"data": "sample data"}

    result_str = await execute_api_tool(api_config, parameters_schema, tool_input)
    result = json.loads(result_str)

    # The original had 'assert response.status_code == 201' which is incorrect here.
    # We assert the content of the result. The status code was part of mock setup.
    assert result == mock_response_data
    request = httpx_mock.get_request()
    assert request.url == mock_url
    assert request.method == "POST"
    assert json.loads(request.content) == tool_input

@pytest.mark.asyncio
async def test_execute_api_tool_http_error(httpx_mock):
    mock_url = "http://test.com/api/error"
    httpx_mock.add_response(url=mock_url, method="GET", status_code=404, json={"detail": "Not Found"})

    api_config = {"url": mock_url, "method": "GET", "name": "TestError"}
    result_str = await execute_api_tool(api_config, None, None)

    assert "Error: API request to http://test.com/api/error failed with status 404" in result_str
    assert '"detail": "Not Found"' in result_str


@pytest.mark.asyncio
async def test_execute_api_tool_request_error(httpx_mock):
    mock_url = "http://nonexistent.domain/api"
    httpx_mock.add_exception(httpx.ConnectError("Connection failed"))

    api_config = {"url": mock_url, "method": "GET", "name": "TestConnectError"}
    result_str = await execute_api_tool(api_config, None, None)
    assert f"Error: Could not connect to API at {mock_url}" in result_str

@pytest.mark.asyncio
async def test_execute_api_tool_non_json_response(httpx_mock):
    mock_url = "http://test.com/api/text"
    mock_response_text = "This is a plain text response."
    httpx_mock.add_response(url=mock_url, method="GET", text=mock_response_text)

    api_config = {"url": mock_url, "method": "GET", "name": "TestTextResponse"}
    result_str = await execute_api_tool(api_config, None, None)
    assert result_str == mock_response_text

@pytest.mark.asyncio
async def test_execute_api_tool_missing_url():
    api_config = {"method": "GET", "name": "TestMissingURL"}
    result_str = await execute_api_tool(api_config, None, None)
    assert "Error: API URL is not defined" in result_str

@pytest.mark.asyncio
async def test_execute_api_tool_post_with_string_input_expecting_json_obj_schema(httpx_mock):
    mock_url = "http://test.com/api/post_string_obj_schema"
    api_config = {"url": mock_url, "method": "POST", "name": "TestPostStringObjSchema"}
    parameters_schema = {"type": "object", "properties": {"message": {"type": "string"}}}
    tool_input = "This is a raw string"

    # This test checks the error handling part of execute_api_tool
    # when a string is passed but an object schema is defined.
    # The tool_executor logic:
    # if parameters_schema and parameters_schema.get("type") == "object":
    #    return f"Error: Tool '{tool_name_for_log}' expects a JSON object, but received a plain string: {tool_input}"
    # This part was in the POST/PUT section:
    # if parameters_schema and parameters_schema.get("type") == "object":
    #    return f"Error: Tool '{tool_name_for_log}' expects a JSON object, but received a plain string: {tool_input}"
    # This error return should be hit.

    result_str = await execute_api_tool(api_config, parameters_schema, tool_input)
    assert "Error: Tool 'TestPostStringObjSchema' expects a JSON object, but received a plain string: This is a raw string" in result_str
    # No request should be made if this input validation fails early.
    assert len(httpx_mock.get_requests()) == 0


@pytest.mark.asyncio
async def test_execute_api_tool_post_with_json_string_input(httpx_mock):
    mock_url = "http://test.com/api/post_json_string"
    mock_response_data = {"status": "ok_json_string"}
    httpx_mock.add_response(url=mock_url, method="POST", json=mock_response_data)

    api_config = {"url": mock_url, "method": "POST", "name": "TestPostJsonString"}
    parameters_schema = {"type": "object", "properties": {"data": {"type": "string"}, "count": {"type": "integer"}}}
    tool_input_str = '{"data": "sample data", "count": 5}'

    result_str = await execute_api_tool(api_config, parameters_schema, tool_input_str)
    result = json.loads(result_str)
    assert result == mock_response_data
    request = httpx_mock.get_request()
    assert json.loads(request.content) == json.loads(tool_input_str)

@pytest.mark.asyncio
async def test_execute_api_tool_with_headers(httpx_mock):
    mock_url = "http://test.com/api/with_headers"
    custom_headers = {"X-Custom-Header": "TestValue123", "Authorization": "Bearer sometoken"}
    api_config = {"url": mock_url, "method": "GET", "name": "TestHeaders", "headers": custom_headers}

    httpx_mock.add_response(url=mock_url, method="GET", json={"status": "ok"})

    await execute_api_tool(api_config, None, None)

    request = httpx_mock.get_request()
    assert request is not None
    assert request.headers.get("X-Custom-Header") == "TestValue123"
    assert request.headers.get("Authorization") == "Bearer sometoken"
