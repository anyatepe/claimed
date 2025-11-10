"""Application configuration using Pydantic BaseSettings."""
from typing import Literal, Optional
try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, model_validator
    PYDANTIC_V2 = True
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings, Field, validator
    PYDANTIC_V2 = False


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    ENV: str = Field(default="development", description="Environment name (development, staging, production)")
    
    # API Configuration
    API_KEYS: str = Field(default="", description="Comma-separated list of API keys")
    JWT_SECRET: str = Field(default="", description="JWT secret key for token signing")
    
    # Vector Backend Configuration
    VECTOR_BACKEND: Literal["pinecone", "chroma"] = Field(
        default="chroma",
        description="Vector database backend (pinecone or chroma)"
    )
    
    # Pinecone Configuration
    PINECONE_ENV: Optional[str] = Field(default=None, description="Pinecone environment")
    PINECONE_INDEX: Optional[str] = Field(default=None, description="Pinecone index name")
    
    # Chroma Configuration
    CHROMA_COLLECTION: str = Field(default="default", description="Chroma collection name")
    
    # Embedding Model Configuration
    EMBED_MODEL_NAME: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="Embedding model name"
    )
    
    # Redis Configuration
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    
    # Langflow Configuration
    LANGFLOW_BASE_URL: str = Field(
        default="http://localhost:7860",
        description="Langflow base URL"
    )
    
    # Storage Configuration
    STORAGE_BUCKET: Optional[str] = Field(
        default=None,
        description="S3 bucket path (optional, e.g., s3://bucket-name/path)"
    )
    
    # Chunking Configuration
    MAX_CHUNK_TOKENS: int = Field(
        default=512,
        ge=1,
        description="Maximum tokens per chunk"
    )
    CHUNK_OVERLAP: int = Field(
        default=50,
        ge=0,
        description="Number of tokens to overlap between chunks"
    )
    
    if PYDANTIC_V2:
        @model_validator(mode="after")
        def validate_vector_backend_config(self):
            """Validate vector backend configuration."""
            if self.VECTOR_BACKEND == "pinecone":
                if not self.PINECONE_ENV or not self.PINECONE_INDEX:
                    raise ValueError("PINECONE_ENV and PINECONE_INDEX are required when VECTOR_BACKEND is pinecone")
            return self
    else:
        # Fallback for older pydantic versions
        @validator("PINECONE_ENV", "PINECONE_INDEX", always=True)
        def validate_pinecone_config(cls, v, values):
            """Validate Pinecone configuration when VECTOR_BACKEND is pinecone."""
            if values.get("VECTOR_BACKEND") == "pinecone" and v is None:
                raise ValueError("PINECONE_ENV and PINECONE_INDEX are required when VECTOR_BACKEND is pinecone")
            return v
        
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()
