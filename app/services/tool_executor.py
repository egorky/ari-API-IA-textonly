import httpx
import json
import logging
from typing import Dict, Any, Optional
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

async def execute_api_tool(
    api_config: Dict[str, Any],
    parameters_schema: Optional[Dict[str, Any]] = None, # Schema of expected parameters for the tool
    tool_input: Any = None
) -> str:
    """Executes an API call based on tool configuration and LLM-provided input.

    This function takes the API configuration of a tool (URL, method, headers),
    the JSON schema defining the tool's expected parameters, and the actual input
    from the LLM. It validates the input against the schema, then constructs and
    executes an asynchronous HTTP request using `httpx.AsyncClient`.
    The response from the external API is processed and returned as a string,
    suitable for feeding back to the LLM.

    Args:
        api_config: A dictionary containing the API configuration for the tool.
            Expected keys:
            - "url" (str): The target URL for the API call.
            - "method" (str, optional): The HTTP method (e.g., "GET", "POST").
              Defaults to "GET".
            - "headers" (Dict[str, str], optional): HTTP headers for the request.
            - "name" (str, optional): Name of the tool, used for logging.
        parameters_schema: An optional dictionary representing the JSON schema
            against which `tool_input` will be validated. If None, no
            JSON schema validation is performed (though basic type checks might still occur).
        tool_input: The input data for the tool, provided by the LLM. This can be
            a dictionary (if the LLM structures arguments), a JSON string, or a
            simple scalar value. The function attempts to parse it appropriately
            before validation and request construction.

    Returns:
        A string representing the result of the API call.
        - If successful and the response is JSON, it's a JSON string.
        - If successful and the response is not JSON, it's the plain text response.
        - In case of validation errors (jsonschema ValidationError), HTTP errors
          (4xx/5xx status codes), or connection issues, it returns a
          descriptive error string prefixed with "Error:".
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

    parsed_input: Any # Define type for parsed_input

    # Try to parse tool_input if it's a string and looks like JSON
    if isinstance(tool_input, str):
        try:
            parsed_input = json.loads(tool_input)
        except json.JSONDecodeError:
            # This specific heuristic might be too complex or better handled by schema validation itself if schema expects an object.
            # If schema expects a string, then this non-JSON string is the value.
            # Let's simplify and let validation catch issues if the schema expects an object/specific types.
            parsed_input = tool_input # Keep as string if not parsable as JSON
            logger.debug(f"Tool input for '{tool_name_for_log}' is a non-JSON string: '{tool_input}'. Will be validated against schema.")
    elif isinstance(tool_input, dict):
        parsed_input = tool_input
    else:
        # For non-string, non-dict types (e.g. numbers, booleans directly from LLM if that happens)
        parsed_input = tool_input
        logger.debug(f"Tool input for '{tool_name_for_log}' is of type {type(tool_input)}. Using as is for validation.")

    # Validate parsed_input against parameters_schema if schema is provided
    if parameters_schema and isinstance(parameters_schema, dict) and parameters_schema: # Ensure schema is a non-empty dict
        try:
            # Ensure that if the schema type is "object", the instance is a dict.
            # If schema type is "string", instance should be string, etc.
            # jsonschema handles this, but LLMs might pass a string for an object with one param.
            # Example: tool expects {"location": "london"}, LLM might send "london".
            # The schema should define the expected structure. If schema expects an object, parsed_input should be a dict.
            # The previous logic for auto-wrapping a single string input into a dict for a single-param object
            # has been removed in favor of stricter schema validation.
            # If the schema expects {"type": "object", "properties": {"param_name": {"type": "string"}}}
            # and parsed_input is "value", validation will fail.
            # If schema expects {"type": "string"}, and parsed_input is "value", it will pass.

            validate(instance=parsed_input, schema=parameters_schema)
            logger.info(f"Tool input for '{tool_name_for_log}' validated successfully against schema.")
        except ValidationError as e:
            error_message = f"Error: Invalid parameters for tool '{tool_name_for_log}'. Details: {e.message}"
            logger.error(f"Tool input validation error for tool '{tool_name_for_log}': {e.message} (Path: {list(e.path)}, Validator: {e.validator})")
            return error_message
        except Exception as e: # Catch other jsonschema errors, though ValidationError is primary
            error_message = f"Error: Schema validation failed for tool '{tool_name_for_log}'. Details: {str(e)}"
            logger.error(f"Unexpected schema validation error for tool '{tool_name_for_log}': {str(e)}", exc_info=True)
            return error_message

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
