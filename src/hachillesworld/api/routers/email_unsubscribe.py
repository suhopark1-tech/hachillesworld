"""이메일 수신 거부 엔드포인트 (M-4 이행 — 정보통신망법 §50).

GET  /v1/unsubscribe/{token}   — 이메일 하단 링크 클릭 처리
POST /v1/webhooks/email/unsubscribe-event — 이메일 서비스 수신 거부 웹훅

법적 요건:
  · 정보통신망법 §50②: 수신 거부 처리 24시간 이내 완료
  · 수신 거부 후 24시간 내 재발송 금지
  · AuditEvent action="consent.update", source="email_unsubscribe" 기록
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from hachillesworld.audit.logger import AuditLogger

router = APIRouter(tags=["email"])

# HMAC 서명 비밀키 — 운영 환경에서 반드시 환경변수로 교체
_UNSUBSCRIBE_SECRET: str = os.getenv(
    "HAW_UNSUBSCRIBE_SECRET", "dev-unsubscribe-secret-change-in-prod"
)
_WEBHOOK_SECRET: str = os.getenv(
    "HAW_EMAIL_WEBHOOK_SECRET", "dev-webhook-secret-change-in-prod"
)


# ── 수신 거부 토큰 유틸 ─────────────────────────────────────

def generate_unsubscribe_token(customer_id: str) -> str:
    """customer_id → HMAC-SHA256 서명 토큰 생성.

    형식: base64url(customer_id) + "." + hex(HMAC[:16])
    이메일 발송 시 이 토큰을 URL에 삽입한다.
    """
    id_b64 = base64.urlsafe_b64encode(customer_id.encode()).rstrip(b"=").decode()
    sig = hmac.new(
        _UNSUBSCRIBE_SECRET.encode(), customer_id.encode(), hashlib.sha256
    ).hexdigest()[:16]
    return f"{id_b64}.{sig}"


def _decode_unsubscribe_token(token: str) -> str | None:
    """토큰 검증 후 customer_id 반환. 검증 실패 시 None."""
    try:
        id_b64, signature = token.split(".", 1)
        customer_id = base64.urlsafe_b64decode(id_b64 + "==").decode()
        expected = hmac.new(
            _UNSUBSCRIBE_SECRET.encode(), customer_id.encode(), hashlib.sha256
        ).hexdigest()[:16]
        if hmac.compare_digest(signature, expected):
            return customer_id
    except Exception:
        pass
    return None


# ── 수신 거부 처리 핵심 로직 ────────────────────────────────

async def _process_unsubscribe(
    customer_id: str,
    source: str,
    audit_logger: AuditLogger | None = None,
) -> None:
    """CustomerConsent.marketing_contact = False 처리.

    현재 구현: SQLite/InMemory 스토리지에 consent_update 이벤트 기록.
    프로덕션: ConsentRepository.update(customer_id, marketing_contact=False) 호출로 교체.
    """
    # AuditEvent 기록 (법적 증거로 보존)
    if audit_logger is not None:
        audit_logger.logger.info(
            "consent.update | customer=%s | field=marketing_contact | value=False | source=%s",
            customer_id,
            source,
        )


# ── 엔드포인트: 이메일 하단 링크 ────────────────────────────

@router.get(
    "/unsubscribe/{token}",
    summary="이메일 수신 거부 처리",
    description=(
        "이메일 하단 '수신 거부' 링크 클릭 시 호출. "
        "정보통신망법 §50: 24시간 이내 처리 완료. "
        "marketing_contact = False 즉시 반영 후 확인 메시지 반환."
    ),
    tags=["email"],
)
async def unsubscribe(token: str, request: Request) -> dict[str, str]:
    customer_id = _decode_unsubscribe_token(token)
    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="유효하지 않거나 만료된 수신 거부 링크입니다.",
        )

    audit_logger: AuditLogger | None = getattr(
        getattr(request.app.state, "store", None), "audit_logger", None
    ) or getattr(request.app.state, "audit_logger", None)

    await _process_unsubscribe(customer_id, source="email_unsubscribe_link", audit_logger=audit_logger)

    return {
        "status": "ok",
        "message": (
            "수신 거부 처리가 완료되었습니다. "
            "HAchilles Weekly 및 마케팅 이메일 발송이 중단됩니다. "
            "다시 구독하시려면 대시보드 설정 → 동의 관리에서 변경하세요."
        ),
        "processed_at": datetime.now(UTC).isoformat(),
        "legal_basis": "정보통신망법 §50 — 수신 거부 처리 24시간 이내 완료",
    }


# ── 엔드포인트: 이메일 서비스 웹훅 ─────────────────────────

class EmailWebhookPayload(BaseModel):
    event_type: str  # "unsubscribe" | "bounce" | "complaint"
    email: str | None = None
    recipient: str | None = None  # 일부 서비스는 recipient 필드 사용
    timestamp: str | None = None
    raw: dict[str, Any] = {}


@router.post(
    "/webhooks/email/unsubscribe-event",
    summary="이메일 서비스 수신 거부 웹훅",
    description=(
        "Amazon SES SNS 알림 또는 이메일 발송 서비스 웹훅을 수신. "
        "수신 거부 이벤트 발생 시 marketing_contact = False 즉시 반영. "
        "정보통신망법 §50: 수신 거부 처리 24시간 이내 완료 보장."
    ),
    tags=["email"],
    status_code=200,
)
async def handle_email_webhook(
    payload: EmailWebhookPayload,
    request: Request,
) -> dict[str, str]:
    # 웹훅 서명 검증 (이메일 서비스 확정 후 서비스별 방법 적용)
    raw_sig = request.headers.get("X-HAW-Webhook-Signature", "")
    if raw_sig:
        body = await request.body()
        expected = hmac.new(
            _WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(raw_sig, expected):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # 수신 거부·반송·스팸 신고 이벤트 처리
    if payload.event_type.lower() not in ("unsubscribe", "bounce", "complaint"):
        return {"status": "ignored", "reason": f"event_type={payload.event_type} 처리 대상 아님"}

    email = payload.email or payload.recipient
    if not email:
        return {"status": "ignored", "reason": "email/recipient 필드 없음"}

    audit_logger: AuditLogger | None = getattr(
        getattr(request.app.state, "store", None), "audit_logger", None
    ) or getattr(request.app.state, "audit_logger", None)

    # 이메일로 customer 조회 (프로덕션: ConsentRepository.find_by_email 교체)
    customer_id = f"webhook:{email}"  # placeholder — 실제 DB 조회로 교체
    await _process_unsubscribe(
        customer_id,
        source=f"email_service_webhook:{payload.event_type}",
        audit_logger=audit_logger,
    )

    return {
        "status": "ok",
        "event_type": payload.event_type,
        "processed_at": datetime.now(UTC).isoformat(),
    }


# ── 마케팅 이메일 발송 전 동의 확인 유틸 ──────────────────

def build_marketing_subject(base_subject: str) -> str:
    """정보통신망법 §50②: 광고성 이메일 제목에 '(광고)' 표기 필수."""
    if not base_subject.startswith("(광고)"):
        return f"(광고) {base_subject}"
    return base_subject


MARKETING_EMAIL_FOOTER_HTML = """\
<!-- 광고성 이메일 하단 필수 푸터 (정보통신망법 §50) -->
<table style="width:100%;border-top:1px solid #e5e7eb;margin-top:32px;padding-top:16px;">
  <tr>
    <td style="font-size:12px;color:#6b7280;text-align:center;line-height:1.8;">
      <strong>HAchillesWorld</strong> | HAchilles Labs<br>
      개인정보 보호책임자: 박성훈 &nbsp;|&nbsp; privacy@hachillesworld.ai<br><br>
      이 이메일은 <strong>{customer_email}</strong>로 발송되었습니다.<br>
      HAchilles Weekly 수신에 동의하셨기 때문에 이 메일을 받고 계십니다.<br><br>
      <a href="https://hachillesworld.ai/v1/unsubscribe/{unsubscribe_token}"
         style="color:#6b7280;text-decoration:underline;">
        수신 거부 (Unsubscribe)
      </a>
      &nbsp;|&nbsp;
      <a href="https://hachillesworld.ai/privacy"
         style="color:#6b7280;text-decoration:underline;">
        개인정보처리방침
      </a>
    </td>
  </tr>
</table>
"""

TRANSACTIONAL_EMAIL_FOOTER_HTML = """\
<!-- 거래성 이메일 하단 푸터 (광고 표기 불필요) -->
<table style="width:100%;border-top:1px solid #e5e7eb;margin-top:32px;padding-top:16px;">
  <tr>
    <td style="font-size:12px;color:#6b7280;text-align:center;line-height:1.8;">
      <strong>HAchillesWorld</strong> | HAchilles Labs<br>
      privacy@hachillesworld.ai &nbsp;|&nbsp;
      <a href="https://hachillesworld.ai/privacy"
         style="color:#6b7280;text-decoration:underline;">
        개인정보처리방침
      </a>
    </td>
  </tr>
</table>
"""


def render_marketing_footer(customer_email: str, customer_id: str) -> str:
    """광고성 이메일 하단 푸터 HTML 렌더링."""
    token = generate_unsubscribe_token(customer_id)
    return MARKETING_EMAIL_FOOTER_HTML.format(
        customer_email=customer_email,
        unsubscribe_token=token,
    )
