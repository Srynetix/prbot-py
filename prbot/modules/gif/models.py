from pydantic import BaseModel


class TenorGifObject(BaseModel):
    url: str


class TenorGifResult(BaseModel):
    media: list[dict[str, TenorGifObject]]


class TenorGifResponse(BaseModel):
    results: list[TenorGifResult]
