# Módulo: app.crud

**Archivo Original:** `app/crud.py`

## Propósito General

El módulo `crud.py` (Create, Read, Update, Delete) encapsula la lógica de interacción directa con la base de datos para los modelos de datos de la aplicación, específicamente `Prompt` y `Tool`. Su objetivo es abstraer las operaciones de base de datos del resto de la aplicación (especialmente de los routers API), proporcionando un conjunto claro de funciones para manipular estos recursos.

Al centralizar estas operaciones, se promueve un código más limpio, se evita la duplicación y se facilita el mantenimiento y las pruebas de la lógica de base de datos.

Cada conjunto de funciones CRUD para un modelo típicamente incluye:

*   **Crear (`create_`):**
    *   Toma un esquema Pydantic (ej. `schemas.PromptCreate`) como entrada con los datos para el nuevo objeto.
    *   Crea una instancia del modelo SQLAlchemy correspondiente (ej. `models.Prompt`).
    *   Añade la nueva instancia a la sesión de base de datos.
    *   Confirma (commits) la transacción.
    *   Refresca la instancia para obtener los valores generados por la base de datos (ej. el ID).
    *   Devuelve la instancia del modelo SQLAlchemy recién creada.
*   **Leer (`get_`, `get_..._by_...`):**
    *   `get_...`: Recupera un único objeto por su ID.
    *   `get_..._by_...`: Recupera un único objeto por otro campo único (ej. `get_prompt_by_name`).
    *   `get_...(s)`: Recupera una lista de objetos, a menudo con parámetros de paginación (`skip`, `limit`).
    *   Utiliza consultas (`db.query(...)`) para buscar los objetos en la base de datos.
    *   Devuelve el/los objeto(s) encontrado(s) o `None` si no se encuentra.
*   **Actualizar (`update_`):**
    *   Toma el ID del objeto a actualizar y un esquema Pydantic (ej. `schemas.PromptUpdate`) con los datos a modificar.
    *   Primero recupera el objeto existente de la base de datos.
    *   Si se encuentra, actualiza sus atributos basándose en los datos proporcionados en el esquema de actualización (generalmente excluyendo los valores no establecidos para permitir actualizaciones parciales).
    *   Confirma la transacción.
    *   Refresca la instancia.
    *   Devuelve la instancia del modelo SQLAlchemy actualizada.
*   **Eliminar (`delete_`):**
    *   Toma el ID del objeto a eliminar.
    *   Primero recupera el objeto existente.
    *   Si se encuentra, lo elimina de la sesión de base de datos.
    *   Confirma la transacción.
    *   Devuelve el objeto eliminado (o a veces `None` o un booleano indicando éxito).

Este módulo trabaja directamente con las sesiones de SQLAlchemy, los modelos SQLAlchemy y los esquemas Pydantic.

## Funciones CRUD Implementadas

*   **Para Prompts (`models.Prompt`, `schemas.Prompt...`):**
    *   `get_prompt(db: Session, prompt_id: int)`
    *   `get_prompt_by_name(db: Session, name: str)`
    *   `get_prompts(db: Session, skip: int = 0, limit: int = 100)`
    *   `create_prompt(db: Session, prompt: schemas.PromptCreate)`
    *   `update_prompt(db: Session, prompt_id: int, prompt_update: schemas.PromptUpdate)`
    *   `delete_prompt(db: Session, prompt_id: int)`
*   **Para Herramientas (`models.Tool`, `schemas.Tool...`):**
    *   `get_tool(db: Session, tool_id: int)`
    *   `get_tool_by_name(db: Session, name: str)`
    *   `get_tools(db: Session, skip: int = 0, limit: int = 100)`
    *   `create_tool(db: Session, tool: schemas.ToolCreate)`
    *   `update_tool(db: Session, tool_id: int, tool_update: schemas.ToolUpdate)`
    *   `delete_tool(db: Session, tool_id: int)`

## Dependencias Clave

*   **`sqlalchemy.orm.Session`:** El objeto de sesión de SQLAlchemy, que se pasa a cada función CRUD para interactuar con la base de datos.
*   **`app.models`:** Contiene las definiciones de los modelos SQLAlchemy (`Prompt`, `Tool`) que se están creando, leyendo, actualizando o eliminando.
*   **`app.schemas`:** Contiene los esquemas Pydantic (`PromptCreate`, `ToolUpdate`, etc.) que se utilizan para la validación de datos de entrada y la serialización de datos de salida en algunos contextos (aunque las funciones CRUD suelen devolver instancias de modelos).
