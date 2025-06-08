import httpx
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

async def execute_api_tool(
    api_config: Dict[str, Any],
    parameters_schema: Optional[Dict[str, Any]] = None, # Schema of expected parameters for the tool
    tool_input: Any = None # Input provided by the LLM, can be a string or dict
) -> str:
    """
    Executes an API call based on the provided tool configuration and parameters.
    'parameters_schema' is the schema defined for the tool.
    'tool_input' is the actual data from the LLM for the tool's arguments.
    """
    url = api_config.get("url")
    method = api_config.get("method", "GET").upper()
    headers = api_config.get("headers", {})

    tool_name_for_log = api_config.get('name', 'Unknown Tool') # For logging

    if not url:
        logger.error(f"Tool '{tool_name_for_log}' is missing URL in api_config.")
        return "Error: API URL is not defined in tool configuration."

    request_params = {}
    request_json_data = None

    # Try to parse tool_input if it's a string and looks like JSON
    if isinstance(tool_input, str):
        try:
            parsed_input = json.loads(tool_input)
        except json.JSONDecodeError:
            if parameters_schema and parameters_schema.get("type") == "object" and len(parameters_schema.get("properties", {})) > 1:
                logger.warning(f"Tool input '{tool_input}' for tool '{tool_name_for_log}' is not JSON but multiple parameters are expected.")
                required_params = parameters_schema.get("required", [])
                props = parameters_schema.get("properties", {})
                if len(required_params) == 1 and props.get(required_params[0], {}).get("type") == "string":
                    parsed_input = {required_params[0]: tool_input}
                    logger.debug(f"Assigned string input to single required string param: {required_params[0]}")
                else:
                    return f"Error: Input '{tool_input}' for tool '{tool_name_for_log}' is not valid JSON for the expected parameters."
            else:
                parsed_input = tool_input
                logger.debug(f"Tool input for '{tool_name_for_log}' is a non-JSON string: '{tool_input}'. Using as is or based on schema.")
    elif isinstance(tool_input, dict):
        parsed_input = tool_input
    else:
        parsed_input = tool_input
        logger.debug(f"Tool input for '{tool_name_for_log}' is not string or dict: {type(tool_input)}. Using as is.")


    if method == "GET":
        if isinstance(parsed_input, dict):
            request_params = parsed_input
        elif parameters_schema: # Input is not a dict (e.g. string, number) but schema exists
            param_names = list(parameters_schema.get("properties", {}).keys())
            if len(param_names) == 1: # Single parameter expected
                 # Ensure the type matches if possible, or let the API handle mismatch.
                param_type = parameters_schema["properties"][param_names[0]].get("type")
                if isinstance(parsed_input, str) and param_type != "string":
                    logger.warning(f"Tool '{tool_name_for_log}' param '{param_names[0]}' expects {param_type} but got string '{parsed_input}'. API might coerce or fail.")
                request_params[param_names[0]] = parsed_input
            elif parsed_input is not None : # Multiple params expected, but input is not a dict
                logger.warning(f"GET request for tool '{tool_name_for_log}' received non-dict input '{parsed_input}' but expects multiple params or a JSON object string.")
        # If no parameters_schema, and tool_input is string/number, it's not used for query params unless logic is added.

    elif method in ["POST", "PUT", "PATCH"]:
        if isinstance(parsed_input, dict):
            request_json_data = parsed_input
        elif isinstance(parsed_input, str):
            try: # If LLM provides a JSON string for a POST body
                request_json_data = json.loads(parsed_input)
            except json.JSONDecodeError:
                if parameters_schema and parameters_schema.get("type") == "object":
                     return f"Error: Tool '{tool_name_for_log}' expects a JSON object, but received a plain string: {tool_input}"
                # If schema expects a string (e.g. "text/plain"), this could be it.
                # For now, we assume JSON or simple value wrapping.
                request_json_data = {"value": parsed_input}
                logger.warning(f"Non-JSON string input for {method} tool '{tool_name_for_log}'. Wrapped as {{'value': ...}}.")
        else:
            request_json_data = {"value": parsed_input}
            logger.debug(f"Scalar input for {method} tool '{tool_name_for_log}'. Wrapped as {{'value': ...}}.")


    logger.info(f"Executing Tool: {tool_name_for_log}")
    logger.debug(f"Method: {method}, URL: {url}")
    logger.debug(f"Headers: {headers}")
    logger.debug(f"Query Params: {request_params}")
    logger.debug(f"JSON Body: {request_json_data}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                params=request_params if method == "GET" and request_params else None, # ensure request_params is not None
                json=request_json_data if method in ["POST", "PUT", "PATCH"] and isinstance(request_json_data, (dict, list)) else None,
                data=request_json_data if method in ["POST", "PUT", "PATCH"] and isinstance(request_json_data, str) else None,
                headers=headers,
                timeout=20.0
            )
            response.raise_for_status()

            try:
                return json.dumps(response.json())
            except json.JSONDecodeError:
                return response.text
            except Exception as e:
                logger.error(f"Error processing response from {url} as JSON: {e}")
                return response.text

    except httpx.HTTPStatusError as e:
        error_text = f"Error: API request to {url} failed with status {e.response.status_code}."
        try:
            error_details = e.response.json()
            error_text += f" Details: {json.dumps(error_details)}"
        except json.JSONDecodeError:
            error_text += f" Details: {e.response.text[:200]}"
        logger.error(error_text, exc_info=False) # exc_info=False to avoid full traceback for HTTP errors unless debug
        return error_text
    except httpx.RequestError as e:
        logger.error(f"Request error for {url}: {e}", exc_info=True)
        return f"Error: Could not connect to API at {url}. Details: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during API call for {url}: {e}", exc_info=True)
        return f"Error: An unexpected error occurred during the API call. {str(e)}"
