from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# BaseSettings de pydantic sirve para definir una clase y que te coja los mismos valores del archivo .env
class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    admin_api_token: str = ""
    agent_api_token: str = ""

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
    )


# Instantiate settings once. Pylance may warn about the BaseSettings
# constructor signature; the precise runtime instantiation is correct so
# silence the `call-arg` type-checker complaint here.
settings: Settings = Settings()  # type: ignore[call-arg]
