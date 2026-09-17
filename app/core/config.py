import os

from dotenv import load_dotenv

load_dotenv()

# model_config = SettingsConfigDict(env_file=".env")


class Settings:
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DATABASE: str = os.getenv("POSTGRES_DB", "")
    VALKEY_HOST: str = os.getenv("VALKEY_HOST", "")
    VALKEY_PORT: int = int(os.getenv("VALKEY_PORT", "6379"))
    VALKEY_PASSWORD: str = os.getenv("VALKEY_PASSWORD", "")
    MONGO_URL: str = os.getenv("MONGO_URL", "")
    CHROMA_URL: str = os.getenv("CHROMA_URL", "")
    MINIO_URL: str = os.getenv("MINIO_URL", "")
    NEO4J_URI: str = os.getenv("NEO4J_URI", "")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    SMTP_HOST: str = os.getenv("SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("SMTP_FROM", "")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()
