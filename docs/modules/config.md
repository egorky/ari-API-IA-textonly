# Módulo: app.core.config

**Archivo Original:** `app/core/config.py`

## Propósito General

Este módulo es central para la gestión de la configuración de la aplicación. Su principal objetivo es definir y cargar todas las variables de configuración que la aplicación necesita para operar correctamente.

Utiliza la biblioteca `pydantic-settings` para lograr una configuración robusta y tipada. Las características clave son:

*   **Clase `Settings`:**
    *   Define una clase llamada `Settings` que hereda de `pydantic_settings.BaseSettings`.
    *   Cada atributo de esta clase representa una variable de configuración esperada por la aplicación (ej. `OPENAI_API_KEY`, `DATABASE_URL`, etc.).
    *   Los atributos están tipados (ej. `str`, `int`, `bool`), lo que `pydantic-settings` utiliza para validar y convertir los valores cargados.
    *   Se pueden definir valores por defecto directamente en la clase. Estos valores se utilizarán si la variable correspondiente no se encuentra en el entorno o en el archivo `.env`.

*   **Carga desde Archivo `.env`:**
    *   Dentro de la clase `Settings`, una clase interna `Config` especifica `env_file = ".env"`.
    *   Esto instruye a `pydantic-settings` para que intente cargar los valores de las variables de configuración desde un archivo llamado `.env` ubicado en el directorio raíz del proyecto.
    *   Las variables definidas en el archivo `.env` anulan los valores por defecto definidos en la clase `Settings`.

*   **Instancia Global `settings`:**
    *   El módulo crea una instancia única de la clase `Settings`, llamada `settings`.
    *   Esta instancia `settings` se importa y utiliza en toda la aplicación siempre que se necesite acceder a un valor de configuración. Esto proporciona un punto de acceso centralizado y consistente a la configuración.

En resumen, `app.core.config.py` proporciona una forma estructurada, validada y fácil de usar para gestionar las configuraciones de la aplicación, priorizando las variables de entorno (a través de `.env`) sobre los valores predeterminados codificados.

## Dependencias Clave

*   **`pydantic-settings`:** La biblioteca fundamental utilizada para la creación de la clase `Settings` y la carga de configuraciones desde variables de entorno y archivos `.env`.

## Variables de Configuración Definidas

Para obtener una lista detallada de todas las variables de configuración gestionadas por este módulo, su propósito, valores por defecto y ejemplos, consulte el documento:
[Variables de Configuración](../../01_configuration_variables.md)
