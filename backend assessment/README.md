# Recruitment API

A REST backend service for a Recruitment Platform built with **Python / FastAPI**. Manages candidate profiles with searching, filtering, sorting, pagination, and recruiter actions tracked via an audit log.

---

## Tech Stack

| Concern       | Choice                                  |
|---------------|-----------------------------------------|
| Language      | Python 3.10+                            |
| Framework     | FastAPI                                 |
| Validation    | Pydantic v2 (built into FastAPI)        |
| Storage       | In-memory (seeded from `data/candidates.json`) |
| Server        | Uvicorn (ASGI)                          |
| Tests         | pytest + FastAPI TestClient (httpx)     |

---

## Setup & Run

```bash
# 1. Create and activate a virtual environment (recommended)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload --port 3000
```

The API is now available at `http://localhost:3000`.

Copy `.env.example` to `.env` to override defaults:
```
PORT=3000
API_KEY=dev-api-key-2026
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

To apply env vars before starting:
```bash
# Windows PowerShell
$env:API_KEY="my-secret-key"; uvicorn app.main:app --reload

# macOS/Linux
API_KEY=my-secret-key uvicorn app.main:app --reload
```

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Interactive API Docs

FastAPI auto-generates OpenAPI docs at:
- **Swagger UI** → `http://localhost:3000/docs`
- **ReDoc**       → `http://localhost:3000/redoc`

---

## Authentication

Every endpoint except `GET /health` requires the header:

```
x-api-key: dev-api-key-2026
```

Missing or wrong key → `401 UNAUTHORIZED`.

---

## Endpoint Reference

### `GET /health`
Public. Returns `{ "status": "ok" }`.

---

### `GET /candidates`
List candidates with search, filter, sort, and pagination.

**Query parameters:**

| Param          | Type    | Default      | Description                                              |
|----------------|---------|--------------|----------------------------------------------------------|
| `q`            | string  | —            | Full-text search across `fullName`, `headline`, `skills` |
| `location`     | string  | —            | Partial, case-insensitive location match                 |
| `skill`        | string  | —            | Exact, case-insensitive skill match                      |
| `status`       | string  | —            | Exact, case-insensitive status match                     |
| `availability` | string  | —            | Exact, case-insensitive availability match               |
| `minExp`       | integer | —            | Minimum years of experience (inclusive)                  |
| `maxExp`       | integer | —            | Maximum years of experience (inclusive)                  |
| `sort`         | string  | `updatedAt`  | `updatedAt` \| `score` \| `yearsOfExperience`            |
| `order`        | string  | `desc`       | `asc` \| `desc`                                          |
| `page`         | integer | `1`          | Page number (min 1)                                      |
| `pageSize`     | integer | `12`         | Results per page (1–50)                                  |

**Response:**
```json
{
  "data": [
    {
      "id": "c-001",
      "fullName": "Lina Hassan",
      "headline": "Frontend Engineer | React, TypeScript | Design Systems",
      "location": "Cairo, Egypt",
      "yearsOfExperience": 4,
      "skills": ["React", "TypeScript", "CSS"],
      "availability": "2 weeks",
      "updatedAt": "2026-02-03",
      "status": "Open to work",
      "score": 86,
      "shortlisted": false,
      "rejected": false
    }
  ],
  "meta": { "page": 1, "pageSize": 12, "total": 30, "totalPages": 3 }
}
```

---

### `GET /candidates/{id}`
Returns the full candidate profile including `experience`, `projects`, `notes`, `education`, `links`, `languages`, `summary`, `shortlisted`, `rejected`, and `auditLog`.

Returns `404` for unknown IDs.

---

### `PATCH /candidates/{id}`
Update one or more of: `status` (string), `shortlisted` (boolean), `rejected` (boolean).

- Unknown fields → `400 VALIDATION_ERROR` (Pydantic `extra="forbid"`)
- Empty body → `400 VALIDATION_ERROR`
- `updatedAt` is always updated to today's date
- An audit log entry is appended for each field that actually changed

**Request body:**
```json
{ "status": "Interviewing", "shortlisted": true }
```

**Response:** full updated candidate object.

---

### `GET /candidates/{id}/related`
Returns 5–10 related candidates.

**Response:**
```json
{
  "data": [
    {
      "id": "c-004",
      "relatednessScore": 14,
      "fullName": "Youssef Abdelrahman",
      ...
    }
  ]
}
```

---

## Example curl Calls

```bash
# Health check (no auth required)
curl http://localhost:3000/health

# List all candidates — first page, default sort
curl -H "x-api-key: dev-api-key-2026" http://localhost:3000/candidates

# Full-text search
curl -H "x-api-key: dev-api-key-2026" "http://localhost:3000/candidates?q=TypeScript"

# Filter by skill + location, sort by score
curl -H "x-api-key: dev-api-key-2026" \
  "http://localhost:3000/candidates?skill=React&location=Cairo&sort=score&order=desc"

# Filter by experience band + availability, paginate
curl -H "x-api-key: dev-api-key-2026" \
  "http://localhost:3000/candidates?minExp=4&maxExp=6&availability=Immediate&page=1&pageSize=5"

# Filter by status
curl -H "x-api-key: dev-api-key-2026" \
  "http://localhost:3000/candidates?status=Open+to+work&pageSize=20"

# Get a single candidate (full profile)
curl -H "x-api-key: dev-api-key-2026" http://localhost:3000/candidates/c-001

# Shortlist a candidate
curl -X PATCH http://localhost:3000/candidates/c-001 \
  -H "x-api-key: dev-api-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"shortlisted": true}'

# Change status
curl -X PATCH http://localhost:3000/candidates/c-002 \
  -H "x-api-key: dev-api-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"status": "Interviewing"}'

# Reject and update status in one request
curl -X PATCH http://localhost:3000/candidates/c-003 \
  -H "x-api-key: dev-api-key-2026" \
  -H "Content-Type: application/json" \
  -d '{"rejected": true, "status": "Rejected"}'

# Get related candidates
curl -H "x-api-key: dev-api-key-2026" http://localhost:3000/candidates/c-001/related
```

