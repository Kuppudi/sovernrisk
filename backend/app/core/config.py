from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://sovereign:local_dev_only@localhost:5432/sovereign_risk"
    )
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    world_bank_base_url: str = "https://api.worldbank.org/v2"
    raw_data_dir: Path = Path("data/raw")
    report_data_dir: Path = Path("data/reports")
    predictions_blob_url: str = ""
    predictions_file: str = ""
    scenario_model_file: str = ""
    scenario_model_sha256: str = ""
    scenario_snapshot_file: str = ""
    scenario_bundle_file: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_key: SecretStr = SecretStr("")
    frontend_dir: Path = Path(__file__).resolve().parents[3] / "frontend" / "dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()
