from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # Required from M2 (LLM extraction). Optional until then so M0/M1 run without it.
    anthropic_api_key: SecretStr | None = None
    llm_model: str = "claude-haiku-5-5"
    tts_provider: str = "fake"
    whisper_model: str = "large-v3"
    whisper_device: str = "cuda"
    redis_url: str = "redis://localhost:6379/0"
    data_dir: Path = ROOT_DIR / "data"
    scorer: str = "rules-v1"
    max_active_jobs: int = 2
    max_source_sec: int = 7200

    health_check_timeout_sec: float = 0.5

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
