# Asterisk AI Integration Framework

This project provides a framework for integrating Asterisk with Large Language Models (LLMs) like OpenAI's GPT and Google's Gemini. It features an Asterisk REST Interface (ARI) client to handle calls, a LangChain-based AI service for processing user input and interacting with external tools/APIs, and a FastAPI web interface for managing AI prompts and tool configurations.

## Features

*   **Asterisk ARI Integration**: Connects to Asterisk to receive call events and control call flow.
*   **Multi-LLM Support with Tools**: Supports OpenAI and Google Gemini models, both capable of utilizing dynamically defined tools/APIs.
*   **Dynamic Tool/API Calling**: Define external APIs (tools) through a web interface. The AI can learn to use these tools, with input parameters validated against a defined JSON schema.
*   **Dynamic Prompts with JavaScript**: Embed JavaScript snippets (`{{ your_code }}`) directly within prompts for dynamic content generation (e.g., current date/time) executed on the backend before sending to the LLM.
*   **Conversation Memory**: Utilizes Redis to maintain conversation history per call (session).
*   **Web-based Management UI**:
    *   Secure login (HTTP Basic Auth).
    *   CRUD operations for AI Prompts.
    *   CRUD operations for Tool/API definitions.
    *   **Prompt Testing Page**: Interactively test prompts with different models, inputs, and session IDs.
    *   View system status (ARI, Redis, JavaScript Engine connection) and key configurations.
*   **Configurable**: Uses a `.env` file for easy configuration of API keys, service URLs, etc.
*   **Asynchronous**: Built with FastAPI and `asyncio` for efficient I/O operations.

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── api/                  # FastAPI routers
│   │   ├── __init__.py
│   │   ├── ari_handler.py    # Handles ARI events
│   │   ├── prompts_router.py # Web UI and API for Prompts
│   │   ├── tools_router.py   # Web UI and API for Tools
│   │   └── testing_router.py # API for prompt testing UI
│   ├── core/                 # Core components (config, database, security)
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/               # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── prompt.py
│   │   └── tool.py
│   ├── schemas.py            # Pydantic schemas
│   ├── services/             # Business logic
│   │   ├── __init__.py
│   │   ├── ai_service.py     # LangChain integration, agent logic
│   │   ├── redis_service.py  # Redis connection utility
│   │   └── tool_executor.py  # Executes API calls for tools
│   ├── static/               # Static files (CSS, JS)
│   │   └── css/
│   │       └── style.css
│   ├── templates/            # Jinja2 HTML templates
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── prompts/
│   │   │   ├── create_or_edit.html
│   │   │   └── list.html
│   │   ├── tools/
│   │   │   ├── create_or_edit.html
│   │   │   └── list.html
│   │   └── testing/
│   │       └── test_prompt.html
│   ├── main.py               # FastAPI application entry point
│   └── vendor/               # Vendored libraries (ari-py, swaggerpy)
│       ├── __init__.py
│       ├── ari_py/
│       └── swaggerpy/
├── .env.example            # Example environment file
├── .env                    # Local environment configuration
├── .gitignore
├── pyproject.toml
├── poetry.lock
└── README.md
```

## Prerequisites

*   Python 3.9+
*   Poetry (for dependency management)
*   Redis server (for conversation memory)
*   Asterisk server (with ARI enabled and configured)
*   API keys for OpenAI and/or Google Gemini (if you plan to use them)

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    poetry install
    ```

3.  **Configure Environment Variables:**
    Copy the example environment file (or create `.env` directly) and customize it:
    ```bash
    cp .env.example .env
    ```
    Edit `.env` with your specific configurations:
    *   `OPENAI_API_KEY`: Your OpenAI API key.
    *   `GEMINI_API_KEY`: Your Google API key for Gemini.
    *   `DEFAULT_AI_MODEL`: `openai` or `gemini`.
    *   `OPENAI_MODEL_NAME`: Specific OpenAI model to use (e.g., `gpt-3.5-turbo-0125`).
    *   `GEMINI_MODEL_NAME`: Specific Gemini model to use (e.g., `gemini-pro`, `gemini-1.5-pro-latest`).
    *   `REDIS_HOST`: Redis server hostname (default: `localhost`).
    *   `REDIS_PORT`: Redis server port (default: `6379`).
    *   `REDIS_PASSWORD`: Redis server password (leave empty if none).
    *   `DATABASE_URL`: SQLAlchemy database URL (default: `sqlite:///./test.db`).
    *   `WEB_UI_USERNAME`: Username for web interface login.
    *   `WEB_UI_PASSWORD`: Password for web interface login.
    *   `SECRET_KEY`: A secret key for session management or other security features (generate a random string like `openssl rand -hex 32`).
    *   `ASTERISK_ARI_URL`: Full base URL to your Asterisk ARI (e.g., `http://localhost:8088`). The application will append paths like `/ari/api-docs/resources.json` or `/ari/events`.
    *   `ASTERISK_ARI_USERNAME`: Username for ARI connection.
    *   `ASTERISK_ARI_PASSWORD`: Password for ARI connection.
    *   `ASTERISK_APP_NAME`: The name of your Stasis application in Asterisk.
    *   `DEBUG_MODE`: Set to `True` for verbose logging from LangChain agents (default: `False`).


## Running the Application

1.  **Ensure Redis is running.**
2.  **Ensure Asterisk is running and configured for ARI.** You'll need to configure a Stasis application in `stasis.conf` or `extensions.conf` that points to the `ASTERISK_APP_NAME` you set in your `.env` file.

    Example `extensions.conf` snippet:
    ```
    exten => _X.,1,NoOp(Incoming call for AI IVR)
    same => n,Stasis(ai_ari_app,your_custom_arg1=value1,UNIQUEID=${UNIQUEID},USER_INPUT=${YOUR_DIALPLAN_VARIABLE},AI_PROMPT_NAME=your_prompt_name_from_db)
    same => n,Hangup()
    ```
    Make sure to pass necessary variables like `USER_INPUT`, `UNIQUEID`, and optionally `AI_PROMPT_NAME` or `AI_MODEL` to the Stasis application.

