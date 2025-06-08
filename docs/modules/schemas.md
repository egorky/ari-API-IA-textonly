# Esquemas Pydantic: app.schemas

**Archivo Original:** `app/schemas.py`

## Propósito General

El módulo `app.schemas.py` define los esquemas de datos utilizando Pydantic. Estos esquemas se utilizan principalmente para:

1.  **Validación de Datos de API:** Cuando los datos se reciben a través de solicitudes HTTP (ej. en el cuerpo de un POST o PUT), FastAPI utiliza estos esquemas para validar que los datos entrantes se ajustan a la estructura y los tipos esperados. Si la validación falla, FastAPI devuelve automáticamente una respuesta de error HTTP 422.
2.  **Serialización de Datos de Respuesta:** Al devolver datos en las respuestas de la API, estos esquemas se pueden usar para controlar el formato de salida, asegurando que solo se expongan los campos deseados y que los datos se serialicen correctamente (ej. de un objeto de modelo SQLAlchemy a un diccionario JSON).
3.  **Documentación Automática de API:** FastAPI utiliza estos esquemas Pydantic para generar automáticamente la documentación de la API (Swagger UI y ReDoc), mostrando los formatos de datos esperados para las solicitudes y respuestas.

Pydantic permite definir la "forma" de los datos con tipos de Python, ofreciendo validación de datos concisa y robusta.

## Esquemas Principales Definidos

A continuación, se describen los grupos principales de esquemas definidos en este módulo:

### 1. Esquemas para Prompts (`Prompt...`)

Estos esquemas se utilizan para las operaciones CRUD relacionadas con los prompts.

*   **`PromptBase`:**
    *   **Uso:** Esquema base que contiene los campos comunes compartidos por otros esquemas de prompt.
    *   **Campos Clave:** `name` (str), `content` (str), `metadata` (Optional[Dict[str, Any]]).
*   **`PromptCreate`:**
    *   **Uso:** Para validar los datos al crear un nuevo prompt. Hereda de `PromptBase`.
    *   **Campos Clave:** Los mismos que `PromptBase`.
*   **`PromptUpdate`:**
    *   **Uso:** Para validar los datos al actualizar un prompt existente. Todos los campos son opcionales, permitiendo actualizaciones parciales.
    *   **Campos Clave:** `name` (Optional[str]), `content` (Optional[str]), `metadata` (Optional[Dict[str, Any]]).
*   **`PromptInDB` (o `PromptResponse`, `Prompt`):**
    *   **Uso:** Para formatear los datos de un prompt al devolverlo en una respuesta de API (ej. después de crearlo o al obtenerlo). Hereda de `PromptBase`.
    *   **Campos Clave:** Incluye los campos de `PromptBase` más el `id` (int) del prompt.
    *   **Configuración:** `from_attributes = True` (o `orm_mode = True` en Pydantic v1) se utiliza para permitir que el esquema Pydantic se cree a partir de un objeto de modelo SQLAlchemy.

### 2. Esquemas para Herramientas (`Tool...`)

Estos esquemas se utilizan para las operaciones CRUD relacionadas con las herramientas/APIs.

*   **`ToolBase`:**
    *   **Uso:** Esquema base con campos comunes para las herramientas.
    *   **Campos Clave:** `name` (str), `description` (Optional[str]), `parameters` (Optional[Dict[str, Any]] - para el JSON schema de los parámetros), `api_config` (Optional[Dict[str, Any]] - para la configuración de la API como URL, método).
*   **`ToolCreate`:**
    *   **Uso:** Para validar los datos al crear una nueva herramienta. Hereda de `ToolBase`.
    *   **Campos Clave:** Los mismos que `ToolBase`.
*   **`ToolUpdate`:**
    *   **Uso:** Para validar los datos al actualizar una herramienta. Todos los campos son opcionales.
    *   **Campos Clave:** `name` (Optional[str]), `description` (Optional[str]), `parameters` (Optional[Dict[str, Any]]), `api_config` (Optional[Dict[str, Any]]).
*   **`ToolInDB` (o `ToolResponse`, `Tool`):**
    *   **Uso:** Para formatear los datos de una herramienta en las respuestas de API. Hereda de `ToolBase`.
    *   **Campos Clave:** Incluye los campos de `ToolBase` más el `id` (int) de la herramienta.
    *   **Configuración:** `from_attributes = True`.

### 3. Esquemas para Pruebas de Prompts (en `app.api.testing_router.py`, pero podrían referenciarse o definirse aquí)

*   **`PromptTestExecutionPayload`:**
    *   **Uso:** Para validar el cuerpo de la solicitud del endpoint `/api/testing/execute-test-prompt`.
    *   **Campos Clave:** `prompt_content` (str), `user_input` (str), `ai_model` (str), `session_id` (Optional[str]).
*   **`PromptTestExecutionResponse`:**
    *   **Uso:** Para estructurar la respuesta del endpoint `/api/testing/execute-test-prompt`.
    *   **Campos Clave:** `ai_response` (str), `session_id_used` (str).
*   **`SimplePromptInfo`:**
    *   **Uso:** Para devolver una lista simplificada de prompts (ID y nombre) para la UI de prueba de prompts.
    *   **Campos Clave:** `id` (int), `name` (str).

## Dependencias Clave

*   **`pydantic.BaseModel`:** La clase base de la cual heredan todos los esquemas Pydantic.
*   **`pydantic.Field`:** Para definir metadatos y validaciones adicionales en los campos del esquema (ej. longitud mínima/máxima, ejemplos).
*   **`typing` (Optional, Dict, Any, List):** Tipos estándar de Python utilizados para definir la estructura de los campos del esquema.

Este módulo es crucial para mantener una interfaz API bien definida, validada y documentada. Facilita la interacción entre el frontend, el backend y los desarrolladores que puedan consumir la API.
