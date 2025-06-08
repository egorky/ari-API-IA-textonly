# Variables de Configuración

Este documento detalla todas las variables de entorno y del dialplan utilizadas por la aplicación para su configuración y operación.

## Introducción

La aplicación utiliza una combinación de variables de entorno (generalmente gestionadas a través de un archivo `.env`) y argumentos pasados desde el dialplan de Asterisk al iniciar la aplicación Stasis. Esta aproximación permite una configuración flexible tanto para el entorno de despliegue como para el comportamiento en tiempo de ejecución por llamada.

Las variables de entorno se cargan al inicio de la aplicación utilizando la biblioteca `pydantic-settings`, que lee desde un archivo `.env` ubicado en la raíz del proyecto. Las variables del dialplan se parsean en `app.api.ari_handler.py` cuando una nueva llamada entra en la aplicación Stasis.

## Variables de Entorno (`.env`)

Estas variables se definen típicamente en un archivo `.env` en la raíz del proyecto. Se recomienda copiar `.env.example` a `.env` y modificarlo según sea necesario.

---

**`OPENAI_API_KEY`**
*   **Descripción:** Su clave API para los servicios de OpenAI (GPT).
*   **Valor por Defecto en Código:** `"your_openai_api_key_here"`
*   **Ejemplo de Valor:** `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
*   **Notas:** Requerida si se utiliza `openai` como `DEFAULT_AI_MODEL` o se selecciona a través del dialplan.

---

**`GEMINI_API_KEY`**
*   **Descripción:** Su clave API para los servicios de Google AI (Gemini).
*   **Valor por Defecto en Código:** `"your_gemini_api_key_here"`
*   **Ejemplo de Valor:** `AIzaSyxxxxxxxxxxxxxxxxxxxxxxxxxxx`
*   **Notas:** Requerida si se utiliza `gemini` como `DEFAULT_AI_MODEL` o se selecciona a través del dialplan.

---

**`OPENAI_MODEL_NAME`**
*   **Descripción:** El identificador del modelo específico de OpenAI a utilizar.
*   **Valor por Defecto en Código:** `"gpt-3.5-turbo-0125"`
*   **Ejemplo de Valor:** `gpt-4-turbo-preview`
*   **Notas:** Utilizado cuando el modelo seleccionado es OpenAI.

---

**`GEMINI_MODEL_NAME`**
*   **Descripción:** El identificador del modelo específico de Gemini a utilizar.
*   **Valor por Defecto en Código:** `"gemini-pro"`
*   **Ejemplo de Valor:** `gemini-1.5-pro-latest`
*   **Notas:** Utilizado cuando el modelo seleccionado es Gemini.

---

**`DEFAULT_AI_MODEL`**
*   **Descripción:** El modelo de IA a utilizar por defecto si no se especifica uno diferente a través del dialplan (`AI_MODEL`).
*   **Valor por Defecto en Código:** `"openai"`
*   **Ejemplo de Valor:** `gemini`
*   **Notas:** Debe ser `openai` o `gemini` (insensible a mayúsculas/minúsculas en la práctica debido al procesamiento en `ai_service.py`).

---

**`DEBUG_MODE`**
*   **Descripción:** Activa o desactiva el modo debug. Principalmente afecta la verbosidad de los logs de LangChain.
*   **Valor por Defecto en Código:** `False`
*   **Ejemplo de Valor:** `True`
*   **Notas:** Útil para el desarrollo y la depuración.

---

**`REDIS_HOST`**
*   **Descripción:** El nombre de host o la dirección IP del servidor Redis.
*   **Valor por Defecto en Código:** `"localhost"`
*   **Ejemplo de Valor:** `redis_service` (si se usa Docker Compose con un servicio llamado `redis_service`)
*   **Notas:** Utilizado para la memoria de conversación.

---

**`REDIS_PORT`**
*   **Descripción:** El puerto en el que el servidor Redis está escuchando.
*   **Valor por Defecto en Código:** `6379`
*   **Ejemplo de Valor:** `6379`
*   **Notas:** Estándar para Redis.

---

**`REDIS_PASSWORD`**
*   **Descripción:** La contraseña para la conexión al servidor Redis.
*   **Valor por Defecto en Código:** `""` (string vacío, sin contraseña)
*   **Ejemplo de Valor:** `your_redis_password`
*   **Notas:** Dejar vacío si Redis no tiene configurada una contraseña.

---

**`DATABASE_URL`**
*   **Descripción:** La URL de conexión a la base de datos SQLAlchemy.
*   **Valor por Defecto en Código:** `"sqlite:///./test.db"` (un archivo SQLite en la raíz del proyecto)
*   **Ejemplo de Valor:** `postgresql://user:password@host:port/database`
*   **Notas:** Define dónde se almacenarán los prompts y las configuraciones de herramientas.

---

**`WEB_UI_USERNAME`**
*   **Descripción:** El nombre de usuario para acceder a la interfaz web (`/ui/*`).
*   **Valor por Defecto en Código:** `"admin"`
*   **Ejemplo de Valor:** `myadmin`
*   **Notas:** Utiliza autenticación básica HTTP.

---

**`WEB_UI_PASSWORD`**
*   **Descripción:** La contraseña para acceder a la interfaz web.
*   **Valor por Defecto en Código:** `"password"`
*   **Ejemplo de Valor:** `secure_password123`
*   **Notas:** Asegúrese de cambiar esto en un entorno de producción.

