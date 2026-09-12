from pydantic_settings import BaseSettings, SettingsConfigDict

# BaseSettings de pydantic sirve para definir una clase y que te coja los mismos valores del archivo .env
class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

settings = Settings()