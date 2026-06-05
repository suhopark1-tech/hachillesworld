"""HAchillesWorld FastAPI 서버."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hachillesworld.api.routers import group, operate, scan, study
from hachillesworld.api.state import AppState

_API_KEY: str = os.getenv("HAW_API_KEY", "dev-key-insecure")
_security = HTTPBearer(auto_error=False)


def _verify_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> str:
    if credentials is None or credentials.credentials != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return credentials.credentials


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.store = AppState()
    yield


app = FastAPI(
    title="HAchillesWorld API",
    version="1.0.0",
    description="AI 에이전트 World Model 품질 진단 REST API",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_auth = [Depends(_verify_key)]

app.include_router(scan.router, prefix="/v1", dependencies=_auth)
app.include_router(operate.router, prefix="/v1", dependencies=_auth)
app.include_router(study.router, prefix="/v1", dependencies=_auth)
app.include_router(group.router, prefix="/v1", dependencies=_auth)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """서버 헬스체크."""
    return {"status": "ok", "version": "1.0.0"}
