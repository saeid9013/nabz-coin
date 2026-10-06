from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from datetime import timezone


class Coin(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    id: int = Field(gt=0)
    rank: int = Field(gt=0)
    name: str
    symbol: str
    price: float = Field(ge=0)
    change_24h: float
    volume_24h: float = Field(ge=0)
    market_cap: float = Field(ge=0)
    logo_url: str | None = None


class MarketResponse(BaseModel):
    mode: Literal['demo', 'live']
    fetched_at: datetime
    freshness: Literal['fresh', 'stale', 'demo']
    scope: str = 'top_100'
    items: list[Coin]
    total: int


class CoinResponse(BaseModel):
    mode: Literal['demo', 'live']
    fetched_at: datetime
    freshness: Literal['fresh', 'stale', 'demo']
    coin: Coin


class Point(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    time: datetime
    price: float = Field(ge=0)
    @field_validator('time')
    @classmethod
    def utc_time(cls, value):
        if value.tzinfo is None:
            raise ValueError('Chart timestamps require timezone')
        return value.astimezone(timezone.utc)


class ChartResponse(BaseModel):
    mode: Literal['demo', 'live']
    fetched_at: datetime | None = None
    freshness: str
    range: Literal['1d', '7d', '30d']
    points: list[Point]
    source: Literal['demo', 'collected', 'cmc_history'] = 'collected'


class ArticleResponse(BaseModel):
    id: str
    url: HttpUrl
    publisher: str
    published_at: datetime
    coin_ids: list[int]
    demo: bool
    title_fa: str | None = None
    summary_fa: str | None = None
    original_fa: bool = False
    translation_status: str


class NewsResponse(BaseModel):
    mode: Literal['demo', 'live']
    items: list[ArticleResponse]
    next_cursor: str | None = None
    fetched_at: datetime | None = None
    freshness: str = 'unavailable'
