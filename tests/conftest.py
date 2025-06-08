import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import sys
from pathlib import Path

# Add app directory to sys.path to allow direct imports for tests
# This might be needed if tests are run with `python -m pytest` from project root
# and `app` is not automatically discoverable. Poetry run pytest usually handles this.
APP_DIR = Path(__file__).resolve().parent.parent / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

# Now import app components
from main import app # Import app from app.main
from core.database import get_db as app_get_db # Import original get_db
from core.config import settings
from models import Base # Import Base from app.models (via app.models.__init__)

# Use a separate in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL_TEST = "sqlite:///:memory:" # In-memory SQLite

engine = create_engine(
    SQLALCHEMY_DATABASE_URL_TEST,
    connect_args={"check_same_thread": False}, # Required for SQLite
    poolclass=StaticPool, # Recommended for SQLite with TestClient
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override get_db dependency for testing
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Apply the override for the duration of tests
app.dependency_overrides[app_get_db] = override_get_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    # Create tables before any tests run
    Base.metadata.create_all(bind=engine)
    yield
    # Optional: Drop tables after all tests run if needed, but in-memory DB is ephemeral
    # Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="module")
def client():
    # The setup_test_database fixture ensures tables are created before client is used
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db_session():
    # Provides a database session for tests that need direct DB access
    # Ensures tables are created by setup_test_database fixture
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
