"""Request bodies. Validation failures become the published 400, never a Pydantic dump."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Format = Literal["jpg", "png", "webp"]


class UrlRequest(BaseModel):
    url: str = Field(min_length=3, max_length=2048)

    @field_validator("url")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()


class AnalyzeRequest(UrlRequest):
    sizeId: str = "hd"
    includeAI: bool = True


class CompareRequest(BaseModel):
    urls: list[str] = Field(min_length=2, max_length=4)
    includeAI: bool = False

    @field_validator("urls")
    @classmethod
    def _clean(cls, value: list[str]) -> list[str]:
        cleaned = [u.strip() for u in value if u and u.strip()]
        if len(cleaned) < 2:
            raise ValueError("Paste at least two links to compare")
        return cleaned


class ChannelRequest(UrlRequest):
    limit: int = Field(default=24, ge=1, le=24)


class DownloadRequest(UrlRequest):
    sizeId: str = "hd"
    format: Format = "jpg"


class ZipItem(BaseModel):
    sizeId: str
    format: Format = "jpg"


class ZipRequest(UrlRequest):
    items: list[ZipItem] = Field(min_length=1, max_length=24)
