# Módulo: app.services.tool_executor

**Archivo Original:** `app/services/tool_executor.py`

## Propósito General

Este módulo es responsable de la ejecución real de las llamadas a APIs externas que han sido definidas como "herramientas" y que el modelo de IA decide utilizar. Actúa como un puente entre la decisión del agente de IA de usar una herramienta y la interacción efectiva con el servicio externo.

Sus funciones clave son:

*   **Recepción de Configuración y Parámetros:**
    *   La función principal `execute_api_tool` recibe tres argumentos principales:
        *   `api_config` (Diccionario): Contiene la configuración de la API para la herramienta específica, incluyendo la `url`, el `method` HTTP (GET, POST, etc.), y los `headers` necesarios.
        *   `parameters_schema` (Diccionario, opcional): El esquema JSON (según la especificación OpenAPI/JSON Schema) que define los parámetros esperados por la herramienta.
        *   `tool_input` (Mixto): Los argumentos reales proporcionados por el LLM para la herramienta. Puede ser un diccionario (si el LLM estructura los argumentos) o una cadena (que podría ser una cadena JSON o un valor simple).
*   **Procesamiento y Validación de `tool_input`:**
    *   Intenta parsear `tool_input` si es una cadena JSON.
    *   Si se proporciona un `parameters_schema`, utiliza la biblioteca `jsonschema` para validar el `parsed_input` (los argumentos procesados) contra este esquema.
    *   Si la validación falla debido a una `ValidationError`, se registra un error y se devuelve un mensaje descriptivo a la IA, evitando la llamada a la API externa.
*   **Construcción de la Solicitud HTTP:**
    *   Basándose en el `method` HTTP (GET, POST, PUT, PATCH) y el `parsed_input` (validado):
        *   Para **GET**: Los parámetros del `parsed_input` (si es un diccionario) se utilizan como parámetros de consulta (query string). Si `parsed_input` es un valor simple y el esquema define un solo parámetro, se intenta usar ese valor para el parámetro.
        *   Para **POST, PUT, PATCH**: Si `parsed_input` es un diccionario, se envía como el cuerpo JSON de la solicitud. Si es una cadena, se intenta enviar como JSON (si es una cadena JSON válida) o se envuelve en un objeto `{"value": parsed_input}` como fallback para algunos casos.
*   **Ejecución Asíncrona de la Llamada HTTP:**
    *   Utiliza `httpx.AsyncClient` para realizar la llamada a la API de forma asíncrona, lo cual es importante para no bloquear el bucle de eventos de la aplicación FastAPI.
    *   Configura la URL, método, headers, parámetros de consulta y cuerpo JSON según corresponda.
    *   Establece un timeout para la solicitud.
*   **Procesamiento de la Respuesta de la API:**
    *   Verifica si la respuesta HTTP fue exitosa (usando `response.raise_for_status()`).
    *   Intenta interpretar la respuesta como JSON. Si tiene éxito, la serializa de nuevo a una cadena JSON.
    *   Si la respuesta no es JSON, devuelve el contenido de texto plano de la respuesta.
    *   El objetivo es siempre devolver una representación en cadena del resultado de la API, ya que es lo que los agentes de LangChain generalmente esperan.
*   **Manejo Detallado de Errores:**
    *   Captura `httpx.HTTPStatusError` para errores HTTP (4xx, 5xx), extrayendo detalles del cuerpo de la respuesta si es posible.
    *   Captura `httpx.RequestError` para problemas de conexión o de red.
    *   Captura excepciones genéricas que puedan ocurrir durante el proceso.
    *   En todos los casos de error, se registra el problema y se devuelve un mensaje de error descriptivo en formato de cadena, que puede ser utilizado por la IA para entender por qué falló la herramienta.

## Dependencias Clave

*   **`httpx`:** Una biblioteca moderna para realizar clientes HTTP asíncronos y síncronos. Se utiliza aquí para las llamadas asíncronas a las APIs externas.
*   **`jsonschema`:** Para validar los parámetros de entrada (`tool_input`) proporcionados por la IA contra el esquema JSON (`parameters_schema`) definido para la herramienta.
*   **`logging`:** Para registrar información sobre la ejecución de herramientas, incluyendo los parámetros, errores y resultados.
*   **`json`:** Para parsear y serializar datos en formato JSON.
