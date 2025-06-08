from sqlalchemy import Column, Integer, String, Text, JSON
from app.core.database import Base

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=True) # For JavaScript snippets or other configurations
