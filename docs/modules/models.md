# Modelos de Datos SQLAlchemy: app.models

**Archivos Originales:**
*   `app/models/__init__.py`
*   `app/models/prompt.py`
*   `app/models/tool.py`

(Nota: Los modelos individuales `prompt.py` y `tool.py` no existen actualmente; los modelos `Prompt` y `Tool` están definidos directamente en un archivo como `app/models.py` o similar, o podrían estarlo si el proyecto crece. La documentación asumirá que están definidos y son accesibles a través de `app.models`). La clase `Base` para los modelos declarativos se define en `app.core.database`.

## Propósito General

El paquete/módulo `app.models` contiene las definiciones de los modelos de datos utilizando SQLAlchemy ORM. Estos modelos representan la estructura de las tablas en la base de datos y proporcionan una forma orientada a objetos para interactuar con esos datos.

Cada clase de modelo hereda de `app.core.database.Base`, lo que permite a SQLAlchemy mapearlas a tablas de base de datos. Los atributos de clase dentro de cada modelo corresponden a las columnas de sus respectivas tablas.

## Modelos Definidos

### 1. `Prompt`

*   **Tabla en BD:** `prompts`
*   **Descripción:** Representa una plantilla de prompt que puede ser utilizada por el servicio de IA. Los prompts son textos que guían al modelo de IA para generar respuestas específicas o comportarse de cierta manera.
*   **Campos Principales:**
    *   `id` (Integer, Primary Key): Identificador único para el prompt.
    *   `name` (String, Unique, Index): Un nombre único y legible por humanos para el prompt (ej. "customer_service_greeting", "technical_support_level_1"). Se utiliza para buscar prompts.
    *   `content` (Text): El contenido textual completo del prompt que se enviará al LLM. Puede incluir placeholders o snippets de JavaScript si la lógica de procesamiento de prompts los maneja.
    *   `metadata` (JSON, Opcional): Un campo JSON para almacenar cualquier metadato adicional relacionado con el prompt (ej. versión, etiquetas, información de autoría).

### 2. `Tool`

*   **Tabla en BD:** `tools`
*   **Descripción:** Representa una herramienta externa (generalmente una API) que el modelo de IA puede aprender a utilizar para obtener información del mundo real o realizar acciones.
*   **Campos Principales:**
    *   `id` (Integer, Primary Key): Identificador único para la herramienta.
    *   `name` (String, Unique, Index): Un nombre único para la herramienta (ej. "get_weather_api", "query_database_tool"). Este nombre es el que el LLM usará para referirse a la herramienta.
    *   `description` (Text, Opcional): Una descripción detallada de lo que hace la herramienta, para qué sirve y cuándo debería ser utilizada por el LLM.
    *   `parameters` (JSON, Opcional): Un objeto JSON que define el esquema de los parámetros que la herramienta espera. Esto debe seguir la especificación de JSON Schema (similar a OpenAPI) para que los LLMs (especialmente los que soportan "function calling" como OpenAI) puedan entender cómo estructurar los argumentos para la herramienta. Ejemplo: `{"type": "object", "properties": {"location": {"type": "string", "description": "City name"}}, "required": ["location"]}`.
    *   `api_config` (JSON, Opcional): Un objeto JSON que contiene la configuración necesaria para ejecutar la llamada a la API. Esto incluye:
        *   `url` (String): La URL del endpoint de la API.
        *   `method` (String): El método HTTP (ej. "GET", "POST").
        *   `headers` (Objeto JSON, Opcional): Cualquier cabecera HTTP necesaria (ej. para autenticación como `X-API-Key`).
        *   (Podría incluir otros campos como `body_template` si fuera necesario para transformaciones complejas, aunque actualmente `tool_executor.py` maneja el cuerpo JSON directamente desde los parámetros).

## Dependencias Clave

*   **`sqlalchemy` (ORM):** Se utilizan varios componentes de SQLAlchemy para definir los modelos:
    *   `Column`, `Integer`, `String`, `Text`, `JSON`: Para definir los tipos de datos de las columnas.
    *   Heredan de `app.core.database.Base` para el mapeo declarativo.

Estos modelos son fundamentales para la capa de persistencia de la aplicación, permitiendo almacenar y recuperar prompts y definiciones de herramientas de manera estructurada. Son utilizados por `app.crud` para las operaciones de base de datos y por `app.schemas` para la validación y serialización de datos en la capa API.
