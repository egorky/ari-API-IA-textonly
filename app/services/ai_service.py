import logging
import json
import os
from typing import List, Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage # AIMessage also needed
from langchain_core.tools import Tool as LangchainTool
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import RedisChatMessageHistory # Corrected import

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Agent-specific imports
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.agents.format_scratchpad.openai_functions import format_to_openai_function_messages
from langchain.agents.output_parsers.openai_functions import OpenAIFunctionsAgentOutputParser

# For RunnableWithMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


import re # For JavaScript processing in prompts
from app.core.config import settings
from app.services.redis_service import get_redis_client
from app.services.tool_executor import execute_api_tool
from app import crud # Assuming crud.py is in app directory, not app.crud if accessing directly
from sqlalchemy.orm import Session # For type hinting db session

logger = logging.getLogger(__name__)

# Attempt to import MiniRacer and set up context for JavaScript processing
PY_MINI_RACER_AVAILABLE = False
JS_CONTEXT = None
try:
    from py_mini_racer import MiniRacer
    JS_CONTEXT = MiniRacer()
    PY_MINI_RACER_AVAILABLE = True
    logger.info("py_mini_racer imported successfully. JavaScript processing in prompts is enabled.")
except ImportError:
    logger.warning("py_mini_racer not found. JavaScript processing in prompts will be disabled. Please install it if needed.")
except Exception as e:
    logger.error(f"Error initializing MiniRacer: {e}. JavaScript processing in prompts will be disabled.")
    JS_CONTEXT = None # Ensure context is None if initialization failed
    PY_MINI_RACER_AVAILABLE = False


DEFAULT_SYSTEM_PROMPT_FOR_AGENT = "You are a helpful assistant. You have access to the following tools. Use them when appropriate."

# Function to process JavaScript snippets in prompts
def process_prompt_javascript(prompt_content: str) -> str:
    """
    Processes JavaScript snippets embedded in prompt content.

    This function searches for JavaScript code snippets wrapped in double curly
    braces (e.g., `{{ new Date().getFullYear() }}`) within the provided
    `prompt_content` string. If `py_mini_racer` is available and initialized,
    it executes these snippets and replaces them with their string results.

    If `py_mini_racer` is not available, or if `JS_CONTEXT` (the MiniRacer instance)
    is None, or if the `prompt_content` is empty, the original content is returned
    unmodified. A warning is logged if snippets are present but `py_mini_racer`
    is unavailable.

    Errors during the execution of individual JavaScript snippets are caught,
    logged, and the original snippet is left unprocessed in the content. This
    prevents a single faulty snippet from breaking the entire prompt processing.

    Args:
        prompt_content: The string content of the prompt, potentially containing
                        JavaScript snippets.

    Returns:
        The prompt content string with JavaScript snippets evaluated and replaced
        by their results. If JS processing is disabled or an error occurs with
        a snippet, the original snippet might remain or be handled as per error logic.
    """
    if not PY_MINI_RACER_AVAILABLE or not prompt_content or not JS_CONTEXT:
        if not PY_MINI_RACER_AVAILABLE and "{{" in prompt_content: # Log only if JS snippets are present but processor is unavailable
             logger.warning("JavaScript snippets found in prompt, but py_mini_racer is not available or failed to initialize. Snippets will not be processed.")
        return prompt_content

    processed_content = prompt_content
    # Using finditer to handle multiple occurrences and replacements correctly
    # Find non-overlapping matches
    matches = list(re.finditer(r"\{\{(.*?)\}\}", prompt_content))

    # Iterate in reverse to maintain correct indices after replacements
    for match in reversed(matches):
        original_snippet_with_braces = match.group(0)
        js_code = match.group(1).strip()

        if not js_code:
            logger.warning(f"Empty JavaScript snippet found: {original_snippet_with_braces}. Skipping.")
            continue

        try:
            logger.debug(f"Attempting to execute JS snippet: {js_code}")
            js_result = JS_CONTEXT.eval(js_code)
            result_str = str(js_result) # Ensure result is a string

            # Replace the specific match in the current state of processed_content
            # Re.sub can be tricky with overlapping matches or multiple replaces in one go on original string.
            # Manual replacement on `processed_content` using match start/end ensures accuracy.
            start_index, end_index = match.span()
            processed_content = processed_content[:start_index] + result_str + processed_content[end_index:]

            logger.debug(f"Successfully executed JS: '{js_code}', result: '{result_str}'. Snippet '{original_snippet_with_braces}' replaced.")
        except Exception as e:
            # In case of an error executing a specific snippet, log it and leave the original snippet in place.
            logger.error(f"Error executing JS snippet '{original_snippet_with_braces}': {e}. Snippet will remain unprocessed.")
            # Optionally, replace with an error marker:
            # processed_content = processed_content[:start_index] + "[JS Execution Error]" + processed_content[end_index:]

    if prompt_content != processed_content:
        logger.info("JavaScript snippets processed in prompt content.")
    return processed_content

