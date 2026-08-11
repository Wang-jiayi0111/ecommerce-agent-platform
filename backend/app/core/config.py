from dataclasses import dataclass
from os import getenv


@dataclass(frozen=True)
class Settings:
    app_name: str = "E-commerce Operations Intelligence Agent API"
    environment: str = getenv("APP_ENV", "local")
    database_url: str = getenv("DATABASE_URL", "sqlite:///./ecommerce_agent.db")
    redis_url: str = getenv("REDIS_URL", "redis://localhost:6379/0")
    qdrant_url: str = getenv("QDRANT_URL", "http://localhost:6333")
    object_storage_endpoint: str = getenv("MINIO_ENDPOINT", "localhost:9000")


settings = Settings()
