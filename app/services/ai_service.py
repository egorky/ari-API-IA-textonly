import logging
import os
from app.core.config import settings
from app.services.redis_service import get_redis_client

# Updated import for RedisChatMessageHistory as per deprecation warning
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain.memory import ConversationBufferMemory # This one seems to be okay in langchain.memory for now
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import ConversationChain
from langchain.prompts import MessagesPlaceholder, PromptTemplate
from langchain.schema import HumanMessage, AIMessage, SystemMessage


logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT_TEMPLATE = """
You are a helpful AI assistant. Your goal is to assist the user with their questions.
Keep your responses concise and helpful.
Current conversation:
{history}
Human: {input}
AI:"""

def get_ai_response(text_input: str, session_id: str, model_preference: str = None, initial_prompt_str: str = None):
    logger.info(f"AI Service call: session_id='{session_id}', model_preference='{model_preference}', input='{text_input[:50]}...'")

    chosen_model_name = model_preference if model_preference else settings.DEFAULT_AI_MODEL
    logger.info(f"Chosen AI model type: {chosen_model_name}")

    llm = None
    if chosen_model_name.lower() == 'openai':
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == 'your_openai_api_key_here':
            logger.error("OpenAI API key is not configured.")
            return "Error: OpenAI API key not configured."
        try:
            llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY, model_name="gpt-3.5-turbo")
            logger.info("Using OpenAI model.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI LLM: {e}")
            return f"Error: Could not initialize OpenAI model. {e}"
    elif chosen_model_name.lower() == 'gemini':
        if not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == 'your_gemini_api_key_here':
            logger.error("Gemini API key is not configured.")
            return "Error: Gemini API key not configured."
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=settings.GEMINI_API_KEY, convert_system_message_to_human=True)
            logger.info("Using Google Gemini model.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini LLM: {e}")
            return f"Error: Could not initialize Gemini model. {e}"
    else:
        logger.error(f"Unsupported AI model type: {chosen_model_name}")
        return f"Error: Unsupported AI model type '{chosen_model_name}'. Please choose 'openai' or 'gemini'."

    if llm is None:
        return "Error: LLM could not be initialized due to unsupported model type or API key issue."

    redis_client = get_redis_client()
    if not redis_client:
        logger.error("Redis client is not available. Cannot use conversation memory.")
        return "Error: Redis client not available, conversation memory cannot be established."

    try:
        redis_auth_part = f":{settings.REDIS_PASSWORD}@" if settings.REDIS_PASSWORD else ""
        redis_url = f"redis://{redis_auth_part}{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
        if not settings.REDIS_PASSWORD: # Log URL without password if it's not set
            logger.info(f"Using Redis URL for ChatMessageHistory: redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0")
        else:
            logger.info(f"Using Redis URL for ChatMessageHistory: redis://<REDACTED_PASSWORD>@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0")


        message_history = RedisChatMessageHistory(
            session_id=f"ari_chat_history:{session_id}",
            url=redis_url
        )
        logger.info(f"RedisChatMessageHistory setup for session_id: ari_chat_history:{session_id}")
    except Exception as e:
        logger.error(f"Failed to setup RedisChatMessageHistory: {e}", exc_info=True) # Added exc_info
        return f"Error: Could not setup Redis for memory. {e}"

    effective_prompt_template_str = initial_prompt_str if initial_prompt_str else DEFAULT_SYSTEM_PROMPT_TEMPLATE

    if not ("{history}" in effective_prompt_template_str and "{input}" in effective_prompt_template_str):
        logger.warning("Prompt template does not contain {history} and {input}. Using the default template.")
        effective_prompt_template_str = DEFAULT_SYSTEM_PROMPT_TEMPLATE

    PROMPT = PromptTemplate(
        input_variables=["history", "input"], template=effective_prompt_template_str
    )

    memory = ConversationBufferMemory(
        memory_key="history",
        chat_memory=message_history,
        return_messages=True
    )
    logger.info("ConversationBufferMemory setup with Redis history.")

    conversation = ConversationChain(llm=llm, memory=memory, prompt=PROMPT, verbose=settings.DEBUG_MODE if hasattr(settings, 'DEBUG_MODE') else False)
    logger.info("ConversationChain initialized.")

    try:
        logger.info(f"Sending input to LLM: '{text_input}'")
        response = conversation.predict(input=text_input)
        logger.info(f"LLM raw response for session {session_id}: '{response[:100]}...'")
        return response
    except Exception as e:
        logger.error(f"Error during AI conversation for session {session_id}: {e}", exc_info=True)
        return f"Error: AI processing failed. {e}"

if __name__ == '__main__':
    import redis # For standalone Redis connection test
    logging.basicConfig(level=logging.INFO)

    # Mock settings for standalone test
    class MockSettings:
        OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')
        GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'your_gemini_api_key_here')
        REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
        REDIS_PORT = int(os.getenv('REDIS_PORT', "6379"))
        REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None) # Handles empty string as None
        DEFAULT_AI_MODEL = os.getenv('DEFAULT_AI_MODEL', 'openai')
        DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

    original_settings_ai = settings
    settings = MockSettings()

    test_redis_available = False
    logger.info(f"--- Testing Redis Connection for AI Service (Host: {settings.REDIS_HOST}, Port: {settings.REDIS_PORT}) ---")
    try:
        # Use the get_redis_client which now uses the mocked settings
        r_test_client = get_redis_client()
        if r_test_client:
            r_test_client.ping() #This ping uses the client from get_redis_client
            logger.info("Redis connection successful for standalone AI service test.")
            test_redis_available = True
        else:
            logger.warning("Redis client not available for standalone AI service test (get_redis_client returned None).")
    except redis.exceptions.ConnectionError as e:
        logger.warning(f"Redis connection failed for standalone AI service test: {e}. AI tests needing memory will be skipped or fail.")
    except Exception as e: # Catch any other exception from get_redis_client
        logger.error(f"Unexpected error getting Redis client for AI service test: {e}", exc_info=True)


    if test_redis_available:
        logger.info("--- Testing AI Service (OpenAI) ---")
        if settings.OPENAI_API_KEY != 'your_openai_api_key_here':
            response_openai = get_ai_response("Hello, who are you?", "test_session_openai_standalone", "openai")
            logger.info(f"OpenAI Response: {response_openai}")
            response_openai_2 = get_ai_response("What was my first question?", "test_session_openai_standalone", "openai")
            logger.info(f"OpenAI Response 2 (memory test): {response_openai_2}")
        else:
            logger.warning("Skipping OpenAI test as API key is 'your_openai_api_key_here'. Set OPENAI_API_KEY env var to test.")

        logger.info("--- Testing AI Service (Gemini) ---")
        if settings.GEMINI_API_KEY != 'your_gemini_api_key_here':
            response_gemini = get_ai_response("Hi there, what can you do?", "test_session_gemini_standalone", "gemini")
            logger.info(f"Gemini Response: {response_gemini}")
            response_gemini_2 = get_ai_response("My favorite color is blue.", "test_session_gemini_standalone", "gemini")
            logger.info(f"Gemini Response 2 (memory test A): {response_gemini_2}")
            response_gemini_3 = get_ai_response("What is my favorite color?", "test_session_gemini_standalone", "gemini")
            logger.info(f"Gemini Response 3 (memory test B): {response_gemini_3}")
        else:
            logger.warning("Skipping Gemini test as API key is 'your_gemini_api_key_here'. Set GEMINI_API_KEY env var to test.")
    else:
        logger.warning("Skipping AI service tests that require memory due to Redis unavailability.")

    settings = original_settings_ai # Restore original settings