def load_langchain_tools_from_db(db: Session) -> List[LangchainTool]:
    """
    Loads tool definitions from the database and converts them into LangchainTool objects.

    This function retrieves tool configurations stored in the database via `crud.get_tools`.
    These configurations include the tool's name, description, a JSON schema
    defining its expected parameters (`db_tool_data.parameters`), and API
    configuration details (`db_tool_data.api_config` such as URL, method, headers).

    It then constructs `LangchainTool` objects. Each tool is given an asynchronous
    coroutine (`specific_tool_coro`) as its callable function. This coroutine,
    when invoked by a LangChain agent, calls `execute_api_tool` with the
    tool's specific `api_config`, `parameters_schema`, and the input provided by the agent.
    A closure is used to ensure that `specific_tool_coro` correctly captures
    the `name`, `config`, and `schema` for each distinct tool from the loop.

    The `db_tool_data.parameters` field is crucial as it's used by agents (like
    OpenAI Functions or Gemini with tool binding) to understand how to structure
    arguments for the tool. The `db_tool_data.api_config` dictates how
    `execute_api_tool` will make the actual HTTP call.

    Args:
        db: The SQLAlchemy database session used to fetch tool definitions.

    Returns:
        A list of `LangchainTool` objects. If no tools are found in the database
        or if essential configuration like `api_config.url` is missing for a tool,
        that tool is skipped, and an empty list might be returned.
    """
    db_tools = crud.get_tools(db=db, limit=100) # Pass db session to crud function
    langchain_tools = []
    for db_tool_data in db_tools:
        if not db_tool_data.api_config or not db_tool_data.api_config.get("url"):
            logger.warning(f"Tool '{db_tool_data.name}' is missing api_config or URL, skipping.")
            continue

        # Closure to capture loop variables correctly for the coroutine
        def create_coroutine(name, config, schema):
            async def specific_tool_coro(tool_input_str_or_dict: Any) -> str: # Input can be dict from OpenAI agent
                logger.info(f"Langchain Tool '{name}' invoked with input: {tool_input_str_or_dict}")
                tool_input_data = tool_input_str_or_dict

                # OpenAI functions agent often directly provides a dictionary of arguments.
                # If it's a string, it might be from a different type of agent or direct call.
                if isinstance(tool_input_str_or_dict, str):
                    try:
                        tool_input_data = json.loads(tool_input_str_or_dict)
                    except json.JSONDecodeError:
                        # If schema expects a single string, this is fine.
                        # If schema expects an object, this is an issue handled by execute_api_tool.
                        logger.debug(f"Tool input for '{name}' is not JSON: {tool_input_str_or_dict}. Passing as is.")
                        pass # tool_input_data remains tool_input_str_or_dict

                return await execute_api_tool(
                    api_config=config, # This should include the tool name for logging inside execute_api_tool
                    parameters_schema=schema,
                    tool_input=tool_input_data
                )
            return specific_tool_coro

        # Add tool name to api_config for logging inside execute_api_tool
        current_api_config = db_tool_data.api_config.copy()
        current_api_config['name'] = db_tool_data.name

        tool_description = db_tool_data.description or f"Tool named {db_tool_data.name}."
        # For OpenAI functions agent, the parameters schema is part of the function definition sent to OpenAI
        # The description should be human-readable. Langchain's OpenAI agent creation handles schema.
        # No need to append JSON schema to description for OpenAI functions agent.

        langchain_tool = LangchainTool(
            name=db_tool_data.name,
            coro=create_coroutine(db_tool_data.name, current_api_config, db_tool_data.parameters),
            description=tool_description,
            # args_schema is not directly used by create_openai_functions_agent in this way.
            # The function schema is derived from the tool name, description, and parameters for OpenAI.
        )
        langchain_tools.append(langchain_tool)
        logger.info(f"Loaded Langchain Tool: {db_tool_data.name}")
    return langchain_tools

