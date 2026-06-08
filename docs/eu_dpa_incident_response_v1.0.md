# HAchillesWorld EU DPA 침해 신고 절차서

**문서 번호**: HAW-IRP-EU-001  
**버전**: v1.0  
**작성일**: 2026년 6월 8일  
**작성자**: 박성훈 (CPO, GDPR 대응 담당자)  
**이행 기한**: 2026년 8월 31일 (HAW-CPL-002 M-6)  
**법적 근거**: GDPR Art.33 (감독기관 신고) + Art.34 (정보주체 통지)  
**관련 문서**: HAW-CPL-002 · HAW-POL-001 §12.2 · HAW-DR-001

---

## 1. 관할 DPA 결정 기준

```
EU Representative 미지정 현황 (초기 단계):
  → 침해된 정보주체의 거주국 DPA에 각각 신고 (GDPR Art.27(3))
  예) 독일 고객 유출 → BfDI 신고
      독일 + 프랑스 고객 동시 유출 → BfDI + CNIL 모두 신고

EU Representative 지정 후 (EU 고객 50명+ 확보 시):
  → 대표자 소재국 DPA 단일 창구 신고 (원스톱 메커니즘)
```

## 2. EU DPA 연락처 목록

| 국가 | 기관 | 신고 URL | 신고 언어 |
|------|------|---------|---------|
| 🇩🇪 독일 | BfDI | bfdi.bund.de/meldung | 독일어·영어 |
| 🇫🇷 프랑스 | CNIL | notifications.cnil.fr | 프랑스어 |
| 🇮🇪 아일랜드 | DPC | dataprotection.ie/en/report-a-breach | 영어 |
| 🇳🇱 네덜란드 | AP | autoriteitpersoonsgegevens.nl | 네덜란드어·영어 |
| 🇸🇪 스웨덴 | IMY | imy.se | 스웨덴어·영어 |
| EU 통합 | EDPB | edpb.europa.eu | — |

> **1순위 연락처**: DPC(아일랜드) — 영어 대응, 기술기업 경험 풍부

---

## 3. Art.33 신고 vs Art.34 통지 판단 매트릭스

| 침해 유형 | Art.33 신고 | Art.34 통지 | 비고 |
|---------|:----------:|:----------:|------|
| 이메일 유출 (암호화 해제됨) | 필수 | 필수 | 고위험 |
| 이메일 유출 (암호화 유지) | 필수 | 불필요 | Art.34(3)(a) 예외 |
| 에이전트 수치 데이터 유출 | 필수 | CPO 판단 | 민감도 낮음 |
| API 키 해시 유출 | 필수 | 불필요 | bcrypt — 원본 복원 불가 |
| IP 마스킹 AuditEvent 유출 | 상황 판단 | 불필요 | 재식별 불가 |

---

## 4. 72시간 대응 체크리스트

```
T+0   사고 탐지
  □ 최초 인지 시각 기록 (UTC)
  □ CPO 즉시 보고
  □ 내부 인시던트 채널 개설

T+1h  초기 범위 파악
  □ EU 고객 포함 여부 확인
  □ 침해 데이터 유형 목록화
  □ Art.33 신고 필요 여부 1차 판단

T+4h  신고 준비
  □ Art.34 통지 필요 여부 판단 (고위험 여부 = 암호화 해제 여부)
  □ §5 신고 양식 초안 작성
  □ 영향받은 EU 고객 국적별 분류 → 관할 DPA 확정

T+24h 신고 초안 완성
  □ EU DPA 포털 계정 확인
  □ 영문 고객 통지 이메일 초안 완성 (§6 템플릿 활용)

T+48h 최종 확인
  □ 침해 범위 확정 (정보주체 수 확정)
  □ Art.34 통지 여부 최종 결정

T+72h 신고 제출 기한
  □ 해당 DPA 포털 온라인 신고 제출
  □ 제출 확인번호(Reference Number) 기록
  □ Art.34 해당 시: EU 고객 영문 이메일 발송
  □ AuditEvent: action="gdpr.dpa.reported"
```