3.  **Start the FastAPI application:**
    ```bash
    poetry run python app/main.py
    ```
    Or using Uvicorn directly for development with auto-reload:
    ```bash
    poetry run uvicorn app.main:app --reload
    ```
    The application will typically be available at `http://localhost:8000`.

## Accessing the System

*   **Web Interface**: Navigate to `http://localhost:8000/ui` in your web browser. You will be prompted for the username and password configured in your `.env` file. The main page provides a dashboard with system status.
*   **API Documentation (Swagger UI)**: Available at `http://localhost:8000/docs`.
*   **Alternative API Documentation (ReDoc)**: Available at `http://localhost:8000/redoc`.

## Using the Web Interface

The web interface allows you to:

*   **Manage Prompts**:
    *   Create new prompts with a name, content (the actual prompt text for the LLM), and optional JSON metadata.
    *   View, edit, and delete existing prompts.
*   **Manage Tools/APIs**:
    *   Define new tools that the AI can use.
    *   Specify the tool's name, description (for the LLM to understand its purpose), parameters (as a JSON schema defining expected inputs), and API configuration (URL, HTTP method, headers).
    *   View, edit, and delete existing tools.
*   **Test Prompts**:
    *   Access a dedicated page (`/ui/test-prompt`) to test prompts.
    *   Load existing prompts or write custom prompt content.
    *   Provide user input and select an AI model (OpenAI/Gemini).
    *   Optionally specify a session ID for testing conversation continuity.
    *   View the AI's response directly in the UI. This is useful for designing, debugging, and refining prompts.

## How it Works

1.  An incoming call to Asterisk is routed to the Stasis application named in `ASTERISK_APP_NAME`.
2.  The `ari_handler.py` receives the `StasisStart` event, along with any variables passed from the dialplan.
3.  It extracts relevant information like `USER_INPUT`, `UNIQUEID`, and desired `AI_MODEL` or `AI_PROMPT_NAME`.
4.  It calls the `ai_service.get_ai_response` function, passing a database session.
5.  The `ai_service` initializes the chosen LLM (OpenAI or Gemini) and sets up conversation memory using Redis (keyed by `UNIQUEID`).
6.  It loads available tools (API definitions) from the database via `crud.get_tools`.
7.  It loads the specified (or default) prompt from the database via `crud.get_prompt_by_name`, or uses prompt content directly provided (e.g., from the Prompt Testing UI).
8.  **Prompt Processing**: The retrieved prompt content undergoes JavaScript processing. Any `{{ snippet }}` found is executed by `py_mini_racer` on the backend, and the snippet is replaced with its result.
9.  A LangChain agent is created with the LLM, tools, and the processed prompt. (For OpenAI, `create_openai_functions_agent`; for Gemini, a similar agent structure is used if tools are present, via `llm.bind_tools()` and `AgentExecutor`).
10. The user's input is passed to the agent.
11. The agent processes the input. If it decides to use a tool:
    *   It determines the tool and arguments.
    *   The `tool_executor.execute_api_tool` function is called.
    *   **Input Validation**: Before execution, `tool_executor` validates the LLM-provided arguments against the tool's defined JSON schema. If validation fails, an error is returned to the agent.
    *   `execute_api_tool` makes the configured HTTP request to the external API and returns the result.
12. The tool's output (or validation error) is fed back to the agent, which then formulates a final response.
13. The `ai_service` returns this final response to `ari_handler`.
13. `ari_handler` sets the response as a channel variable (e.g., `AI_RESPONSE`) and the call continues in the Asterisk dialplan, where this variable can be used (e.g., for Text-to-Speech).

## Development

*   **Database Migrations**: Currently, `models.Base.metadata.create_all(bind=engine)` is used in `main.py` to create tables. For production or more complex schema changes, consider using Alembic for database migrations.
*   **JavaScript Snippets in Prompts (Dynamic Prompts)**:
    *   **Syntax**: JavaScript code can be embedded directly within the prompt content using double curly braces: `{{ your_javascript_code }}`.
    *   **Backend Execution**: These snippets are executed on the server-side by the `py_mini_racer` library (which uses the V8 JavaScript engine) *before* the prompt is sent to the LLM.
    *   **Capabilities**: Standard JavaScript functionalities available in V8 can be used. This allows for dynamic generation of content within prompts, such as including the current date/time, simple calculations, or formatting. Example: `Today's date is {{ new Date().toLocaleDateString() }}.`
    *   **Security**: `py_mini_racer` executes the JavaScript in a sandboxed environment. However, complex or potentially malicious JS code should be avoided, especially if prompt content can be influenced by external, untrusted sources. Execution timeouts or resource limits are not currently implemented by this application layer but might be available in `py_mini_racer` itself or could be added for enhanced security.
    *   **Error Handling**: If a JavaScript snippet fails to execute, an error is logged, and the original snippet (`{{ ... }}`) is left unprocessed in the prompt content. The rest of the prompt processing and AI call will proceed.
*   **Error Handling**: Basic error handling is in place, but can be further enhanced for production readiness.

## Further Enhancements

*   Add unit and integration tests.
*   Implement more sophisticated logging and monitoring.
*   Enhance user roles and permissions for the Web UI.
*   Add support for more LLM providers or models.
*   Refine the tool execution mechanism (e.g., support for OAuth, more complex parameter mapping, different request/response content types).
*   Improve error handling and user feedback in the Web UI's JavaScript.
```
