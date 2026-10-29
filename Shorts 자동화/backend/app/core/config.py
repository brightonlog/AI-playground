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

    llm_timeout_sec: float = 120
    llm_max_retries: int = 2
    llm_max_tokens: int = 16000
    llm_description_max_chars: int = 1500
    keyword_base_strength: float = 0.2
    keyword_recommend_strength: float = 0.6
    # Share of the analyzing stage spent on LLM extraction; the rest is scoring.
    analyze_extract_share: float = 0.7

    # Candidates and scoring (spec 5). Lengths are seconds of the source video.
    candidate_min_sec: float = 30
    candidate_max_sec: float = 60
    candidate_pad_sec: float = 0.2
    candidate_max_gap_sentences: int = 1
    candidate_context_sentences: int = 1
    recommend_top_k: int = 3
    overlap_iou_max: float = 0.3
    signal_weights: dict[str, float] = {
        "product_specific": 0.30,
        "recommend_strength": 0.25,
        "usage": 0.15,
        "density": 0.10,
        "continuity": 0.10,
        "length_fit": 0.10,
    }
    product_specific_with_brand: float = 1.0
    product_specific_product_only: float = 0.6
    usage_ratio_scale: float = 2.0
    density_full_chars_per_sec: float = 7.0
    continuity_gap_sec: float = 1.0
    continuity_mixed_products_factor: float = 0.5
    length_fit_full: tuple[float, float] = (35, 55)
    length_fit_edge_score: float = 0.5
    tag_thresholds: dict[str, float] = {
        "usage_scene": 0.3,
        "strong_recommend": 0.7,
        "dense_speech": 0.7,
        "continuous": 0.8,
    }
    tags_max: int = 2

    waveform_peaks_per_sec: int = 10
    waveform_sample_rate: int = 8000

    # Shorts (spec 2, 7).
    short_stage_weights: dict[str, float] = {"downloading": 0.3, "preparing": 0.7}
    short_min_sec: float = 15
    short_max_sec: float = 60
    section_margin_sec: float = 1.0
    section_max_height: int = 1080
    # Share of the preparing stage per step ("copy" is title, narration and TTS).
    prepare_shares: dict[str, float] = {"words": 0.4, "crop": 0.2, "copy": 0.1, "preview": 0.3}

    # 9:16 crop (spec 6). Faces are sampled every interval on a downscaled frame.
    crop_aspect: float = 9 / 16
    crop_sample_sec: float = 0.5
    crop_detect_width: int = 320
    crop_min_confidence: float = 0.5
    crop_smooth_window: int = 5
    face_model_path: Path = ROOT_DIR / "assets" / "models" / "blaze_face_short_range.tflite"

    # Draft copy (spec 6 edit ops limits).
    title_max_chars: int = 30
    narration_max_chars: int = 40
    narration_max_count: int = 2
    default_style_preset: str = "title_pink"
    fake_tts_sec_per_char: float = 0.12
    fake_tts_min_sec: float = 0.8

    # Render (spec 6 렌더 규칙). Subtitle layout is in final-size pixels; preview scales it.
    trim_gap_sec: float = 0.15
    narration_duck_volume: float = 0.2
    subtitle_line_chars: int = 16
    subtitle_max_lines: int = 2
    render_preset: str = "veryfast"
    preview_size: tuple[int, int] = (540, 960)
    preview_crf: int = 28
    final_size: tuple[int, int] = (1080, 1920)
    final_crf: int = 20
    fonts_dir: Path = ROOT_DIR / "assets" / "fonts"

    templates_available: tuple[str, ...] = ("celeb_item",)
    list_default_limit: int = 20
    list_max_limit: int = 100

    @property
    def database_url(self) -> str:
        return f"sqlite:///{(self.data_dir / 'app.db').as_posix()}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
