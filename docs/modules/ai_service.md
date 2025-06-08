# Módulo: app.services.ai_service

**Archivo Original:** `app/services/ai_service.py`

## Propósito General

Este módulo es el núcleo de la lógica de inteligencia artificial de la aplicación. Actúa como un orquestador que integra varios componentes para procesar la entrada del usuario y generar una respuesta coherente y contextual, utilizando modelos de lenguaje grandes (LLMs) y herramientas externas.

Sus responsabilidades principales son:

*   **Selección Dinámica de Modelos LLM:**
    *   Determina qué modelo de IA utilizar (OpenAI GPT o Google Gemini) basado en la variable `model_preference` (que puede provenir del dialplan de Asterisk) o, en su defecto, de la configuración `settings.DEFAULT_AI_MODEL`.
    *   Utiliza los nombres de modelo específicos (`settings.OPENAI_MODEL_NAME`, `settings.GEMINI_MODEL_NAME`) de la configuración.
*   **Inicialización de LLMs de LangChain:**
    *   Crea una instancia del cliente LLM apropiado (`ChatOpenAI` o `ChatGoogleGenerativeAI`) con la configuración de API key y nombre de modelo correspondientes.
*   **Carga de Herramientas (Tools):**
    *   Llama a `crud.get_tools` para obtener las definiciones de herramientas (APIs externas) desde la base de datos.
    *   Transforma estas definiciones en objetos `LangchainTool` que el agente de LangChain puede utilizar. Cada `LangchainTool` está configurado con un `coro` (una corutina asíncrona) que llama a `tool_executor.execute_api_tool` cuando la herramienta es invocada por el agente.
*   **Gestión de Memoria de Conversación:**
    *   Intenta conectarse a Redis utilizando `redis_service.get_redis_client()`.
    *   Si Redis está disponible, instancia `RedisChatMessageHistory` utilizando un `session_id` único (derivado del `UNIQUEID` de la llamada de Asterisk) para almacenar y recuperar el historial de la conversación.
    *   Si Redis no está disponible, recurre a `InMemoryChatMessageHistory` como fallback (el historial será efímero para esa llamada).
    *   Integra el historial de mensajes con el agente/cadena usando `RunnableWithMessageHistory` de LangChain, permitiendo conversaciones con estado.
*   **Procesamiento de Prompts:**
    *   Determina el contenido del prompt del sistema:
        *   Da prioridad a `prompt_content_override` si se proporciona (usado por la UI de prueba de prompts).
        *   Si no hay override, intenta cargar un prompt desde la base de datos usando `prompt_name` (pasado desde el dialplan).
        *   Si no se especifica `prompt_name` o no se encuentra, utiliza un `DEFAULT_SYSTEM_PROMPT_FOR_AGENT`.
    *   Llama a `process_prompt_javascript(system_prompt_content)` para identificar y ejecutar cualquier snippet de JavaScript (`{{ ... }}`) embebido en el contenido del prompt. Esto se hace utilizando la biblioteca `py_mini_racer` si está disponible. El resultado del JS ejecutado reemplaza el snippet en el prompt.
*   **Construcción y Ejecución de Agentes LangChain:**
    *   **Para OpenAI con herramientas:** Crea un agente utilizando `create_openai_functions_agent` y lo envuelve en un `AgentExecutor`. Este agente está diseñado para trabajar con el modelo de "function calling" de OpenAI.
    *   **Para Gemini con herramientas:** Si hay herramientas disponibles, vincula las herramientas al modelo Gemini (`llm.bind_tools(tools)`). Luego, construye un agente runnable (similar en estructura al de OpenAI, usando `OpenAIFunctionsAgentOutputParser` inicialmente) y lo envuelve en un `AgentExecutor`.
    *   **Sin herramientas (o para modelos no configurados para herramientas):** Recurre a una `ConversationChain` más simple para mantener una conversación básica con memoria.
    *   El `AgentExecutor` (o `ConversationChain`) maneja la interacción con el LLM, la invocación de herramientas (si aplica), y el flujo general de la conversación.
*   **Retorno de Respuesta:**
    *   La respuesta final generada por el agente (o cadena) se devuelve como una cadena de texto.

## Dependencias Clave

*   **LangChain:**
    *   `langchain_openai.ChatOpenAI`: Cliente para modelos OpenAI.
    *   `langchain_google_genai.ChatGoogleGenerativeAI`: Cliente para modelos Gemini.
    *   `langchain_core.prompts.ChatPromptTemplate`, `MessagesPlaceholder`: Para definir las plantillas de prompt.
    *   `langchain_core.tools.Tool`: Para la representación de herramientas.
    *   `langchain.memory.ConversationBufferMemory`: Para la cadena de conversación básica.
    *   `langchain_community.chat_message_histories.RedisChatMessageHistory`: Para el historial de chat en Redis.
    *   `langchain.agents.AgentExecutor`, `create_openai_functions_agent`, `OpenAIFunctionsAgentOutputParser`: Componentes para construir y ejecutar agentes con herramientas.
    *   `langchain_core.runnables.history.RunnableWithMessageHistory`: Para gestionar el historial de mensajes con cadenas y agentes.
*   **Configuración y Servicios Propios:**
    *   `app.core.config.settings`: Para acceder a la configuración de la aplicación (API keys, nombres de modelo, etc.).
    *   `app.services.redis_service.get_redis_client`: Para obtener el cliente Redis.
    *   `app.services.tool_executor.execute_api_tool`: Para ejecutar las llamadas a las herramientas/APIs.
    *   `app.crud`: Para interactuar con la base de datos (cargar prompts y herramientas).
*   **Base de Datos:**
    *   `sqlalchemy.orm.Session`: Para el tipado de la sesión de base de datos.
*   **Procesamiento de JavaScript en Prompts:**
    *   `py_mini_racer.MiniRacer` (opcional, importación intentada): Para ejecutar snippets de JavaScript.
    *   `re`: Para encontrar los snippets de JavaScript en el texto del prompt.
*   **Otros:**
    *   `logging`: Para el registro de eventos y errores.
    *   `json`: Para el manejo de datos en formato JSON.
    *   `os`: Para operaciones relacionadas con el sistema operativo (no muy prominente aquí, pero a menudo en `settings`).
