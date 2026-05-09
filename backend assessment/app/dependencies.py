import os
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("API_KEY", "dev-api-key-2026")

# auto_error=False so we control the 401 shape ourselves instead of getting a 403
_api_key_scheme = APIKeyHeader(name="x-api-key", auto_error=False)


def require_api_key(api_key: str = Security(_api_key_scheme)) -> None:
    if not api_key or api_key != API_KEY:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Missing or invalid x-api-key header",
                "details": [],
            },
        )
