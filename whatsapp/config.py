"""Configuration for the standalone WhatsApp webhook."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    meta_access_token: str
    meta_phone_number_id: str
    webhook_verify_token: str
    meta_app_secret: str = ""
    meta_api_version: str = "v23.0"

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()  # type: ignore[call-arg]