---

## Error Response Shape

All errors follow a consistent envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [...]
  }
}
```

| Code               | HTTP | Trigger                                              |
|--------------------|------|------------------------------------------------------|
| `UNAUTHORIZED`     | 401  | Missing or invalid `x-api-key`                      |
| `NOT_FOUND`        | 404  | Unknown candidate ID or route                        |
| `VALIDATION_ERROR` | 400  | Invalid query params, PATCH body, or empty body      |
| `INTERNAL_ERROR`   | 500  | Unhandled server exception                           |

---

## Filtering, Sorting & Pagination Behaviour

- **`q` search** — substring match (case-insensitive) against `fullName`, `headline`, and each element of `skills`.
- **`skill` filter** — exact, case-insensitive match against individual skill tokens (e.g. `?skill=react` matches `"React"`).
- **`location` filter** — substring match (e.g. `?location=cairo` matches `"Cairo, Egypt"`).
- **`status` / `availability`** — exact, case-insensitive equality.
- **`minExp` / `maxExp`** — inclusive bounds on `yearsOfExperience`.
- **Sort** — applied after all filters; ties broken by `id` (ascending, lexicographic) for deterministic ordering across pages.
- **`pageSize`** — capped at 50; validated by FastAPI before the handler runs.
- An out-of-range `page` returns an empty `data` array with an accurate `meta`.

---

## Related Candidates Scoring

`GET /candidates/{id}/related` scores every other candidate against the target using three signals, then returns the top 10 ordered by score descending (ties broken by `id`):

| Signal                                          | Points        |
|-------------------------------------------------|---------------|
| Each shared skill                               | +3 per skill  |
| Same `location` (exact string match)            | +2            |
| `yearsOfExperience` within ±2 years             | +1            |

**Example** — candidate c-001 has skills `["React", "TypeScript", "CSS", "Storybook", "Accessibility", "Jest"]` and 4 years experience in Cairo:
- A Cairo candidate with React + TypeScript + 5 years → 6 + 2 + 1 = **9 pts**
- An Alexandria candidate with React only + 4 years → 3 + 0 + 1 = **4 pts**

The `relatednessScore` is included in each returned object.

---

## CORS Configuration

CORS is enabled for `GET` and `PATCH` requests.  
Default allowed origins:

- `http://localhost:3000`
- `http://localhost:5173` (Vite dev)
- `http://localhost:4173` (Vite preview)

Override via the `CORS_ORIGINS` environment variable (comma-separated list).

---

## Project Architecture

```
app/
├── main.py          — FastAPI app, middleware, exception handlers, lifespan (seed)
├── dependencies.py  — x-api-key auth dependency
├── models.py        — Pydantic models (request bodies, response shapes)
├── repo/
│   └── candidates.py  — in-memory store: seed, find_all, find_by_id, update
├── services/
│   └── candidates.py  — business logic: search, patch, related scoring
└── routers/
    └── candidates.py  — FastAPI router: route declarations + HTTP in/out
```

Layering rule: routers call services; services call the repo; the repo has no HTTP knowledge.

---

## Trade-offs & What I'd Add Next

**Trade-offs made:**

- **In-memory storage** — zero infrastructure, resets on restart. Swapping to SQLite/Postgres requires only replacing `app/repo/candidates.py`.
- **API key auth** — sufficient for the assessment scope. Production would use JWT + refresh tokens with proper RBAC.
- **No caching layer** — in-memory reads are already sub-millisecond. With a real DB, a short-lived cache (e.g. Redis with 30 s TTL keyed on query string) on `GET /candidates` would reduce DB load.
- **Substring `q` search** — simple and correct. A production platform would use a dedicated search index (Elasticsearch, PostgreSQL `pg_trgm`) for relevance ranking and fuzzy matching.

**Next improvements:**

1. **Persistence** — SQLite via `aiosqlite` + `databases`, or PostgreSQL + `asyncpg`.
2. **Migrations** — Alembic for schema version control.
3. **Pagination** — cursor-based pagination for stable results under concurrent writes.
4. **Rate limiting** — `slowapi` (FastAPI-compatible `limits` wrapper) per IP to complement the API key.
5. **Structured logging** — `structlog` or `python-json-logger` for JSON-formatted logs easy to ship to a log aggregator.
6. **Docker** — `Dockerfile` + `docker-compose.yml` for a one-command reproducible environment.
7. **CI** — GitHub Actions running `pytest` on every push.

---

## Time Spent

~5 hours:
- 30 min — reading spec, planning architecture
- 2 h — core implementation (repo → service → router → middleware)
- 1 h — validation, error handling, audit log, CORS, auth
- 45 min — 25 test cases covering all endpoints and edge cases
- 45 min — README, cleanup, final review
