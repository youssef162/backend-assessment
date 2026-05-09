import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.repo.candidates import seed
from app.routers import candidates as candidates_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    yield


app = FastAPI(
    title="Recruitment API",
    description="Backend service for the Recruitment Platform assessment",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — allow common local dev origins; override via CORS_ORIGINS env var
# ---------------------------------------------------------------------------
_raw_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://localhost:4173",
)
allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key"],
)


# ---------------------------------------------------------------------------
# Request logging: method, path, status, latency
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    level = "ERROR" if response.status_code >= 500 else "WARN" if response.status_code >= 400 else "INFO"
    print(f"[{level}] {request.method} {request.url.path} {response.status_code} {ms:.1f}ms", flush=True)
    return response


# ---------------------------------------------------------------------------
# Exception handlers — produce a consistent { "error": { ... } } envelope
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors(),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict):
        content = {"error": detail}
    else:
        content = {"error": {"code": "HTTP_ERROR", "message": str(detail), "details": []}}
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Unhandled {type(exc).__name__}: {exc} — {request.method} {request.url.path}", flush=True)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred", "details": []}},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(candidates_router.router, prefix="/candidates", tags=["candidates"])
