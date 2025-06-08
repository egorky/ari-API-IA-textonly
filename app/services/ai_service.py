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


from app.core.config import settings
from app.services.redis_service import get_redis_client
from app.services.tool_executor import execute_api_tool
from app import crud # Assuming crud.py is in app directory, not app.crud if accessing directly
from sqlalchemy.orm import Session # For type hinting db session

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT_FOR_AGENT = "You are a helpful assistant. You have access to the following tools. Use them when appropriate."

def load_langchain_tools_from_db(db: Session) -> List[LangchainTool]:
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
    db: Session, # Added db session
    model_preference: str = None,
    prompt_name: Optional[str] = None # Name of the prompt to fetch from DB
):
    logger.info(f"AI Service call: session_id='{session_id}', model_preference='{model_preference}', prompt_name='{prompt_name}', input='{text_input[:50]}...'")

    chosen_model_name = model_preference if model_preference else settings.DEFAULT_AI_MODEL
    logger.info(f"Chosen AI model type: {chosen_model_name}")

    llm = None
    is_openai_model = False
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
            llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=settings.GEMINI_API_KEY, convert_system_message_to_human=True, temperature=0)
            logger.info("Using Google Gemini model.")
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


    system_prompt_content = DEFAULT_SYSTEM_PROMPT_FOR_AGENT
    if prompt_name:
        db_prompt_obj = crud.get_prompt_by_name(db, name=prompt_name)
        if db_prompt_obj:
            system_prompt_content = db_prompt_obj.content
            logger.info(f"Using prompt '{prompt_name}' from database.")
        else:
            logger.warning(f"Prompt '{prompt_name}' not found. Using default agent prompt.")

    # For OpenAI Functions agent, tools are passed directly, not described in prompt this way usually.
    # The agent creation process binds tools to the LLM.
    # The system prompt should guide the LLM's behavior and persona.
    if is_openai_model and tools:
        # OpenAI Functions Agent specific prompt structure
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessage(content=system_prompt_content),
            MessagesPlaceholder(variable_name="chat_history"),
            HumanMessage(content="{input}"), # Langchain uses {input} by default for user query
            MessagesPlaceholder(variable_name="agent_scratchpad"), # Crucial for agent execution steps
        ])
        agent = create_openai_functions_agent(llm, tools, prompt_template)
        agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=settings.DEBUG_MODE, handle_parsing_errors=True)
        logger.info("OpenAI Functions Agent with tools created.")
    else: # Fallback for Gemini or if no tools, or if OpenAI model but no tools
        logger.info(f"Using basic ConversationChain (Model: {chosen_model_name}, Tools: {len(tools)}).")
        # Simpler prompt for basic ConversationChain
        # This template needs 'history' and 'input'
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
        agent_executor = ConversationChain(llm=llm, memory=memory_for_conv_chain, prompt=prompt_template, verbose=settings.DEBUG_MODE)
        logger.info("Basic ConversationChain created.")

    # Setup RunnableWithMessageHistory for managing history with the chosen agent_executor
    chain_with_history = RunnableWithMessageHistory(
        agent_executor,
        # get_session_history factory function
        lambda session_id_for_history: message_history, # Return the single message_history instance
        input_messages_key="input",
        history_messages_key="chat_history", # Ensure this matches placeholder in agent prompt if used
        # Output key for AgentExecutor is 'output', for ConversationChain it's 'response'
        output_messages_key="output" if isinstance(agent_executor, AgentExecutor) else "response"
    )

    try:
        logger.info(f"Invoking chain_with_history for session {session_id} with input: '{text_input}'")
        result = await chain_with_history.ainvoke(
            {"input": text_input}, # Input for the agent/chain
            config={"configurable": {"session_id": session_id}} # Config for RunnableWithMessageHistory
        )

        ai_response = result.get("output") if isinstance(agent_executor, AgentExecutor) else result.get("response")
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
