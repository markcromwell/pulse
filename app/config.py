from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "PULSE"
    version: str = "0.1.0"
    database_url: str = "sqlite:///./app.db"  # override via env for Postgres


settings = Settings()
