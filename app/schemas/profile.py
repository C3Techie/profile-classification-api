from pydantic import BaseModel, Field
from typing import List, Optional

class ProfileCreate(BaseModel):
    name: str = Field(...)

class ProfileData(BaseModel):
    id: str
    name: str
    gender: str
    gender_probability: float
    sample_size: int
    age: int
    age_group: str
    country_id: str
    country_probability: float
    created_at: str

class ProfileSummary(BaseModel):
    id: str
    name: str
    gender: str
    age: int
    age_group: str
    country_id: str

class ProfileResponse(BaseModel):
    model_config = {"exclude_none": True}
    status: str = "success"
    message: Optional[str] = None
    data: ProfileData

class ProfileListResponse(BaseModel):
    status: str = "success"
    count: int
    data: List[ProfileSummary]

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
