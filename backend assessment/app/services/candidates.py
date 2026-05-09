import functools
from datetime import date, datetime, timezone
from typing import Optional

from app.repo import candidates as repo


def _sort_key(sort_field: str, descending: bool):
    """cmp_to_key comparator: sort by sort_field (asc/desc), tie-break by id ascending."""
    def compare(a, b):
        av = a[sort_field]
        bv = b[sort_field]
        if av < bv:
            return 1 if descending else -1
        if av > bv:
            return -1 if descending else 1
        if a["id"] < b["id"]:
            return -1
        if a["id"] > b["id"]:
            return 1
        return 0
    return functools.cmp_to_key(compare)


def search(
    *,
    q: Optional[str],
    location: Optional[str],
    skill: Optional[str],
    status: Optional[str],
    availability: Optional[str],
    min_exp: Optional[int],
    max_exp: Optional[int],
    sort: str,
    order: str,
    page: int,
    page_size: int,
) -> dict:
    candidates = list(repo.find_all())

    if q:
        lower = q.lower()
        candidates = [
            c for c in candidates
            if lower in c["fullName"].lower()
            or lower in c["headline"].lower()
            or any(lower in s.lower() for s in c["skills"])
        ]

    if location:
        lower = location.lower()
        candidates = [c for c in candidates if lower in c["location"].lower()]

    if skill:
        lower = skill.lower()
        candidates = [c for c in candidates if any(s.lower() == lower for s in c["skills"])]

    if status:
        lower = status.lower()
        candidates = [c for c in candidates if c["status"].lower() == lower]

    if availability:
        lower = availability.lower()
        candidates = [c for c in candidates if c["availability"].lower() == lower]

    if min_exp is not None:
        candidates = [c for c in candidates if c["yearsOfExperience"] >= min_exp]

    if max_exp is not None:
        candidates = [c for c in candidates if c["yearsOfExperience"] <= max_exp]

    candidates = sorted(candidates, key=_sort_key(sort, order == "desc"))

    total = len(candidates)
    total_pages = max(1, -(-total // page_size))  # ceiling division without math.ceil
    start = (page - 1) * page_size
    page_data = candidates[start: start + page_size]

    return {
        "data": [_to_list_shape(c) for c in page_data],
        "meta": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": total_pages,
        },
    }


def get_by_id(candidate_id: str) -> Optional[dict]:
    return repo.find_by_id(candidate_id)


def patch(candidate_id: str, updates: dict) -> Optional[dict]:
    candidate = repo.find_by_id(candidate_id)
    if candidate is None:
        return None

    now = datetime.now(timezone.utc).isoformat()
    audit_events = []

    if "status" in updates and updates["status"] != candidate["status"]:
        audit_events.append({
            "at": now,
            "action": "status_changed",
            "from": candidate["status"],
            "to": updates["status"],
        })

    if "shortlisted" in updates and updates["shortlisted"] != candidate["shortlisted"]:
        audit_events.append({
            "at": now,
            "action": "shortlisted_changed",
            "from": candidate["shortlisted"],
            "to": updates["shortlisted"],
        })

    if "rejected" in updates and updates["rejected"] != candidate["rejected"]:
        audit_events.append({
            "at": now,
            "action": "rejected_changed",
            "from": candidate["rejected"],
            "to": updates["rejected"],
        })

    changes = {
        **updates,
        "updatedAt": date.today().isoformat(),
        "auditLog": candidate["auditLog"] + audit_events,
    }

    return repo.update(candidate_id, changes)


def get_related(candidate_id: str) -> Optional[list]:
    candidate = repo.find_by_id(candidate_id)
    if candidate is None:
        return None

    scored = []
    for c in repo.find_all():
        if c["id"] == candidate_id:
            continue
        score = 0
        shared = [s for s in c["skills"] if s in candidate["skills"]]
        score += len(shared) * 3
        if c["location"] == candidate["location"]:
            score += 2
        if abs(c["yearsOfExperience"] - candidate["yearsOfExperience"]) <= 2:
            score += 1
        scored.append((c, score))

    scored.sort(key=lambda x: (-x[1], x[0]["id"]))

    return [
        {**_to_list_shape(c), "relatednessScore": score}
        for c, score in scored[:10]
    ]


def _to_list_shape(c: dict) -> dict:
    return {
        "id": c["id"],
        "fullName": c["fullName"],
        "headline": c["headline"],
        "location": c["location"],
        "yearsOfExperience": c["yearsOfExperience"],
        "skills": c["skills"],
        "availability": c["availability"],
        "updatedAt": c["updatedAt"],
        "status": c["status"],
        "score": c["score"],
        "shortlisted": c["shortlisted"],
        "rejected": c["rejected"],
    }
