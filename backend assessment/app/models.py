from typing import Any, Optional
from pydantic import BaseModel, ConfigDict


class CandidateListItem(BaseModel):
    id: str
    fullName: str
    headline: str
    location: str
    yearsOfExperience: int
    skills: list[str]
    availability: str
    updatedAt: str
    status: str
    score: int
    shortlisted: bool
    rejected: bool


class RelatedCandidate(CandidateListItem):
    relatednessScore: int


class PaginationMeta(BaseModel):
    page: int
    pageSize: int
    total: int
    totalPages: int


class CandidateListResponse(BaseModel):
    data: list[CandidateListItem]
    meta: PaginationMeta


class RelatedResponse(BaseModel):
    data: list[RelatedCandidate]


class CandidatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Optional[str] = None
    shortlisted: Optional[bool] = None
    rejected: Optional[bool] = None


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: list[Any] = []


class ErrorResponse(BaseModel):
    error: ErrorDetail