---

**`SECRET_KEY`**
*   **Descripción:** Una clave secreta utilizada por FastAPI para ciertas funciones de seguridad (ej. cookies de sesión si se usaran explícitamente, firma de tokens JWT si se implementaran).
*   **Valor por Defecto en Código:** `"a_very_secret_key_for_jwt_or_sessions"`
*   **Ejemplo de Valor:** Una cadena larga y aleatoria (ej. generada con `openssl rand -hex 32`).
*   **Notas:** Crítico para la seguridad en producción.

---

**`ASTERISK_ARI_URL`**
*   **Descripción:** La URL base para la interfaz ARI de Asterisk.
*   **Valor por Defecto en Código:** `"http://localhost:8088"`
*   **Ejemplo de Valor:** `http://asterisk_server:8088`
*   **Notas:** La aplicación añadirá rutas específicas como `/ari/events` a esta URL base.

---

**`ASTERISK_ARI_USERNAME`**
*   **Descripción:** El nombre de usuario para la conexión ARI.
*   **Valor por Defecto en Código:** `"asterisk"`
*   **Ejemplo de Valor:** `ari_user`
*   **Notas:** Definido en `ari.conf` en Asterisk.

---

**`ASTERISK_ARI_PASSWORD`**
*   **Descripción:** La contraseña para la conexión ARI.
*   **Valor por Defecto en Código:** `"asterisk"`
*   **Ejemplo de Valor:** `ari_password`
*   **Notas:** Definido en `ari.conf` en Asterisk.

---

**`ASTERISK_APP_NAME`**
*   **Descripción:** El nombre de la aplicación Stasis que esta instancia manejará.
*   **Valor por Defecto en Código:** `"ai_ari_app"`
*   **Ejemplo de Valor:** `my_ai_ivr`
*   **Notas:** Debe coincidir con el nombre usado en la llamada a `Stasis()` en el dialplan de Asterisk.

## Variables del Dialplan de Asterisk

Estas variables se pasan como argumentos a la aplicación Stasis cuando se llama desde el dialplan de Asterisk. `app.api.ari_handler.py` parsea estos argumentos.

Ejemplo de llamada en `extensions.conf`:
```
exten => _X.,1,Stasis(ai_ari_app,UNIQUEID=${UNIQUEID},USER_INPUT=${YOUR_DIALPLAN_VARIABLE},AI_MODEL=gemini,AI_PROMPT_NAME=support_prompt)
```

---

**`UNIQUEID`**
*   **Descripción:** El identificador único de la llamada en Asterisk.
*   **Uso en la Aplicación:** Se utiliza como `session_id` para la memoria de conversación en Redis, asegurando que cada llamada tenga su propio historial de conversación. Si no se pasa explícitamente `UNIQUEID=...` en los argumentos del dialplan, la aplicación intentará usar el `channel.id` de ARI como fallback.
*   **Ejemplo de Dialplan:** `UNIQUEID=${CHANNEL(UNIQUEID)}` o `UNIQUEID=${UNIQUEID}` (dependiendo de la versión de Asterisk).

---

**`USER_INPUT`**
*   **Descripción:** La entrada del usuario, generalmente obtenida de una grabación de voz (Speech-to-Text) o DTMF.
*   **Uso en la Aplicación:** Es el texto principal que se envía al servicio de IA para su procesamiento.
*   **Ejemplo de Dialplan:** `USER_INPUT=${ASR_RESULT}` (si `ASR_RESULT` contiene la transcripción).
*   **Notas:** Si no se proporciona, se usará un valor predeterminado como "No input provided".

---

**`AI_MODEL`**
*   **Descripción:** Permite especificar qué modelo de IA utilizar para una llamada particular (ej. "openai" o "gemini").
*   **Uso en la Aplicación:** Anula el valor de `DEFAULT_AI_MODEL` definido en el archivo `.env`.
*   **Precedencia:** Variable del Dialplan > Variable de Entorno (`DEFAULT_AI_MODEL`) > Valor Predeterminado en Código (`config.py`).
*   **Ejemplo de Dialplan:** `AI_MODEL=gemini`

---

**`AI_PROMPT_NAME`**
*   **Descripción:** El nombre de un prompt predefinido (gestionado a través de la UI) que se utilizará para esta llamada.
*   **Uso en la Aplicación:** El `ai_service` cargará el contenido de este prompt desde la base de datos y lo usará como el prompt del sistema para la IA.
*   **Ejemplo de Dialplan:** `AI_PROMPT_NAME=customer_greeting_prompt`
*   **Notas:** Si no se proporciona o el nombre no se encuentra, se utilizará un prompt por defecto definido en `ai_service.py`. Si se utiliza `prompt_content_override` en la UI de testing, esta variable se ignora.

---

**Otras Variables (Genéricas `key=value`)**
*   **Descripción:** `ari_handler.py` está diseñado para parsear cualquier argumento adicional pasado en formato `clave=valor` desde el dialplan.
*   **Uso en la Aplicación:** Actualmente, no se utilizan explícitamente otras variables genéricas en la lógica principal, pero podrían ser útiles para futuras extensiones o logging personalizado sin modificar el código del handler.
*   **Ejemplo de Dialplan:** `MyCustomVar=SomeValue,AnotherVar=123`
