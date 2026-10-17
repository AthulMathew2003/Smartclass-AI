from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import List, Union


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartClass AI"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+psycopg://", 1)
            elif v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    # Security & JWT
    SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS Origins (accepts comma-separated string or list)
    BACKEND_CORS_ORIGINS: Union[str, List[str]] = "http://localhost:3000,https://smartclass-ai-1lek.onrender.com"

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip().rstrip("/") for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return [origin.strip().rstrip("/") for origin in v if isinstance(origin, str) and origin.strip()]
        return v

    # App URLs
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = ""

    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = ""

    # AWS S3 Settings
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = ""
    ASSIGNMENT_ATTACHMENT_MAX_SIZE_MB: int = 25
    ASSIGNMENT_MAX_ATTACHMENTS_COUNT: int = 10

    # Subject Course Materials limits (in MB)
    MATERIAL_MAX_DOC_SIZE_MB: int = 50
    MATERIAL_MAX_IMAGE_SIZE_MB: int = 10
    MATERIAL_MAX_VIDEO_SIZE_MB: int = 500
    MATERIAL_MAX_ZIP_SIZE_MB: int = 100

    # Google Gemini & RAG Settings
    GEMINI_API_KEY: str = ""
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_GENERATION_MODEL: str = "gemini-3.6-flash"

    # ChromaDB Settings
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "smartclass_materials"

    # RAG Chunking & Search Settings
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_DEFAULT_SEARCH_TOP_K: int = 5
    RAG_MAX_SEARCH_TOP_K: int = 20

    # AI Tutor Settings
    AI_TUTOR_MAX_HISTORY_MESSAGES: int = 10
    AI_TUTOR_MAX_CONTEXT_CHUNKS: int = 5
    AI_TUTOR_TEMPERATURE: float = 0.3
    AI_TUTOR_MAX_OUTPUT_TOKENS: int = 2048

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
