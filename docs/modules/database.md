# Módulo: app.core.database

**Archivo Original:** `app/core/database.py`

## Propósito General

Este módulo es responsable de toda la configuración y gestión de la conexión a la base de datos utilizando SQLAlchemy, el Object-Relational Mapper (ORM) de Python. Proporciona los componentes necesarios para que el resto de la aplicación interactúe con la base de datos de una manera estandarizada.

Sus funciones principales son:

*   **Configuración de la URL de la Base de Datos:**
    *   Lee la URL de la base de datos desde `settings.DATABASE_URL` (proveniente de `app.core.config`). Esto permite configurar fácilmente diferentes tipos de bases de datos (SQLite, PostgreSQL, etc.) a través de variables de entorno.
*   **Creación del Motor SQLAlchemy (`engine`):**
    *   Crea una instancia de `sqlalchemy.create_engine` utilizando la URL de la base de datos.
    *   Para SQLite, configura `connect_args={"check_same_thread": False}` para permitir su uso con FastAPI y múltiples hilos/tareas asíncronas.
    *   Este `engine` es el punto de entrada de bajo nivel para la comunicación con la base de datos.
*   **Creación de `SessionLocal`:**
    *   Define `SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)`.
    *   `SessionLocal` es una fábrica que crea nuevas instancias de `Session` de SQLAlchemy. Estas sesiones son las que se utilizan para realizar consultas y transacciones a la base de datos.
*   **Clase Base Declarativa (`Base`):**
    *   Define `Base = declarative_base()`.
    *   Esta `Base` es utilizada por los modelos de datos SQLAlchemy (ej. en `app/models/prompt.py` y `app/models/tool.py`) como la clase base de la cual heredan. Permite a SQLAlchemy descubrir y mapear estos modelos a tablas de base de datos.
*   **Función de Dependencia `get_db()`:**
    *   Define una función generadora `get_db()` que se utiliza como una dependencia de FastAPI (`Depends(get_db)`).
    *   Esta función gestiona el ciclo de vida de una sesión de base de datos por solicitud:
        *   Crea una nueva sesión (`SessionLocal()`).
        *   Proporciona (mediante `yield`) esta sesión a la ruta que la solicita.
        *   Asegura que la sesión se cierre (`db.close()`) después de que la solicitud haya terminado, incluso si ocurren errores.
    *   Esto promueve un patrón de una sesión por solicitud, que es una buena práctica para aplicaciones web.

## Dependencias Clave

*   **`sqlalchemy`:** La biblioteca principal para la interacción con bases de datos y el mapeo objeto-relacional. Específicamente, se utilizan:
    *   `create_engine`
    *   `orm.sessionmaker`
    *   `ext.declarative.declarative_base`
*   **`app.core.config.settings`:** Para obtener la `DATABASE_URL` que define a qué base de datos conectarse.
