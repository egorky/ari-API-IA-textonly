# Router: app.api.tools_router

**Archivo Original:** `app/api/tools_router.py`

## Propósito General

Este módulo define las rutas FastAPI relacionadas con la gestión de las "Herramientas" (Tools) que la IA puede utilizar. Similar al `prompts_router`, proporciona tanto una interfaz de usuario web (HTML) para la administración de herramientas como una API JSON subyacente. Las herramientas representan APIs externas o funcionalidades que el agente de IA puede invocar.

Las responsabilidades clave incluyen:

*   **Servir la Interfaz de Usuario Web (UI) para Herramientas:**
    *   **Listar Herramientas (`/ui/tools/` - GET):** Muestra una página HTML con una tabla de todas las herramientas definidas, obteniéndolas a través de `crud.get_tools`.
    *   **Crear Herramienta (Formulario) (`/ui/tools/create` - GET):** Muestra un formulario HTML para definir una nueva herramienta.
    *   **Editar Herramienta (Formulario) (`/ui/tools/{tool_id}/edit` - GET):** Muestra un formulario HTML pre-rellenado con los datos de una herramienta existente para su edición.
*   **Manejar Envíos de Formularios HTML para Operaciones CRUD:**
    *   Al igual que con `prompts_router`, la implementación actual favorece que la UI haga llamadas JavaScript a los endpoints API JSON en lugar de envíos de formularios HTML tradicionales para las operaciones de creación/actualización.
*   **Proporcionar Endpoints API JSON para Herramientas:**
    *   **Crear Herramienta (`/ui/tools/api` - POST):** Endpoint para crear una nueva definición de herramienta. Recibe datos validados por `schemas.ToolCreate`. Llama a `crud.create_tool`.
    *   **Leer Todas las Herramientas (`/ui/tools/api` - GET):** Endpoint para obtener una lista de todas las herramientas. Llama a `crud.get_tools`. Devuelve una lista de `schemas.ToolInDB`.
    *   **Leer Herramienta Específica (`/ui/tools/api/{tool_id}` - GET):** Endpoint para obtener una herramienta por su ID. Llama a `crud.get_tool`. Devuelve `schemas.ToolInDB`.
    *   **Actualizar Herramienta (`/ui/tools/api/{tool_id}` - PUT):** Endpoint para actualizar una herramienta existente. Recibe datos validados por `schemas.ToolUpdate`. Llama a `crud.update_tool`.
    *   **Eliminar Herramienta (`/ui/tools/api/{tool_id}` - DELETE):** Endpoint para eliminar una herramienta. Llama a `crud.delete_tool`.
*   **Seguridad:** Todas las rutas definidas en este router están protegidas y requieren autenticación de usuario, implementada mediante la dependencia `Depends(get_current_username)`.
*   **Renderizado de Plantillas:** Utiliza `Jinja2Templates` para renderizar las páginas HTML de la interfaz de usuario, pasando los datos necesarios (como la lista de herramientas o los detalles de una herramienta específica) al contexto de la plantilla.

## Campos Clave de una Herramienta

Al definir una herramienta, los campos importantes que este router maneja (a través de los schemas y el CRUD) son:
*   `name`: Nombre único de la herramienta.
*   `description`: Descripción para el LLM sobre qué hace la herramienta.
*   `parameters`: Esquema JSON de los parámetros que la herramienta espera.
*   `api_config`: Configuración para llamar a la API externa (URL, método, headers).

## Dependencias Clave

*   **`fastapi.APIRouter`:** Para la creación del objeto router.
*   **`fastapi.Depends`:** Para la inyección de dependencias (`get_db`, `get_current_username`).
*   **`fastapi.Request`:** Para el objeto de solicitud en rutas que renderizan plantillas.
*   **`fastapi.HTTPException`:** Para generar respuestas de error HTTP.
*   **`fastapi.responses.HTMLResponse`, `RedirectResponse`:** Para respuestas HTML o redirecciones (aunque las modificaciones se manejan vía API JSON).
*   **`sqlalchemy.orm.Session`:** Para el tipado de la dependencia `get_db`.
*   **`app.crud`:** Para acceder a las funciones CRUD que interactúan con la base de datos para las herramientas.
*   **`app.schemas`:** Para los modelos Pydantic (`ToolCreate`, `ToolUpdate`, `ToolInDB`) utilizados en la validación y serialización.
*   **`app.models`:** (Indirectamente, a través de `app.crud`) Para las definiciones de modelos SQLAlchemy.
*   **`app.core.database.get_db`:** Función de dependencia para obtener una sesión de base de datos.
*   **`app.core.security.get_current_username`:** Función de dependencia para autenticación y autorización.
*   **`jinja2.Jinja2Templates`:** Para renderizar las plantillas HTML.
*   **`logging`:** Para registro de eventos.
*   **`pathlib.Path`:** Para la gestión de rutas a directorios de plantillas.

Este router es crucial para la funcionalidad de "herramientas dinámicas", permitiendo a los usuarios configurar cómo la IA puede interactuar con sistemas externos.
