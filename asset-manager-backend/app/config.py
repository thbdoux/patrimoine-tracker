from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://patrimoine:password@localhost:5432/patrimoine_db"

    # Powens
    powens_client_id: str = ""
    powens_client_secret: str = ""
    powens_domain: str = "sandbox.biapi.pro"
    powens_user_token: str = ""

    # Binance
    binance_api_key: str = ""
    binance_api_secret: str = ""
    binance_testnet: bool = True

    # App
    log_level: str = "INFO"
    sync_on_startup: bool = True


settings = Settings()
