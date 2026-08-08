import os


class Settings:
    POSTGRES_URL: str = os.getenv("POSTGRES_URL", "")
    VALKEY_URL: str = os.getenv("VALKEY_URL", "")
    MONGO_URL: str = os.getenv("MONGO_URL", "")
    ELASTIC_URL: str = os.getenv("ELASTIC_URL", "")
    INFLUX_URL: str = os.getenv("INFLUX_URL", "")
    CHROMA_URL: str = os.getenv("CHROMA_URL", "")
    SURREAL_URL: str = os.getenv("SURREAL_URL", "")
    MINIO_URL: str = os.getenv("MINIO_URL", "")
    NEO4J_URI: str = os.getenv("NEO4J_URI", "")
    NEO4J_USERNAME: str = os.getenv("NEO4J_USERNAME", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    ASTRA_DB_ID: str = os.getenv("ASTRA_DB_ID", "")
    ASTRA_DB_KEYSPACE: str = os.getenv("ASTRA_DB_KEYSPACE", "")


settings = Settings()
