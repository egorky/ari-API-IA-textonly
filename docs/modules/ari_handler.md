# Módulo: app.api.ari_handler

**Archivo Original:** `app/api/ari_handler.py`

## Propósito General

Este módulo es el componente central para la interacción directa con el servidor Asterisk a través de la Asterisk REST Interface (ARI). Su función principal es escuchar eventos de Asterisk, manejar las llamadas entrantes a la aplicación Stasis designada y coordinar la interacción entre Asterisk y el servicio de inteligencia artificial.

Sus responsabilidades clave incluyen:

*   **Conexión al Servidor ARI:** Establece una conexión con el servidor Asterisk utilizando las credenciales y la URL especificadas en la configuración (`settings.ASTERISK_ARI_URL`, `settings.ASTERISK_ARI_USERNAME`, `settings.ASTERISK_ARI_PASSWORD`).
*   **Registro de la Aplicación Stasis:** Se suscribe a eventos para una aplicación Stasis específica, cuyo nombre está definido en `settings.ASTERISK_APP_NAME`.
*   **Manejo del Evento `StasisStart`:** Este es el punto de entrada para nuevas llamadas en la aplicación.
    *   Cuando una llamada entra en la aplicación Stasis, este manejador se activa.
    *   Extrae variables importantes pasadas desde el dialplan de Asterisk, como:
        *   `UNIQUEID`: Identificador único de la llamada, usado para la memoria de conversación.
        *   `USER_INPUT`: La entrada del usuario (ej. transcripción de voz).
        *   `AI_MODEL`: Preferencia de modelo IA para la llamada.
        *   `AI_PROMPT_NAME`: Nombre del prompt a utilizar.
        *   Otros argumentos `key=value` personalizados.
    *   Si `UNIQUEID` no se pasa explícitamente, utiliza el `channel.id` de ARI como fallback.
*   **Interacción con `ai_service`:**
    *   Llama a la función `ai_service.get_ai_response`, pasándole la entrada del usuario, el ID de sesión (`UNIQUEID`), una sesión de base de datos, la preferencia de modelo y el nombre del prompt.
*   **Devolución de Respuesta al Dialplan:**
    *   Una vez que `ai_service` devuelve la respuesta generada por la IA, este módulo la establece como una variable de canal en Asterisk (ej. `AI_RESPONSE`) utilizando `channel.setChannelVar()`.
    *   Esto permite que el dialplan de Asterisk continúe el flujo de la llamada utilizando la respuesta de la IA (ej. para reproducción con Text-to-Speech).
*   **Manejo de Errores y Continuación del Dialplan:**
    *   Captura excepciones durante la interacción con ARI o el `ai_service`.
    *   Intenta establecer variables de canal de error (ej. `ARI_ERROR` o `SYSTEM_ERROR`) para que el dialplan pueda manejar estas situaciones.
    *   Asegura que la llamada salga de la aplicación Stasis para continuar en el dialplan.
*   **Reconexión Automática:** Implementa un bucle (`_run_ari_client_with_retry`) que intenta reconectar con el servidor ARI en caso de desconexión, proporcionando resiliencia.
*   **Gestión de Tareas Asíncronas:** Utiliza `asyncio` para manejar las operaciones de red de ARI y la tarea del cliente de forma asíncrona.

## Dependencias Clave

*   **`app.vendor.ari_py`:** La biblioteca cliente Python para interactuar con la interface ARI de Asterisk. (Vendida dentro del proyecto).
*   **`app.core.config.settings`:** Para acceder a las configuraciones de la aplicación, especialmente las relacionadas con Asterisk (URL, credenciales, nombre de la aplicación).
*   **`app.services.ai_service`:** Para obtener la lógica de procesamiento de IA y las respuestas generadas.
*   **`app.core.database.SessionLocal`:** Para crear una sesión de base de datos que se pasa al `ai_service` (usada para cargar prompts, herramientas, etc.).
*   **`asyncio`:** Para la programación asíncrona, esencial para manejar eventos de red de manera eficiente.
*   **`logging`:** Para registrar información sobre el flujo de llamadas, eventos y errores.
