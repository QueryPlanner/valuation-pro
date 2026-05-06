from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FilingSource(str, Enum):
    INTEGRATED = "integrated"
    TRADITIONAL = "traditional"


class FilingMetadata(BaseModel):
    date: datetime
    url: str
    type: str
    source: FilingSource
    is_consolidated: bool

    class Config:
        arbitrary_types_allowed = True


class TargetFilings(BaseModel):
    fraction_of_year: float = Field(..., ge=0.0, le=1.0)
    current_date: str
    current_ytd: Optional[FilingMetadata] = None
    latest_bs_cf: Optional[FilingMetadata] = None
    annual: Optional[FilingMetadata] = None
    prior_ytd: Optional[FilingMetadata] = None


class DownloadedFile(BaseModel):
    date: str
    path: str
    original_url: str
    parsed_json_path: Optional[str] = None


class ValuationMetadata(BaseModel):
    symbol: str
    extraction_date: str
    fraction_of_year: float
    files: dict[str, DownloadedFile]
