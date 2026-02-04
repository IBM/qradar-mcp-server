"""Application configuration."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # Database (SQLite for simplicity)
    database_url: str = "sqlite:///./ibm_mcp_client.db"
    
    # Default LLM settings
    default_llm_provider: str = "watsonx"
    
    # Watsonx
    watsonx_api_key: Optional[str] = None
    watsonx_project_id: Optional[str] = None
    watsonx_url: str = "https://us-south.ml.cloud.ibm.com"
    
    # OpenRouter
    openrouter_api_key: Optional[str] = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    # Anthropic
    anthropic_api_key: Optional[str] = None
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
