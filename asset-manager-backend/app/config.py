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

    # Enable Banking (agrégation PSD2 — ex: Trade Republic, N26...)
    enablebanking_app_id: str = ""  # Application ID (= kid du JWT)
    enablebanking_base_url: str = "https://api.enablebanking.com"
    # Clé privée RSA : soit le contenu PEM inline (prod/docker), soit un chemin (dev local).
    # Le contenu inline est prioritaire sur le chemin s'il est renseigné.
    enablebanking_private_key: str = ""
    enablebanking_private_key_path: str = ""
    # URL de callback enregistrée sur le portail Enable Banking (doit matcher EXACTEMENT)
    # Sandbox/local : http://localhost:8000/connect/enablebanking/callback
    # Prod : https://patrimoine.dou-social.fr/api/v1/connect/enablebanking/callback
    enablebanking_redirect_url: str = "http://localhost:8000/connect/enablebanking/callback"
    # Session active obtenue via le flux de consentement (script scripts/enablebanking-connect.py).
    # En Phase 0, on la stocke ici ; en Phase 2 elle sera persistée en DB.
    enablebanking_session_id: str = ""

    # App
    log_level: str = "INFO"
    sync_on_startup: bool = True


settings = Settings()
