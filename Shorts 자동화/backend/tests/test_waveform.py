from array import array

import pytest

from app.media.waveform import build_waveform, peak
from tests.conftest import HAS_FFMPEG


def test_peak():
    assert peak(array("h", [0, 100, -16384, 50]).tobytes()) == 0.5
    assert peak(b"") == 0.0


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_build_waveform(tone):
    wave = build_waveform(tone)
    assert wave["peaks_per_sec"] == 10
    assert abs(wave["duration_sec"] - 2.0) < 0.1
    assert len(wave["peaks"]) in range(19, 23)
    assert max(wave["peaks"]) == 1.0
