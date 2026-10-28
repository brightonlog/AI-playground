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
    source_timeout_sec: float = 10
    task_visibility_timeout_sec: int = 6 * 3600
    progress_ttl_sec: int = 86400
    progress_min_step: float = 0.01
    sse_heartbeat_sec: float = 15
    max_retries: int = 3

    # Stage weights for overall progress (spec 2). Mode "captions" skips transcribing.
    analysis_stage_weights: dict[str, dict[str, float]] = {
        "captions": {"fetching": 0.4, "analyzing": 0.6},
        "whisper": {"fetching": 0.2, "transcribing": 0.5, "analyzing": 0.3},
    }
    # Share of the fetching stage spent downloading audio; the rest is waveform.
    fetch_audio_share: float = 0.9

    # Sentence building from caption tokens.
    captions_min_hangul_ratio: float = 0.3
    sentence_gap_sec: float = 1.0
    sentence_min_sec: float = 1.5
    sentence_max_sec: float = 15.0

    waveform_peaks_per_sec: int = 10
    waveform_sample_rate: int = 8000

    templates_available: tuple[str, ...] = ("celeb_item",)
    list_default_limit: int = 20
    list_max_limit: int = 100

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
