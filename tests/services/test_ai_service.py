import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session
from langchain_core.tools import Tool as LangchainTool
import sys
from pathlib import Path

# Ensure app is discoverable for imports
APP_DIR = Path(__file__).resolve().parent.parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from services import ai_service # app.services.ai_service
from app import crud, schemas # app.crud, app.schemas
from app.core.config import settings
from app.models import Tool as ModelTool, Prompt as ModelPrompt # For creating mock DB objects

@pytest.fixture
def mock_db_session():
    return MagicMock(spec=Session)

@pytest.fixture
def mock_redis_client():
    client = MagicMock()
    client.ping.return_value = True
    return client

@pytest.fixture(autouse=True)
def mock_dependencies(monkeypatch, mock_redis_client):
    monkeypatch.setattr(ai_service, 'get_redis_client', MagicMock(return_value=mock_redis_client))
    monkeypatch.setattr(ai_service.crud, 'get_tools', MagicMock(return_value=[]))
    monkeypatch.setattr(ai_service.crud, 'get_prompt_by_name', MagicMock(return_value=None))
    monkeypatch.setattr(ai_service.tool_executor, 'execute_api_tool', AsyncMock(return_value='{"tool_result": "success"}'))

@pytest.fixture
def mock_chat_openai():
    with patch('app.services.ai_service.ChatOpenAI') as MockChatOpenAI:
        mock_llm_instance = MockChatOpenAI.return_value
        # Mock the response from RunnableWithMessageHistory.ainvoke
        # This is complex because ainvoke is called on chain_with_history, not llm directly
        yield MockChatOpenAI

@pytest.fixture
def mock_chat_gemini():
    with patch('app.services.ai_service.ChatGoogleGenerativeAI') as MockChatGoogle:
        mock_llm_instance = MockChatGoogle.return_value
        yield MockChatGoogle

@pytest.fixture
def mock_agent_executor_and_runnable():
    with patch('app.services.ai_service.AgentExecutor') as MockAgentExecutor, \
         patch('app.services.ai_service.RunnableWithMessageHistory') as MockRunnableWithMessageHistory:

        mock_agent_instance = MockAgentExecutor.return_value
        mock_runnable_instance = MockRunnableWithMessageHistory.return_value
        mock_runnable_instance.ainvoke = AsyncMock(return_value={"output": "Agent says hello with tools"})

        yield MockAgentExecutor, MockRunnableWithMessageHistory


@pytest.fixture
def mock_conversation_chain_and_runnable():
     with patch('app.services.ai_service.ConversationChain') as MockConversationChain, \
          patch('app.services.ai_service.RunnableWithMessageHistory') as MockRunnableWithMessageHistory:
        mock_chain_instance = MockConversationChain.return_value
        mock_runnable_instance = MockRunnableWithMessageHistory.return_value
        mock_runnable_instance.ainvoke = AsyncMock(return_value={"response": "Chain says hello via ainvoke"})
        yield MockConversationChain, MockRunnableWithMessageHistory


@pytest.mark.asyncio
async def test_get_ai_response_openai_no_tools_no_prompt(mock_db_session, mock_chat_openai, mock_conversation_chain_and_runnable):
    _, MockRunnable = mock_conversation_chain_and_runnable
    settings.OPENAI_API_KEY = "fake_key_openai" # Ensure it's not the placeholder
    settings.DEFAULT_AI_MODEL = "openai"

    response = await ai_service.get_ai_response(
        text_input="Hello", session_id="test_session_1", db=mock_db_session
    )

    mock_chat_openai.assert_called_once()
    MockRunnable.assert_called()
    assert response == "Chain says hello via ainvoke"


@pytest.mark.asyncio
async def test_get_ai_response_gemini_no_tools_no_prompt(mock_db_session, mock_chat_gemini, mock_conversation_chain_and_runnable):
    _, MockRunnable = mock_conversation_chain_and_runnable
    settings.GEMINI_API_KEY = "fake_key_gemini" # Ensure it's not the placeholder
    settings.DEFAULT_AI_MODEL = "gemini"

    response = await ai_service.get_ai_response(
        text_input="Hello Gemini", session_id="test_session_gemini_1", db=mock_db_session, model_preference="gemini"
    )
    mock_chat_gemini.assert_called_once()
    MockRunnable.assert_called()
    assert response == "Chain says hello via ainvoke"

@pytest.mark.asyncio
async def test_get_ai_response_openai_with_tools(mock_db_session, mock_chat_openai, mock_agent_executor_and_runnable):
    MockAgentExecutor, MockRunnable = mock_agent_executor_and_runnable
    settings.OPENAI_API_KEY = "fake_key_openai_tools"
    settings.DEFAULT_AI_MODEL = "openai"

    sample_tool_db = ModelTool( # Use the actual SQLAlchemy model for creating test data
        id=1, name="get_weather", description="Get weather for a location",
        parameters={"location": "string"},
        api_config={"url": "http://example.com/weather", "method": "GET"}
    )
    ai_service.crud.get_tools = MagicMock(return_value=[sample_tool_db])

    response = await ai_service.get_ai_response(
        text_input="What's the weather in London?", session_id="test_session_openai_tools",
        db=mock_db_session, model_preference="openai"
    )

    mock_chat_openai.assert_called_once()
    ai_service.crud.get_tools.assert_called_once_with(db=mock_db_session, limit=100)
    MockAgentExecutor.assert_called()
    MockRunnable.assert_called()
    assert response == "Agent says hello with tools"


