from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    OPENAI_API_KEY: str = "your_openai_api_key_here"
    GEMINI_API_KEY: str = "your_gemini_api_key_here"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    DEFAULT_AI_MODEL: str = "openai"
    WEB_UI_USERNAME: str = "admin"
    WEB_UI_PASSWORD: str = "password"
    SECRET_KEY: str = "a_very_secret_key_for_jwt_or_sessions"
    ASTERISK_ARI_URL: str = "http://localhost:8088"
    ASTERISK_ARI_USERNAME: str = "asterisk"
    ASTERISK_ARI_PASSWORD: str = "asterisk"
    ASTERISK_APP_NAME: str = "ai_ari_app"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
