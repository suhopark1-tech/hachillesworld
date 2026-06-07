"""pytest 전역 픽스처 — 테스트 환경 공통 설정."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _use_memory_storage(monkeypatch: pytest.MonkeyPatch) -> None:
    """모든 테스트에서 인메모리 스토리지를 강제 사용.

    API 서버가 TestClient로 실행될 때 SQLite 파일이 생성되지 않도록 한다.
    test_storage.py는 repository를 직접 생성하므로 이 픽스처의 영향을 받지 않는다.
    """
    monkeypatch.setenv("HAW_STORAGE", "memory")
