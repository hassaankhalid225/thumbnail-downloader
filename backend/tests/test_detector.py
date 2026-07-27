"""Video-ID extraction and platform detection."""

from __future__ import annotations

import pytest

from services.detector import detect, extract_youtube_id, is_channel_url
from utils.errors import InvalidUrlError

ID = "dQw4w9WgXcQ"

VALID = [
    f"https://www.youtube.com/watch?v={ID}",
    f"https://youtube.com/watch?v={ID}",
    f"https://youtu.be/{ID}",
    f"https://youtu.be/{ID}?si=Xy1_ab-CD2",
    f"https://youtube.com/shorts/{ID}",
    f"https://www.youtube.com/shorts/{ID}?feature=share",
    f"https://www.youtube.com/embed/{ID}",
    f"https://www.youtube.com/embed/{ID}?start=30&autoplay=1",
    f"https://www.youtube.com/live/{ID}",
    f"https://www.youtube.com/v/{ID}",
    f"https://m.youtube.com/watch?v={ID}",
    f"https://m.youtube.com/watch?v={ID}&t=42s",
    f"https://music.youtube.com/watch?v={ID}&list=RDAMVM123",
    f"https://www.youtube-nocookie.com/embed/{ID}",
    f"https://www.youtube.com/watch?app=desktop&v={ID}&feature=youtu.be",
    f"http://youtube.com/watch?v={ID}",
]

INVALID = [
    "https://www.youtube.com/watch?v=tooshort",
    "https://www.youtube.com/watch?v=waaaaaaaaytoolong",
    "https://www.youtube.com/watch",
    "https://www.youtube.com/",
    "https://www.youtube.com/@somechannel",
    "https://example.com/watch?v=" + ID,
    "just some text",
    "",
    "ftp://youtube.com/watch?v=" + ID,
    "https://www.youtube.com/playlist?list=PL1234567890",
]


@pytest.mark.parametrize("url", VALID)
def test_valid_youtube_urls_yield_the_id(url: str) -> None:
    assert extract_youtube_id(url) == ID


@pytest.mark.parametrize("url", INVALID)
def test_malformed_urls_are_rejected_cleanly(url: str) -> None:
    assert extract_youtube_id(url) is None


def test_id_regex_does_not_accept_a_twelfth_character() -> None:
    # The classic loose-regex bug: matching 11 chars out of a 12-char token.
    assert extract_youtube_id(f"https://youtu.be/{ID}X") is None


def test_detect_classifies_platforms() -> None:
    assert detect(f"https://youtu.be/{ID}").platform == "youtube"
    assert detect("https://vimeo.com/76979871").platform == "vimeo"
    assert detect("https://vimeo.com/76979871").video_id == "76979871"
    assert detect("https://www.tiktok.com/@user/video/7212345678901234567").platform == "tiktok"
    assert detect("https://x.com/user/status/1").platform == "twitter"
    assert detect("https://www.dailymotion.com/video/x8abcde").video_id == "x8abcde"
    assert detect("https://some-blog.example/post").platform == "generic"


def test_detect_adds_a_scheme_when_the_user_pastes_a_bare_host() -> None:
    assert detect(f"youtube.com/watch?v={ID}").normalized_url.startswith("https://")


@pytest.mark.parametrize("bad", ["", "   ", "hello world", "not/a/url"])
def test_detect_raises_the_published_error(bad: str) -> None:
    with pytest.raises(InvalidUrlError):
        detect(bad)


def test_channel_urls_are_recognised() -> None:
    assert is_channel_url("https://www.youtube.com/@mkbhd")
    assert is_channel_url("https://www.youtube.com/channel/UCabc")
    assert is_channel_url("https://www.tiktok.com/@user")
    assert not is_channel_url(f"https://www.youtube.com/watch?v={ID}")
