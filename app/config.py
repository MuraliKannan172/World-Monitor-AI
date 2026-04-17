from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "qwen2.5:7b"
    ollama_num_ctx: int = 8192

    feed_interval_minutes: int = 7
    feed_jitter_seconds: int = 60

    db_path: str = "data/worldmonitor.db"
    gazetteer_path: str = "data/cities1000.txt"

    log_level: str = "INFO"


settings = Settings()