@pytest.mark.asyncio
async def test_get_ai_response_uses_custom_prompt(mock_db_session, mock_chat_openai, mock_conversation_chain_and_runnable):
    MockConversationChain, MockRunnable = mock_conversation_chain_and_runnable
    settings.OPENAI_API_KEY = "fake_key_custom_prompt"
    settings.DEFAULT_AI_MODEL = "openai"

    custom_prompt_content = "You are a pirate assistant. User: {input} AI:" # Simplified for test
    mock_prompt_db = ModelPrompt(id=1, name="pirate_prompt", content=custom_prompt_content, metadata={})
    ai_service.crud.get_prompt_by_name = MagicMock(return_value=mock_prompt_db)

    response = await ai_service.get_ai_response(
        text_input="Hello", session_id="test_session_custom_prompt",
        db=mock_db_session, prompt_name="pirate_prompt"
    )

    MockRunnable.assert_called_once()
    # Check that the prompt was fetched
    ai_service.crud.get_prompt_by_name.assert_called_with(mock_db_session, name="pirate_prompt")
    # Check if the ConversationChain (or its underlying PromptTemplate) received the custom prompt
    # This is a bit indirect, as ConversationChain is mocked.
    # We'd ideally check the 'prompt' arg to ConversationChain or the system message to the agent.
    # For now, the response check serves as an indirect indicator if LLM mock was more detailed.
    assert response == "Chain says hello via ainvoke"


def test_load_langchain_tools_from_db_empty(mock_db_session):
    ai_service.crud.get_tools = MagicMock(return_value=[])
    tools = ai_service.load_langchain_tools_from_db(mock_db_session)
    assert len(tools) == 0

def test_load_langchain_tools_from_db_with_data(mock_db_session):
    db_tool1 = ModelTool(id=1, name="tool1", description="desc1", api_config={"url": "url1"}, parameters={"type": "object", "properties": {"q": {"type": "string"}}})
    db_tool2 = ModelTool(id=2, name="tool2", description="desc2", api_config={"url": "url2"}, parameters=None) # No parameters
    ai_service.crud.get_tools = MagicMock(return_value=[db_tool1, db_tool2])

    tools = ai_service.load_langchain_tools_from_db(mock_db_session)
    assert len(tools) == 2
    assert isinstance(tools[0], LangchainTool)
    assert tools[0].name == "tool1"
    assert "desc1" in tools[0].description
    # The description format for OpenAI functions agent should not include the schema directly.
    # assert "Call this tool with arguments as a JSON object matching this schema" in tools[0].description
    assert tools[1].name == "tool2"
    assert "desc2" in tools[1].description


@pytest.mark.asyncio
async def test_get_ai_response_no_openai_key(mock_db_session):
    # Save original and set to empty
    original_key = settings.OPENAI_API_KEY
    settings.OPENAI_API_KEY = ""
    settings.DEFAULT_AI_MODEL = "openai"
    response = await ai_service.get_ai_response("test", "s1", mock_db_session)
    assert "Error: OpenAI API key not configured" in response
    settings.OPENAI_API_KEY = original_key # Restore

@pytest.mark.asyncio
async def test_get_ai_response_no_gemini_key(mock_db_session):
    original_key = settings.GEMINI_API_KEY
    settings.GEMINI_API_KEY = ""
    settings.DEFAULT_AI_MODEL = "gemini"
    response = await ai_service.get_ai_response("test", "s2", mock_db_session, model_preference="gemini")
    assert "Error: Gemini API key not configured" in response
    settings.GEMINI_API_KEY = original_key

@pytest.mark.asyncio
async def test_get_ai_response_unsupported_model(mock_db_session):
    original_model = settings.DEFAULT_AI_MODEL
    settings.DEFAULT_AI_MODEL = "unknown_model"
    response = await ai_service.get_ai_response("test", "s3", mock_db_session)
    assert "Error: Unsupported AI model type 'unknown_model'" in response
    settings.DEFAULT_AI_MODEL = original_model

@pytest.mark.asyncio
async def test_get_ai_response_redis_client_none(mock_db_session, monkeypatch, mock_chat_openai, mock_conversation_chain_and_runnable):
    _, MockRunnable = mock_conversation_chain_and_runnable
    settings.OPENAI_API_KEY = "fake_key_redis_none"
    settings.DEFAULT_AI_MODEL = "openai"

    monkeypatch.setattr(ai_service, 'get_redis_client', MagicMock(return_value=None))

    # Expect fallback to InMemoryChatMessageHistory, so it should still produce a response
    response = await ai_service.get_ai_response("Hello", "test_session_redis_fail", db=mock_db_session)
    assert response == "Chain says hello via ainvoke"
    # Check logs for warning about Redis (cannot do directly in test, but ensure code path is hit)

@pytest.mark.asyncio
async def test_get_ai_response_redis_history_connection_error(mock_db_session, mock_chat_openai, mock_redis_client, monkeypatch, mock_conversation_chain_and_runnable):
    _, MockRunnable = mock_conversation_chain_and_runnable
    settings.OPENAI_API_KEY = "fake_key_redis_conn_err"
    settings.DEFAULT_AI_MODEL = "openai"

    # Make get_redis_client return a mock, but make RedisChatMessageHistory instantiation fail
    # This scenario is tricky as RedisChatMessageHistory itself tries to connect.
    # Better to mock RedisChatMessageHistory to raise ConnectionError.
    with patch('app.services.ai_service.RedisChatMessageHistory', side_effect=redis.exceptions.ConnectionError("Redis history init failed")):
        response = await ai_service.get_ai_response("Hello", "test_session_redis_history_fail", db=mock_db_session)
        # Expect fallback to InMemoryChatMessageHistory
        assert response == "Chain says hello via ainvoke"
