# Router: app.api.testing_router

**Archivo Original:** `app/api/testing_router.py`

## Propósito General

Este módulo define las rutas FastAPI que sirven de backend para la funcionalidad de "Prueba de Prompts" disponible en la interfaz de usuario web. Permite a los usuarios experimentar interactivamente con diferentes prompts, entradas de usuario y modelos de IA para observar las respuestas generadas.

Las responsabilidades clave de este router son:

*   **Listar Prompts Existentes (GET `/api/testing/list-prompts`):**
    *   Proporciona un endpoint para que la UI de prueba de prompts pueda obtener una lista simplificada (ID y nombre) de todos los prompts almacenados en la base de datos.
    *   Utiliza `crud.get_prompts` para obtener los datos.
    *   Devuelve los datos usando el esquema `SimplePromptInfo` para minimizar la cantidad de información transferida.
*   **Obtener Contenido de un Prompt Específico (GET `/api/testing/get-prompt-content/{prompt_id}`):**
    *   Permite a la UI de prueba cargar el contenido completo de un prompt existente cuando el usuario lo selecciona de la lista.
    *   Utiliza `crud.get_prompt` para obtener el prompt por su ID.
    *   Devuelve un diccionario con el campo `content` del prompt.
*   **Ejecutar Prueba de Prompt (POST `/api/testing/execute-test-prompt`):**
    *   Este es el endpoint principal para la funcionalidad de prueba.
    *   Recibe un payload (validado por `PromptTestExecutionPayload`) que contiene:
        *   `prompt_content`: El contenido del prompt a probar (puede ser personalizado o cargado de un prompt existente).
        *   `user_input`: La entrada del usuario para la IA.
        *   `ai_model`: El modelo de IA a utilizar (ej. "openai", "gemini").
        *   `session_id` (Opcional): Un ID de sesión para mantener la continuidad de la conversación si se desea probar interacciones múltiples. Si no se proporciona, se genera uno nuevo usando `uuid.uuid4()`.
    *   Llama a la función `ai_service.get_ai_response` con los parámetros recibidos, utilizando específicamente el argumento `prompt_content_override` para pasar el contenido del prompt.
    *   Devuelve la respuesta generada por la IA y el ID de sesión utilizado, estructurado según el esquema `PromptTestExecutionResponse`.
*   **Seguridad:** Todas las rutas en este router están protegidas y requieren que el usuario esté autenticado, lo cual se maneja mediante la dependencia `Depends(get_current_username)`.

Este router no sirve directamente ninguna página HTML, sino que proporciona los endpoints API necesarios para que la página `testing/test_prompt.html` (servida por `app.main.py`) funcione interactivamente.

## Dependencias Clave

*   **`fastapi.APIRouter`:** Para la creación del objeto router.
*   **`fastapi.Depends`:** Para la inyección de dependencias (`get_db`, `get_current_username`).
*   **`fastapi.HTTPException`:** Para generar respuestas de error HTTP.
*   **`sqlalchemy.orm.Session`:** Para el tipado de la dependencia `get_db`.
*   **`pydantic.BaseModel`, `Field`:** Para definir los esquemas de solicitud y respuesta (`PromptTestExecutionPayload`, `PromptTestExecutionResponse`, `SimplePromptInfo`).
*   **`app.crud`:** Para acceder a las funciones que leen datos de prompts de la base de datos.
*   **`app.schemas`:** (Indirectamente, si los esquemas Pydantic se definen allí, aunque en este caso están definidos localmente en el router).
*   **`app.services.ai_service`:** Para llamar a la función principal de generación de respuestas de IA (`get_ai_response`).
*   **`app.core.database.get_db`:** Función de dependencia para obtener una sesión de base de datos.
*   **`app.core.security.get_current_username`:** Función de dependencia para la autenticación.
*   **`uuid`:** Para generar IDs de sesión únicos para las pruebas.
*   **`logging`:** Para registrar información sobre las solicitudes de prueba y cualquier error.
*   **`typing` (List, Optional, Dict, Any):** Para el tipado de Python.
