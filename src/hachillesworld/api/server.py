"""HAchillesWorld FastAPI 서버."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from hachillesworld.api.middleware import AuditMiddleware
from hachillesworld.api.routers import compliance, group, operate, scan, study
from hachillesworld.api.routers.operate import audit_router
from hachillesworld.api.state import AppState
from hachillesworld.audit.logger import AuditLogger

_API_KEY: str = os.getenv("HAW_API_KEY", "dev-key-insecure")
_ADMIN_KEY: str = os.getenv("HAW_ADMIN_KEY", "dev-admin-insecure")
_security = HTTPBearer(auto_error=False)


def _verify_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> str:
    if credentials is None or credentials.credentials != _API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return credentials.credentials


def _create_repository() -> object:
    """HAW_STORAGE 환경변수로 스토리지 백엔드를 선택한다.

    - memory : InMemoryRepository (테스트·개발, 재시작 시 소실)
    - sqlite  : SQLiteRepository  (로컬·기본값, 파일 영구 보존)
    - postgres: PostgreSQLRepository (프로덕션, HAW_DATABASE_URL 필요)
    """
    backend = os.getenv("HAW_STORAGE", "sqlite")
    if backend == "postgres":
        from hachillesworld.storage.postgres import PostgreSQLRepository

        return PostgreSQLRepository(dsn=os.getenv("HAW_DATABASE_URL"))
    if backend == "memory":
        from hachillesworld.storage.memory import InMemoryRepository

        return InMemoryRepository()
    # sqlite (기본)
    from hachillesworld.storage.sqlite import SQLiteRepository

    return SQLiteRepository(db_path=os.getenv("HAW_DB_PATH", "haw_data.db"))


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    repo = _create_repository()
    app.state.store = AppState(repository=repo)
    app.state.audit_logger = AuditLogger(repository=repo)
    yield
    if hasattr(repo, "close"):
        repo.close()


app = FastAPI(
    title="HAchillesWorld API",
    version="1.0.0",
    description="AI 에이전트 World Model 품질 진단 REST API",
    lifespan=_lifespan,
)

app.add_middleware(AuditMiddleware)
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
app.include_router(audit_router, prefix="/v1")  # admin 전용 — 자체 인증 처리
app.include_router(study.router, prefix="/v1", dependencies=_auth)
app.include_router(group.router, prefix="/v1", dependencies=_auth)
app.include_router(compliance.router, prefix="/v1", dependencies=_auth)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """서버 헬스체크."""
    return {"status": "ok", "version": "1.0.0"}
