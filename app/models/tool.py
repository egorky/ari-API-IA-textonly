from sqlalchemy import Column, Integer, String, Text, JSON
from app.core.database import Base

class Tool(Base):
    __tablename__ = "tools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(JSON, nullable=True) # Parameters for the API call (e.g., OpenAPI schema snippet)
    api_config = Column(JSON, nullable=True) # API endpoint, method, headers, etc.
