from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List

# Pydantic models for Prompt
class PromptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["Greeting Prompt"])
    content: str = Field(..., examples=["Hello, how can I help you today?"])
    metadata: Optional[Dict[str, Any]] = Field(None, examples=[{"version": 1.0, "tags": ["customer_service"]}])

class PromptCreate(PromptBase):
    pass

class PromptUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    content: Optional[str] = Field(None)
    metadata: Optional[Dict[str, Any]] = None

class PromptInDB(PromptBase):
    id: int

    class Config:
        from_attributes = True # for Pydantic v2, replaces orm_mode = True

# Pydantic models for Tool
class ToolBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, examples=["WeatherAPI"])
    description: Optional[str] = Field(None, examples=["Fetches weather information for a given location."])
    parameters: Optional[Dict[str, Any]] = Field(None, examples=[{"type": "object", "properties": {"location": {"type": "string"}}, "required": ["location"]}])
    api_config: Optional[Dict[str, Any]] = Field(None, examples=[{"url": "https://api.weather.com/v1/current", "method": "GET", "headers": {"X-API-Key": "secret"}}])

class ToolCreate(ToolBase):
    pass

class ToolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    api_config: Optional[Dict[str, Any]] = None

class ToolInDB(ToolBase):
    id: int

    class Config:
        from_attributes = True
