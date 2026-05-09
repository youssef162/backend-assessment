from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=False)
AUTH = {"x-api-key": "dev-api-key-2026"}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
def test_health_no_auth_required():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def test_missing_api_key_returns_401():
    res = client.get("/candidates")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_wrong_api_key_returns_401():
    res = client.get("/candidates", headers={"x-api-key": "totally-wrong"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


# ---------------------------------------------------------------------------
# GET /candidates — list, filter, sort, paginate
# ---------------------------------------------------------------------------
def test_list_returns_paginated_results():
    res = client.get("/candidates", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body["data"], list)
    meta = body["meta"]
    assert meta["page"] == 1
    assert meta["pageSize"] == 12
    assert meta["total"] >= 30
    assert meta["totalPages"] >= 3


def test_list_items_have_required_fields():
    res = client.get("/candidates", headers=AUTH)
    item = res.json()["data"][0]
    required = [
        "id", "fullName", "headline", "location", "yearsOfExperience",
        "skills", "availability", "updatedAt", "status", "score",
        "shortlisted", "rejected",
    ]
    for field in required:
        assert field in item, f"Missing field: {field}"


def test_filter_by_skill_exact_case_insensitive():
    res = client.get("/candidates?skill=TypeScript", headers=AUTH)
    assert res.status_code == 200
    assert len(res.json()["data"]) > 0
    for c in res.json()["data"]:
        assert any(s.lower() == "typescript" for s in c["skills"])


def test_full_text_search_matches_name():
    res = client.get("/candidates?q=Lina", headers=AUTH)
    assert res.status_code == 200
    assert any("Lina" in c["fullName"] for c in res.json()["data"])


def test_full_text_search_matches_skill():
    res = client.get("/candidates?q=Storybook", headers=AUTH)
    assert res.status_code == 200
    assert len(res.json()["data"]) > 0


def test_filter_min_exp_max_exp():
    res = client.get("/candidates?minExp=5&maxExp=6", headers=AUTH)
    assert res.status_code == 200
    for c in res.json()["data"]:
        assert 5 <= c["yearsOfExperience"] <= 6, f"{c['id']} has {c['yearsOfExperience']} years"


def test_filter_by_status_case_insensitive():
    res = client.get("/candidates?status=Interviewing", headers=AUTH)
    assert res.status_code == 200
    assert len(res.json()["data"]) > 0
    for c in res.json()["data"]:
        assert c["status"].lower() == "interviewing"


def test_filter_by_availability():
    res = client.get("/candidates?availability=Immediate", headers=AUTH)
    assert res.status_code == 200
    assert len(res.json()["data"]) > 0
    for c in res.json()["data"]:
        assert c["availability"].lower() == "immediate"


def test_filter_by_location_partial_match():
    res = client.get("/candidates?location=Cairo", headers=AUTH)
    assert res.status_code == 200
    assert len(res.json()["data"]) > 0
    for c in res.json()["data"]:
        assert "cairo" in c["location"].lower()


def test_pagination_page_size_respected():
    res = client.get("/candidates?page=1&pageSize=5", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert len(body["data"]) == 5
    assert body["meta"]["page"] == 1
    assert body["meta"]["pageSize"] == 5


def test_page_2_is_disjoint_from_page_1():
    p1_ids = {c["id"] for c in client.get("/candidates?page=1&pageSize=5", headers=AUTH).json()["data"]}
    p2_ids = {c["id"] for c in client.get("/candidates?page=2&pageSize=5", headers=AUTH).json()["data"]}
    assert len(p1_ids & p2_ids) == 0


def test_page_size_over_50_rejected():
    res = client.get("/candidates?pageSize=100", headers=AUTH)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_sort_field_rejected():
    res = client.get("/candidates?sort=fullName", headers=AUTH)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_sort_by_score_descending():
    res = client.get("/candidates?sort=score&order=desc&pageSize=30", headers=AUTH)
    assert res.status_code == 200
    scores = [c["score"] for c in res.json()["data"]]
    assert scores == sorted(scores, reverse=True), "Scores not in descending order"


def test_sort_by_yoe_ascending():
    res = client.get("/candidates?sort=yearsOfExperience&order=asc&pageSize=30", headers=AUTH)
    assert res.status_code == 200
    yoe = [c["yearsOfExperience"] for c in res.json()["data"]]
    assert yoe == sorted(yoe), "yearsOfExperience not in ascending order"


def test_sort_is_stable_deterministic():
    r1 = client.get("/candidates?pageSize=30", headers=AUTH).json()["data"]
    r2 = client.get("/candidates?pageSize=30", headers=AUTH).json()["data"]
    assert [c["id"] for c in r1] == [c["id"] for c in r2]


# ---------------------------------------------------------------------------
# GET /candidates/:id
# ---------------------------------------------------------------------------
def test_get_by_id_returns_full_profile():
    res = client.get("/candidates/c-001", headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["id"] == "c-001"
    assert body["fullName"] == "Lina Hassan"
    assert isinstance(body["auditLog"], list)
    assert isinstance(body["shortlisted"], bool)
    assert isinstance(body["rejected"], bool)
    assert "experience" in body
    assert "education" in body


def test_get_by_id_404_for_unknown():
    res = client.get("/candidates/c-999", headers=AUTH)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# PATCH /candidates/:id
# ---------------------------------------------------------------------------
def test_patch_status_updates_and_appends_audit():
    res = client.patch("/candidates/c-002", json={"status": "Interviewing"}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "Interviewing"
    entry = next((e for e in body["auditLog"] if e["action"] == "status_changed"), None)
    assert entry is not None, "Expected a status_changed audit entry"
    assert entry["to"] == "Interviewing"
    assert "from" in entry
    assert entry["at"]


def test_patch_shortlisted_appends_audit():
    res = client.patch("/candidates/c-003", json={"shortlisted": True}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["shortlisted"] is True
    entry = next((e for e in body["auditLog"] if e["action"] == "shortlisted_changed"), None)
    assert entry is not None
    assert entry["from"] is False
    assert entry["to"] is True


def test_patch_rejected_appends_audit():
    res = client.patch("/candidates/c-004", json={"rejected": True}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["rejected"] is True
    assert any(e["action"] == "rejected_changed" for e in body["auditLog"])


def test_patch_multiple_fields_single_request():
    res = client.patch("/candidates/c-005", json={"shortlisted": True, "status": "Hired"}, headers=AUTH)
    assert res.status_code == 200
    body = res.json()
    assert body["shortlisted"] is True
    assert body["status"] == "Hired"
    actions = [e["action"] for e in body["auditLog"]]
    assert "shortlisted_changed" in actions
    assert "status_changed" in actions


def test_patch_updates_updated_at_to_today():
    today = date.today().isoformat()
    res = client.patch("/candidates/c-006", json={"shortlisted": True}, headers=AUTH)
    assert res.status_code == 200
    assert res.json()["updatedAt"] == today


def test_patch_no_audit_event_when_value_unchanged():
    client.patch("/candidates/c-007", json={"shortlisted": True}, headers=AUTH)
    log_len = len(client.get("/candidates/c-007", headers=AUTH).json()["auditLog"])
    # Patch with same value — must not add another entry
    client.patch("/candidates/c-007", json={"shortlisted": True}, headers=AUTH)
    new_log_len = len(client.get("/candidates/c-007", headers=AUTH).json()["auditLog"])
    assert new_log_len == log_len


def test_patch_rejects_unknown_fields():
    res = client.patch("/candidates/c-001", json={"fullName": "Injected"}, headers=AUTH)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_rejects_empty_body():
    res = client.patch("/candidates/c-001", json={}, headers=AUTH)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_patch_404_for_unknown_id():
    res = client.patch("/candidates/c-999", json={"status": "Hired"}, headers=AUTH)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /candidates/:id/related
# ---------------------------------------------------------------------------
def test_related_returns_5_to_10_results():
    res = client.get("/candidates/c-001/related", headers=AUTH)
    assert res.status_code == 200
    data = res.json()["data"]
    assert 5 <= len(data) <= 10, f"Expected 5-10 results, got {len(data)}"


def test_related_excludes_target_candidate():
    res = client.get("/candidates/c-001/related", headers=AUTH)
    assert res.status_code == 200
    ids = [c["id"] for c in res.json()["data"]]
    assert "c-001" not in ids


def test_related_each_result_has_relatedness_score():
    res = client.get("/candidates/c-001/related", headers=AUTH)
    assert res.status_code == 200
    for c in res.json()["data"]:
        assert isinstance(c["relatednessScore"], int), f"{c['id']} missing relatednessScore"


def test_related_ordered_by_score_desc():
    res = client.get("/candidates/c-001/related", headers=AUTH)
    assert res.status_code == 200
    scores = [c["relatednessScore"] for c in res.json()["data"]]
    assert scores == sorted(scores, reverse=True), "relatednessScore not descending"


def test_related_404_for_unknown_id():
    res = client.get("/candidates/c-999/related", headers=AUTH)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "NOT_FOUND"