async def get_ai_response(
    text_input: str,
    session_id: str,
    db: Session,
    model_preference: Optional[str] = None,
    prompt_name: Optional[str] = None,
    prompt_content_override: Optional[str] = None,
) -> str:
    """
    Processes a user's text input and returns an AI-generated response.

    This is the core function for interacting with the AI. It orchestrates:
    1.  Model Selection: Chooses between OpenAI or Gemini based on `model_preference`
        (e.g., from dialplan), then `settings.DEFAULT_AI_MODEL`, falling back to
        a hardcoded default if necessary.
    2.  LLM Initialization: Instantiates the appropriate LangChain LLM client
        (ChatOpenAI or ChatGoogleGenerativeAI) using API keys and model names
        from `settings`.
    3.  Tool Loading: Calls `load_langchain_tools_from_db` to fetch and prepare
        any tools (API integrations) defined in the database.
    4.  Memory Setup: Initializes chat message history. It attempts to use
        `RedisChatMessageHistory` keyed by `session_id` (prefixed with
        "ari_chat_history:"). If Redis is unavailable, it falls back to
        `InMemoryChatMessageHistory` for the current interaction.
    5.  Prompt Processing:
        a.  Determines the system prompt:
            - Priority 1: `prompt_content_override` (if provided, e.g., from testing UI).
            - Priority 2: Content of prompt loaded from DB by `prompt_name` (if provided).
            - Priority 3: `DEFAULT_SYSTEM_PROMPT_FOR_AGENT`.
        b.  Calls `process_prompt_javascript` to execute any `{{ }}` JavaScript
            snippets within the determined prompt content, using `py_mini_racer` if available.
    6.  Agent Construction:
        a.  If tools are available and the model is OpenAI, an agent is created
            using `create_openai_functions_agent` and `AgentExecutor`.
        b.  If tools are available and the model is Gemini, an agent is created by
            binding tools to the LLM (`llm.bind_tools()`) and using `AgentExecutor`
            with `OpenAIFunctionsAgentOutputParser`.
        c.  If no tools are available or the model is not set up for tools,
            a simpler `ConversationChain` with memory is used as a fallback.
    7.  History Management: `RunnableWithMessageHistory` is used to wrap the
        agent or chain, enabling automatic loading from and saving to the
        configured message history (Redis or in-memory).
    8.  Invocation: The agent/chain is invoked with the `text_input` and `session_id`.
    9.  Response: The AI's final response is returned as a string.

    Args:
        text_input: The user's input string to the AI.
        session_id: A unique identifier for the current conversation session,
            typically the Asterisk channel's UNIQUEID. Used for memory.
        db: The SQLAlchemy database session, used for loading prompts and tools.
        model_preference: Optional. The preferred AI model ('openai' or 'gemini').
            Overrides `settings.DEFAULT_AI_MODEL`.
        prompt_name: Optional. The name of a pre-defined prompt to load from the
            database.
        prompt_content_override: Optional. A string containing the full prompt
            content, overriding any prompt loaded by `prompt_name` or the default.
            Primarily used for testing.

    Returns:
        A string containing the AI's generated response. In case of critical
        errors (e.g., API key misconfiguration, LLM initialization failure),
        a descriptive error message string is returned.
    """
    logger.info(f"AI Service call: session_id='{session_id}', model_preference='{model_preference}', prompt_name='{prompt_name}', override_used={'Yes' if prompt_content_override else 'No'}, input='{text_input[:50]}...'")

    chosen_model_name = model_preference if model_preference else settings.DEFAULT_AI_MODEL
    logger.info(f"Chosen AI model type: {chosen_model_name}")

    llm = None
    is_openai_model = False
    is_gemini_model = False # New flag for Gemini
    if chosen_model_name.lower() == 'openai':
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == 'your_openai_api_key_here':
            logger.error("OpenAI API key is not configured.")
            return "Error: OpenAI API key not configured."
        try:
            llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name=settings.OPENAI_MODEL_NAME, temperature=0)
            is_openai_model = True
            logger.info(f"Using OpenAI model: {settings.OPENAI_MODEL_NAME}.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI LLM: {e}", exc_info=True)
            return f"Error: Could not initialize OpenAI model. {str(e)}"
    elif chosen_model_name.lower() == 'gemini':
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == 'your_gemini_api_key_here':
            logger.error("Gemini API key is not configured.")
            return "Error: Gemini API key not configured."
        try:
            # Using the new GEMINI_MODEL_NAME from settings
            llm = ChatGoogleGenerativeAI(model=settings.GEMINI_MODEL_NAME, google_api_key=settings.GEMINI_API_KEY, convert_system_message_to_human=True, temperature=0)
            is_gemini_model = True # Set the flag
            logger.info(f"Using Google Gemini model: {settings.GEMINI_MODEL_NAME}.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}", exc_info=True)
            return f"Error: Could not initialize Gemini model. {str(e)}"
    else:
        logger.error(f"Unsupported AI model type: {chosen_model_name}")
        return f"Error: Unsupported AI model type '{chosen_model_name}'. Please choose 'openai' or 'gemini'."

    if llm is None: # Should have been caught by previous checks
        return "Error: LLM could not be initialized."

    tools = load_langchain_tools_from_db(db)
    logger.info(f"Loaded {len(tools)} tools for the agent: {[tool.name for tool in tools]}")

    redis_client = get_redis_client()
    message_history = None
    if not redis_client:
        logger.warning("Redis client is not available. Falling back to in-memory chat history for this session.")
        from langchain.memory import ChatMessageHistory as InMemoryChatMessageHistory # Local import
        message_history = InMemoryChatMessageHistory()
    else:
        try:
            redis_client.ping()
            redis_auth_part = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else ""
            redis_url = f"redis://{redis_auth_part}{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"

            message_history = RedisChatMessageHistory(
                session_id=f"ari_chat_history:{session_id}", url=redis_url
            )
            logger.info(f"RedisChatMessageHistory setup for session_id: ari_chat_history:{session_id}")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error for message history: {e}. Falling back to in-memory for this session.")
            from langchain.memory import ChatMessageHistory as InMemoryChatMessageHistory # Local import
            message_history = InMemoryChatMessageHistory()
        except Exception as e: # Catch other potential errors during RedisChatMessageHistory setup
            logger.error(f"Failed to setup RedisChatMessageHistory: {e}", exc_info=True)
            return f"Error: Could not setup Redis for memory. {str(e)}"


    system_prompt_content = DEFAULT_SYSTEM_PROMPT_FOR_AGENT # Default
    prompt_source_log = "default agent prompt"

    if prompt_content_override is not None:
        system_prompt_content = prompt_content_override
        prompt_source_log = "direct content override"
        logger.info(f"Using prompt content directly from override. Original length: {len(system_prompt_content)}")
    elif prompt_name:
        db_prompt_obj = crud.get_prompt_by_name(db, name=prompt_name)
        if db_prompt_obj:
            system_prompt_content = db_prompt_obj.content
            prompt_source_log = f"database (prompt name: '{prompt_name}')"
            logger.info(f"Using prompt '{prompt_name}' from database. Original length: {len(system_prompt_content)}")
        else:
            logger.warning(f"Prompt '{prompt_name}' not found. Falling back to default agent prompt. Original length: {len(system_prompt_content)}")
            # system_prompt_content remains DEFAULT_SYSTEM_PROMPT_FOR_AGENT
    else: # No override, no prompt_name, using default
        logger.info(f"Using default agent prompt. Original length: {len(system_prompt_content)}")
        # system_prompt_content remains DEFAULT_SYSTEM_PROMPT_FOR_AGENT

    # Process JavaScript in the system prompt content (whether from override, DB, or default)
    original_len = len(system_prompt_content)
    processed_system_prompt_content = process_prompt_javascript(system_prompt_content) # Use a new variable name

    if len(processed_system_prompt_content) != original_len:
        logger.info(f"System prompt content (from {prompt_source_log}) after JS processing. New length: {len(processed_system_prompt_content)}")
    elif "{{" in system_prompt_content and not PY_MINI_RACER_AVAILABLE:
        logger.info(f"Prompt (from {prompt_source_log}) contains JS snippets, but JS processing is disabled or unavailable.")
    else:
        logger.info(f"No JavaScript snippets processed in system prompt (from {prompt_source_log}), or no change in length.")

    system_prompt_content = processed_system_prompt_content # Assign back after logging original state



    # For OpenAI Functions agent, tools are passed directly, not described in prompt this way usually.
    # The agent creation process binds tools to the LLM.
    # The system prompt should guide the LLM's behavior and persona.

    agent_executor_instance = None # Define a common variable for the executor

    if is_openai_model and tools:
        logger.info(f"Creating OpenAI Functions Agent with {len(tools)} tools.")
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        agent = create_openai_functions_agent(llm, tools, prompt_template)
        agent_executor_instance = AgentExecutor(agent=agent, tools=tools, verbose=settings.DEBUG_MODE, handle_parsing_errors=True, return_intermediate_steps=False)
        logger.info("OpenAI Functions Agent with tools created successfully.")
    elif is_gemini_model and tools:
        logger.info(f"Creating Gemini Agent with {len(tools)} tools, using model {settings.GEMINI_MODEL_NAME}.")
        # Bind tools to the Gemini LLM
        llm_with_tools = llm.bind_tools(tools)

        # Define the prompt structure for Gemini with tools
        # This structure is similar to OpenAI's function agent prompt
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"), # For agent execution steps
        ])

        # Using OpenAIFunctionsAgentOutputParser as Gemini's tool_calls are similar.
        # If issues arise, explore other parsers like Langchain's XMLAgentOutputParser or a custom one for Gemini.
        # For now, assuming Gemini's output when tools are bound is compatible enough.
        # LangChain's documentation suggests that `llm.bind_tools(tools)` for Gemini
        # should produce `AIMessage(tool_calls=[...])` which is what OpenAIFunctionsAgentOutputParser expects.
        output_parser = OpenAIFunctionsAgentOutputParser()

        # Construct the agent runnable sequence
        # The agent_scratchpad is populated by formatting intermediate steps (tool calls and tool observations)
        # into a sequence of AIMessage and ToolMessage objects.
        # format_to_openai_function_messages is a common utility for this.
        agent_runnable = prompt_template | llm_with_tools | output_parser

        agent_executor_instance = AgentExecutor(
            agent=agent_runnable,
            tools=tools,
            verbose=settings.DEBUG_MODE,
            handle_parsing_errors=True, # Crucial for robustness
            return_intermediate_steps=False # Set to True if you need to inspect intermediate steps
        )
        logger.info(f"Gemini Agent with tools created successfully using {settings.GEMINI_MODEL_NAME}.")
    else: # Fallback for Gemini without tools, or OpenAI without tools, or any other model
        logger.info(f"Using basic ConversationChain (Model: {chosen_model_name}, Tools available: {len(tools)}, Tools used: No).")
        # Simpler prompt for basic ConversationChain
        conv_prompt_template_str = system_prompt_content
        if not ("{history}" in conv_prompt_template_str and "{input}" in conv_prompt_template_str):
            logger.warning("System prompt not suitable for ConversationChain (missing {history}/{input}). Using default.")
            conv_prompt_template_str = f"{system_prompt_content}\n\nCurrent conversation:\n{{history}}\nHuman: {{input}}\nAI:"

        from langchain.prompts import PromptTemplate # Local import for this specific use
        prompt_template = PromptTemplate(input_variables=["history", "input"], template=conv_prompt_template_str)

        memory_for_conv_chain = ConversationBufferMemory( # Separate memory instance if not using RunnableWithMessageHistory directly
            memory_key="history",
            chat_memory=message_history, # Use the same message_history store
            return_messages=True
        )
        # For ConversationChain, agent_executor_instance remains the chain itself
        agent_executor_instance = ConversationChain(llm=llm, memory=memory_for_conv_chain, prompt=prompt_template, verbose=settings.DEBUG_MODE)
        logger.info("Basic ConversationChain created.")

    # Setup RunnableWithMessageHistory for managing history with the chosen agent_executor_instance
    # Determine history_messages_key based on whether an AgentExecutor (with chat_history) or ConversationChain (with history) is used.
    # AgentExecutor (for OpenAI with tools, and Gemini with tools) uses "chat_history" in its prompt.
    # ConversationChain uses "history" in its prompt.
    current_history_key = "chat_history" if isinstance(agent_executor_instance, AgentExecutor) else "history"
    logger.info(f"RunnableWithMessageHistory will use history_messages_key='{current_history_key}'")

    chain_with_history = RunnableWithMessageHistory(
        agent_executor_instance,
        lambda session_id_for_history: message_history,
        input_messages_key="input",
        history_messages_key=current_history_key,
        output_messages_key="output" if isinstance(agent_executor_instance, AgentExecutor) else "response"
    )

    try:
        logger.info(f"Invoking chain_with_history for session {session_id} with input: '{text_input}'")
        result = await chain_with_history.ainvoke(
            {"input": text_input},
            config={"configurable": {"session_id": session_id}}
        )

        ai_response = result.get("output") if isinstance(agent_executor_instance, AgentExecutor) else result.get("response")
        if ai_response is None:
            logger.error(f"AI agent/chain returned None or missing expected output key. Result: {result}")
            ai_response = "Error: AI did not produce a valid response."

        logger.info(f"LLM/Agent final response for session {session_id}: '{str(ai_response)[:200]}...'")
        return str(ai_response) # Ensure it's a string
    except Exception as e:
        logger.error(f"Error during AI conversation for session {session_id}: {e}", exc_info=True)
        return f"Error: AI processing failed. Details: {str(e)}"

