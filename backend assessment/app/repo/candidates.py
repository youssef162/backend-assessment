import json
import os
from typing import Optional

_store: list[dict] = []

_DATA_PATH = os.path.join(os.path.dirname(__file__), "../../data/candidates.json")


def seed() -> None:
    global _store
    with open(_DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    _store = [
        {**c, "shortlisted": False, "rejected": False, "auditLog": []}
        for c in raw
    ]


def find_all() -> list[dict]:
    return _store


def find_by_id(candidate_id: str) -> Optional[dict]:
    return next((c for c in _store if c["id"] == candidate_id), None)


def update(candidate_id: str, changes: dict) -> Optional[dict]:
    idx = next((i for i, c in enumerate(_store) if c["id"] == candidate_id), -1)
    if idx == -1:
        return None
    _store[idx] = {**_store[idx], **changes}
    return _store[idx]
