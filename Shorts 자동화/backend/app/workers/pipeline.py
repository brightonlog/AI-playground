"""Analysis stages. Each step skips when its output file exists, so a rerun resumes
from the step that failed (spec 2: retry from the failed stage)."""

from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import JobError
from app.db.models import Analysis, utcnow
from app.media.waveform import build_waveform
from app.services import events
from app.sources import youtube
from app.storage import local
from app.transcript.sentences import group_sentences, tokens_from_json3


def stage_start(mode: str, stage: str | None) -> float:
    """Overall progress at the start of `stage` (sum of earlier stage weights)."""
    done = 0.0
    for name, weight in get_settings().analysis_stage_weights[mode].items():
        if name == stage:
            break
        done += weight
    return done


class Progress:
    def __init__(self, analysis: Analysis) -> None:
        self.analysis = analysis
        self.last = -1.0

    def update(self, stage: str, fraction: float) -> None:
        mode = self.analysis.progress_weight_mode
        weight = get_settings().analysis_stage_weights[mode].get(stage, 0.0)
        overall = stage_start(mode, stage) + weight * fraction
        if overall - self.last >= get_settings().progress_min_step or fraction >= 1:
            self.last = overall
            events.set_progress("analyses", self.analysis.id, stage, overall)


def _enter(db: Session, analysis: Analysis, progress: Progress, stage: str) -> None:
    analysis.status = analysis.stage = stage
    db.commit()
    progress.update(stage, 0.0)


def _fetch_captions(db: Session, analysis: Analysis, transcript_path: Path) -> None:
    captions = youtube.get_source().fetch_captions(analysis.url)
    if captions is None:
        analysis.progress_weight_mode = "whisper"
    else:
        sentences = group_sentences(tokens_from_json3(captions.json3))
        local.write_json(transcript_path, {"source": captions.kind, "sentences": sentences})
        analysis.progress_weight_mode = "captions"
        if captions.kind == "auto" and "auto_captions" not in analysis.warnings:
            analysis.warnings = [*analysis.warnings, "auto_captions"]
    db.commit()


def _fetch(db: Session, analysis: Analysis, progress: Progress, workdir: Path) -> None:
    transcript_path = workdir / "transcript.json"
    if not transcript_path.exists():
        _fetch_captions(db, analysis, transcript_path)
    audio_path = workdir / "audio.m4a"
    share = get_settings().fetch_audio_share
    if not audio_path.exists():
        youtube.get_source().download_audio(
            analysis.url, audio_path, lambda f: progress.update("fetching", f * share)
        )
    waveform_path = workdir / "waveform.json"
    if not waveform_path.exists():
        local.write_json(waveform_path, build_waveform(audio_path))
    progress.update("fetching", 1.0)


def run_pipeline(db: Session, analysis: Analysis) -> None:
    workdir = local.analysis_dir(analysis.id)
    progress = Progress(analysis)

    _enter(db, analysis, progress, "fetching")
    _fetch(db, analysis, progress, workdir)

    transcript_path = workdir / "transcript.json"
    if not transcript_path.exists():
        _enter(db, analysis, progress, "transcribing")
        raise JobError("no_captions", "자막이 없는 영상은 아직 지원하지 않습니다")
    analysis.transcript_source = local.read_json(transcript_path)["source"]

    _enter(db, analysis, progress, "analyzing")
    # M2: product extraction and recommendations.

    analysis.status = "ready"
    analysis.finished_at = utcnow()
    db.commit()
    progress.update("analyzing", 1.0)
    events.publish("analyses", analysis.id, "done", {"status": "ready"})
