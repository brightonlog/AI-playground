"""Scoring model interface (spec 5.2). Stage 2 adds trained scorers behind the same shape."""

from typing import Protocol

from app.core.config import get_settings
from app.recommend.candidates import Candidate


class Scorer(Protocol):
    version: str

    def score(
        self, candidates: list[Candidate], signals: list[dict[str, float]]
    ) -> list[float]: ...


class RulesScorer:
    version = "rules-v1"

    def score(self, candidates: list[Candidate], signals: list[dict[str, float]]) -> list[float]:
        weights = get_settings().signal_weights
        return [round(sum(w * sig[k] for k, w in weights.items()), 4) for sig in signals]


_SCORERS: dict[str, type[Scorer]] = {RulesScorer.version: RulesScorer}


def get_scorer() -> Scorer:
    name = get_settings().scorer
    if name not in _SCORERS:
        raise ValueError(f"unknown SCORER: {name}")
    return _SCORERS[name]()
