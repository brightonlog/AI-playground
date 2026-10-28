import pytest

from app.sources.youtube import parse_video_id

VID = "dQw4w9WgXcQ"


@pytest.mark.parametrize(
    "url",
    [
        f"https://www.youtube.com/watch?v={VID}",
        f"https://youtube.com/watch?v={VID}&t=30s",
        f"https://m.youtube.com/watch?v={VID}",
        f"https://youtu.be/{VID}?si=abc",
        f"https://www.youtube.com/shorts/{VID}",
        f"https://www.youtube.com/live/{VID}",
        f"  https://WWW.YOUTUBE.COM/watch?v={VID}  ",
    ],
)
def test_accepts(url):
    assert parse_video_id(url) == VID


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        f"https://evil.com/watch?v={VID}",
        f"https://youtube.com.evil.com/watch?v={VID}",
        f"javascript:alert(1)//youtube.com/watch?v={VID}",
        f"file:///watch?v={VID}",
        "https://www.youtube.com/watch?v=short",
        "https://www.youtube.com/channel/UC1234567890",
        "https://www.youtube.com/playlist?list=PL123",
    ],
)
def test_rejects(url):
    assert parse_video_id(url) is None