---

## 5. DPA 신고 표준 양식 (사전 작성 템플릿)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section A. Controller Information

  Name:          HAchilles Labs
  Contact:       Park Sung Hoon (CEO / DPO)
  Email:         privacy@hachillesworld.ai
  Country:       Republic of Korea
  EU Rep:        [미지정 / "Not yet designated"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section B. Nature of the Breach

  Detected:  [YYYY-MM-DD HH:MM UTC]
  Occurred:  [YYYY-MM-DD HH:MM UTC or "Unknown"]
  Duration:  [기간 or "Ongoing"]

  Category:
    □ Confidentiality breach (무단 접근·유출)
    □ Integrity breach (무단 수정)
    □ Availability breach (접근 불가·삭제)

  Data affected:
    □ Email addresses
    □ Agent diagnostic data (HAS scores, 15 metrics)
    □ Access logs (IP hashed)
    □ API key hashes
    □ Other: _______________

  Data subjects affected:
    Approximate: [숫자 or "Unknown, under investigation"]
    EU only: [숫자]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section C. Likely Consequences

  [예: "Potential exposure of encrypted email addresses.
   Decryption keys were not compromised — re-identification
   risk assessed as LOW."]

  Risk level: □ Low  □ Medium  □ High (Art.34 notification required)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section D. Measures Taken

  [예: "Revoked compromised API keys within 15 minutes.
   Closed security vulnerability. Forensic investigation launched.
   Affected customers notified. Password reset enforced."]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Section E. Further Information

  All info within 72h?  □ Yes  □ No (reason: _____________)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 6. 영문 정보주체 통지 이메일 템플릿 (Art.34)

```
Subject: [HAchillesWorld] Important Notice: Personal Data Breach

Dear [Customer Name / "HAchillesWorld User"],

We are writing to inform you that HAchillesWorld has experienced a
personal data security incident that may affect your account.

We are notifying you in accordance with Article 34 of the GDPR.

──────────────────────────────────────────

1. WHAT HAPPENED
   On [Date], we detected [brief description].
   Duration: [start] – [end] UTC.

2. WHAT DATA WAS AFFECTED
   · [e.g., Email address (encrypted — decryption key not compromised)]
   · [e.g., Agent diagnostic scores]
   NOT affected: API keys (one-way hash), raw content, payment data.

3. WHAT WE HAVE DONE
   · Revoked compromised credentials within [X] minutes
   · Closed the vulnerability
   · Notified the relevant DPA within 72 hours (GDPR Art.33)

4. WHAT YOU SHOULD DO
   □ Regenerate API key: Dashboard → Settings → API Keys → Regenerate
   □ Review account audit log for unusual activity
   □ Be alert for phishing emails claiming to be from HAchillesWorld

5. YOUR GDPR RIGHTS
   · Lodge a complaint: edpb.europa.eu/national-supervisory-authorities
   · Contact us: privacy@hachillesworld.ai (response within 72h)

We sincerely apologize for any concern this may cause.

HAchilles Labs | privacy@hachillesworld.ai
──────────────────────────────────────────
```

---

## 7. 사전 준비 사항 (M-6 완료 기준)

```
□ DPC (아일랜드) 포털 계정 사전 가입
    URL: dataprotection.ie/en/report-a-breach
□ BfDI (독일) 포털 접속 확인
    URL: meldungen.bfdi.bund.de
□ 모의 훈련 실시 (2026-08-31 이전)
    가상 P1 시나리오로 72h 체크리스트 전체 실행
    훈련 결과 보고서 보관
□ AuditEvent: action="compliance.m6.completed" 기록
```

---

## 8. 버전 이력

| 버전 | 시행일 | 주요 내용 |
|------|--------|---------|
| v1.0 | 2026-06-08 | 최초 작성 (HAW-CPL-002 M-6 이행) |

---

*문서 번호: HAW-IRP-EU-001 | 버전: v1.0*  
*작성자: 박성훈 (CPO) | 관련: HAW-CPL-002 · HAW-POL-001 §12.2*
