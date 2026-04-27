from pydantic import BaseModel, Field, field_serializer
from typing import List, Optional, Any
from datetime import datetime


class ProfileCreate(BaseModel):
    name: str = Field(..., min_length=1)


class ProfileData(BaseModel):
    id: str
    name: str
    gender: str
    gender_probability: float
    age: int
    age_group: str
    country_id: str
    country_name: str
    country_probability: float
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_serializer("created_at")
    def serialize_dt(self, dt: datetime, _info):
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


class ProfileResponse(BaseModel):
    model_config = {"exclude_none": True}
    status: str = "success"
    message: Optional[str] = None
    data: ProfileData


class PaginationLinks(BaseModel):
    self: str
    next: Optional[str] = None
    prev: Optional[str] = None


class ProfileListResponse(BaseModel):
    status: str = "success"
    page: int
    limit: int
    total: int
    total_pages: int
    links: PaginationLinks
    data: List[ProfileData]


class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