# Ensure settings have default values if not set via .env
if not hasattr(settings, 'OPENAI_MODEL_NAME'):
    settings.OPENAI_MODEL_NAME = "gpt-3.5-turbo-0125"
if not hasattr(settings, 'DEBUG_MODE'):
    settings.DEBUG_MODE = False

# Example standalone test function
async def main_test_ai_service():
    logging.basicConfig(level=logging.INFO if settings.DEBUG_MODE else logging.INFO) # Use DEBUG_MODE

    from app.core.database import SessionLocal, engine, Base as AppBase # Use AppBase alias
    # AppBase.metadata.create_all(bind=engine) # Tables should be created by main.py or migrations

    db = SessionLocal()
    try:
        tool_name = "get_current_time_api" # Unique name for test tool
        db_tool = crud.get_tool_by_name(db, name=tool_name)
        if not db_tool:
            from app import schemas as app_schemas # For ToolCreate
            tool_schema = app_schemas.ToolCreate(
                name=tool_name,
                description="Returns the current time from an external API.",
                parameters={},
                api_config={
                    "url": "https://worldtimeapi.org/api/ip",
                    "method": "GET"
                }
            )
            crud.create_tool(db, tool_schema)
            logger.info(f"Created dummy tool '{tool_name}' for testing.")

        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != 'your_openai_api_key_here':
            logger.info("--- Testing AI Service (OpenAI with Tools) ---")
            test_session_id = "test_openai_tool_session_standalone"
            # Clear previous history
            redis_message_history = RedisChatMessageHistory(session_id=f"ari_chat_history:{test_session_id}", url=f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0")
            if redis_message_history: redis_message_history.clear()

            response1 = await get_ai_response("Hello, I am Bob.", test_session_id, db, "openai", prompt_name=None)
            logger.info(f"OpenAI Response 1: {response1}")

            response2 = await get_ai_response("What is the current time?", test_session_id, db, "openai", prompt_name=None)
            logger.info(f"OpenAI Response 2 (tool use attempt): {response2}")

            response3 = await get_ai_response("What is my name?", test_session_id, db, "openai", prompt_name=None)
            logger.info(f"OpenAI Response 3 (memory test): {response3}")
        else:
            logger.warning("Skipping OpenAI tool test as API key is not set or is a placeholder.")

    finally:
        db.close()

if __name__ == '__main__':
    from pathlib import Path
    from dotenv import load_dotenv

    project_root = Path(__file__).resolve().parent.parent.parent
    dotenv_path = project_root / '.env'

    if dotenv_path.exists():
        logger.info(f"Loading .env file from {dotenv_path}")
        load_dotenv(dotenv_path=dotenv_path)
    else:
        logger.warning(f".env file not found at {dotenv_path}. Ensure API keys/settings are in environment.")

    # Re-initialize settings after dotenv load
    # This pattern helps if settings are instantiated globally at module import time
    settings.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", settings.OPENAI_API_KEY)
    settings.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", settings.GEMINI_API_KEY)
    settings.REDIS_HOST = os.getenv("REDIS_HOST", settings.REDIS_HOST)
    settings.REDIS_PORT = int(os.getenv("REDIS_PORT", str(settings.REDIS_PORT)))
    settings.DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    settings.OPENAI_MODEL_NAME = os.getenv("OPENAI_MODEL_NAME", "gpt-3.5-turbo-0125")
    settings.GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-pro") # Load Gemini model name
    settings.DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"

    # For standalone testing, ensure DB engine is configured with potentially loaded DATABASE_URL
    from app.core import database
    from app import models # To access models.Base for create_all
    if settings.DATABASE_URL != database.SQLALCHEMY_DATABASE_URL: # If .env changed it
        database.SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
        database.engine = database.create_engine(
            database.SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False} if database.SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
        )
        models.Base.metadata.bind = database.engine # Re-bind if engine changed
        logger.info(f"Re-configured database engine for standalone test with URL: {settings.DATABASE_URL}")

    # Ensure tables are created for the test database
    models.Base.metadata.create_all(bind=database.engine)


    asyncio.run(main_test_ai_service())
