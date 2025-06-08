# Módulo: app.main

**Archivo Original:** `app/main.py`

## Propósito General

Este módulo es el punto de entrada principal de la aplicación FastAPI. Es responsable de configurar e inicializar la aplicación, así como de definir la lógica de alto nivel para el manejo de eventos de ciclo de vida y rutas globales.

Sus responsabilidades clave incluyen:

*   **Inicialización de FastAPI:** Crea la instancia principal de la aplicación FastAPI, estableciendo el título, versión y descripción del servicio.
*   **Creación de Tablas de Base de Datos:** Al inicio, ejecuta `app_models.Base.metadata.create_all(bind=engine)` para crear todas las tablas definidas en los modelos SQLAlchemy si aún no existen.
*   **Inclusión de Routers API:** Integra los diferentes routers que definen los endpoints específicos de la aplicación:
    *   `app.api.prompts_router.router`: Para la gestión de Prompts (CRUD UI y API).
    *   `app.api.tools_router.router`: Para la gestión de Herramientas/APIs (CRUD UI y API).
    *   `app.api.testing_router.router`: Para las APIs de backend de la funcionalidad de prueba de prompts.
*   **Manejo de Eventos de Ciclo de Vida:**
    *   **`startup`:**
        *   Inicia el listener de eventos ARI (`ari_handler.start_ari_listener()`) para conectarse a Asterisk y comenzar a procesar llamadas.
        *   Inicializa el cliente Redis (`get_redis_client()`) para asegurar que la conexión esté disponible.
    *   **`shutdown`:**
        *   Cancela la tarea del listener ARI para una finalización limpia.
*   **Definición de Rutas UI Principales:**
    *   **`/` (root):** Una ruta simple que devuelve un mensaje de bienvenida.
    *   **`/ui` (dashboard):** Sirve la página principal del dashboard de la interfaz web (`index.html`), mostrando el estado del sistema y enlaces de navegación.
    *   **`/ui/test-prompt`:** Sirve la página de prueba de prompts (`testing/test_prompt.html`).
*   **Servicio de Archivos Estáticos y Plantillas:**
    *   Configura el servicio de archivos estáticos (CSS, JS del lado del cliente) desde el directorio `app/static/`.
    *   Configura `Jinja2Templates` para renderizar las plantillas HTML desde el directorio `app/templates/`.

## Dependencias Clave

*   **Framework Web:**
    *   `fastapi`: El framework principal para construir la API y la aplicación web.
    *   `uvicorn`: El servidor ASGI utilizado para ejecutar la aplicación FastAPI.
*   **Routers API (Internos):**
    *   `app.api.prompts_router`: Maneja las rutas relacionadas con los prompts.
    *   `app.api.tools_router`: Maneja las rutas relacionadas con las herramientas.
    *   `app.api.testing_router`: Maneja las rutas para la funcionalidad de prueba de prompts.
*   **Servicios (Internos):**
    *   `app.api.ari_handler` (referenciado como `ari_handler`): Para la lógica de interacción con Asterisk ARI (inicio/parada del listener, obtención del estado del cliente).
    *   `app.services.redis_service`: Para obtener el cliente Redis.
    *   `app.services.ai_service`: (Indirectamente, a través de `PY_MINI_RACER_AVAILABLE` y `JS_CONTEXT` para el estado del procesador JS en el dashboard).
*   **Configuración (Interna):**
    *   `app.core.config.settings`: Para acceder a todas las variables de configuración de la aplicación.
*   **Base de Datos (Interna):**
    *   `app.core.database.engine`: El motor SQLAlchemy utilizado para la conexión a la base de datos.
    *   `app.core.database.get_db`: Función de dependencia para obtener una sesión de base de datos en las rutas.
    *   `app.models`: Módulos que contienen las definiciones de las tablas SQLAlchemy (utilizados para `create_all`).
*   **Seguridad (Interna):**
    *   `app.core.security.get_current_username`: Función de dependencia para proteger las rutas de la interfaz web y obtener el nombre de usuario autenticado.
*   **Otros:**
    *   `pathlib`: Para la gestión de rutas de archivos.
    *   `asyncio`: Para la concurrencia (usado por FastAPI y ARI).
    *   `logging`, `sys`: Para la configuración del logging.
