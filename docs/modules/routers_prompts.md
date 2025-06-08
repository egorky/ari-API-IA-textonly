# Router: app.api.prompts_router

**Archivo Original:** `app/api/prompts_router.py`

## Propósito General

Este módulo define las rutas FastAPI relacionadas con la gestión de los "Prompts" de IA. Proporciona tanto una interfaz de usuario web (HTML) para que los administradores gestionen los prompts, como una API JSON para la interacción programática si fuera necesario (aunque el enfoque principal es la UI).

Las responsabilidades clave incluyen:

*   **Servir la Interfaz de Usuario Web (UI) para Prompts:**
    *   **Listar Prompts (`/ui/prompts/` - GET):** Muestra una página HTML con una tabla de todos los prompts existentes, obteniéndolos a través de `crud.get_prompts`.
    *   **Crear Prompt (Formulario) (`/ui/prompts/create` - GET):** Muestra un formulario HTML para crear un nuevo prompt.
    *   **Editar Prompt (Formulario) (`/ui/prompts/{prompt_id}/edit` - GET):** Muestra un formulario HTML pre-rellenado con los datos de un prompt existente para su edición.
*   **Manejar Envíos de Formularios HTML para Operaciones CRUD:**
    *   Aunque no se detalla explícitamente en el plan original de esta tarea de documentación, típicamente un router que sirve formularios HTML también manejaría las solicitudes POST resultantes de esos envíos para crear o actualizar recursos. Estas rutas POST esperarían datos de formulario, llamarían a las funciones CRUD correspondientes (`crud.create_prompt`, `crud.update_prompt`) y luego redirigirían de nuevo a la página de lista o mostrarían el formulario con errores. *Nota: La implementación actual en el código fuente usa rutas API JSON para las operaciones de modificación y la UI hace llamadas JavaScript a estas APIs en lugar de envíos de formulario HTML tradicionales.*
*   **Proporcionar Endpoints API JSON para Prompts:**
    *   **Crear Prompt (`/ui/prompts/api` - POST):** Endpoint para crear un nuevo prompt. Recibe datos validados por `schemas.PromptCreate`. Llama a `crud.create_prompt`.
    *   **Leer Todos los Prompts (`/ui/prompts/api` - GET):** Endpoint para obtener una lista de todos los prompts. Llama a `crud.get_prompts`. Devuelve una lista de `schemas.PromptInDB`.
    *   **Leer Prompt Específico (`/ui/prompts/api/{prompt_id}` - GET):** Endpoint para obtener un prompt por su ID. Llama a `crud.get_prompt`. Devuelve `schemas.PromptInDB`.
    *   **Actualizar Prompt (`/ui/prompts/api/{prompt_id}` - PUT):** Endpoint para actualizar un prompt existente. Recibe datos validados por `schemas.PromptUpdate`. Llama a `crud.update_prompt`.
    *   **Eliminar Prompt (`/ui/prompts/api/{prompt_id}` - DELETE):** Endpoint para eliminar un prompt. Llama a `crud.delete_prompt`.
*   **Seguridad:** Todas las rutas definidas en este router están protegidas y requieren autenticación de usuario, lograda mediante la dependencia `Depends(get_current_username)`.
*   **Renderizado de Plantillas:** Utiliza `Jinja2Templates` para renderizar las páginas HTML, pasando los datos necesarios al contexto de la plantilla.

## Dependencias Clave

*   **`fastapi.APIRouter`:** Para crear el objeto router.
*   **`fastapi.Depends`:** Para la inyección de dependencias (ej. `get_db`, `get_current_username`).
*   **`fastapi.Request`:** Para acceder al objeto de solicitud en las rutas que renderizan plantillas.
*   **`fastapi.HTTPException`:** Para generar respuestas de error HTTP.
*   **`fastapi.responses.HTMLResponse`, `RedirectResponse`:** Para devolver respuestas HTML o redirecciones.
*   **`sqlalchemy.orm.Session`:** Para el tipado de la dependencia `get_db`.
*   **`app.crud`:** Para acceder a las funciones CRUD que interactúan con la base de datos para los prompts.
*   **`app.schemas`:** Para los modelos Pydantic (`PromptCreate`, `PromptUpdate`, `PromptInDB`) utilizados en la validación de datos de API y la serialización de respuestas.
*   **`app.models`:** (Indirectamente, a través de `app.crud`) Para las definiciones de modelos SQLAlchemy.
*   **`app.core.database.get_db`:** La función de dependencia para obtener una sesión de base de datos.
*   **`app.core.security.get_current_username`:** La función de dependencia para la autenticación y autorización.
*   **`jinja2.Jinja2Templates`:** Para renderizar las plantillas HTML para la interfaz de usuario.
*   **`logging`:** Para registrar información y errores.
*   **`pathlib.Path`:** Para construir rutas a los directorios de plantillas.

Este router es esencial para permitir la gestión de los prompts que guían el comportamiento de los modelos de IA en la aplicación.
