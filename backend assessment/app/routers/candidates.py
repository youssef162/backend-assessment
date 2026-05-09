from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.dependencies import require_api_key
from app.models import CandidatePatch
from app.services import candidates as service

router = APIRouter(dependencies=[Depends(require_api_key)])


def _not_found(candidate_id: str):
    raise HTTPException(
        status_code=404,
        detail={
            "code": "NOT_FOUND",
            "message": f"Candidate '{candidate_id}' not found",
            "details": [],
        },
    )


@router.get("/")
def list_candidates(
    q: Optional[str] = Query(None, description="Full-text search: fullName, headline, skills"),
    location: Optional[str] = Query(None, description="Partial location match"),
    skill: Optional[str] = Query(None, description="Exact skill match"),
    status: Optional[str] = Query(None, description="Exact status match"),
    availability: Optional[str] = Query(None, description="Exact availability match"),
    min_exp: Optional[int] = Query(None, alias="minExp", ge=0, description="Min years of experience"),
    max_exp: Optional[int] = Query(None, alias="maxExp", ge=0, description="Max years of experience"),
    sort: Literal["updatedAt", "score", "yearsOfExperience"] = Query("updatedAt"),
    order: Literal["asc", "desc"] = Query("desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, alias="pageSize", ge=1, le=50),
):
    return service.search(
        q=q,
        location=location,
        skill=skill,
        status=status,
        availability=availability,
        min_exp=min_exp,
        max_exp=max_exp,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )


@router.get("/{candidate_id}/related")
def get_related(candidate_id: str):
    result = service.get_related(candidate_id)
    if result is None:
        _not_found(candidate_id)
    return {"data": result}


@router.get("/{candidate_id}")
def get_candidate(candidate_id: str):
    candidate = service.get_by_id(candidate_id)
    if candidate is None:
        _not_found(candidate_id)
    return candidate


@router.patch("/{candidate_id}")
def update_candidate(candidate_id: str, body: CandidatePatch):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": "Request body must include at least one field to update",
                "details": [],
            },
        )
    result = service.patch(candidate_id, updates)
    if result is None:
        _not_found(candidate_id)
    return result
