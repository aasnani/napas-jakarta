from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Measurement:
    station_id: str
    station_name: str
    district: str
    observed_at: datetime
    pollutant: str
    concentration: float | None
    concentration_unit: str
    ispu_value: int
    ispu_category: str
    source: str
    averaging_period: str | None = None
    quality_flag: str | None = None
    fetched_at: datetime | None = None


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    publisher: str
    source_url: str
    section: str
    text: str
    # Stable provenance metadata.  Defaults keep compatibility with the
    # original dependency-light callers that construct Document directly.
    source_id: str = ""
    heading_path: str = ""
    page: int | None = None
    article_or_clause: str | None = None
    paragraph: str | None = None
    language: str = "en"
    jurisdiction: str = ""
    status: str = ""
    effective_date: str | None = None
    checksum: str = ""
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class SearchResult:
    document: Document
    score: float
    rank: int
    method: str
