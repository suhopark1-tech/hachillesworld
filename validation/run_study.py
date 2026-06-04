"""HAchillesWorld 횡단 타당도 연구 — 메인 실행 파일

사용법:
  python run_study.py                    # 합성 데이터로 전체 파이프라인 실행
  python run_study.py --data real.json   # 실제 데이터로 실행
  python run_study.py --quick            # 5개 에이전트 빠른 테스트

결과:
  study_results/
    has_scores.json        — 에이전트별 HAS 점수
    correlation_report.txt — H1 검증 결과
    shapley_report.txt     — 지표별 중요도
    full_report.html       — 전체 시각화 보고서
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime

# 모듈 경로 설정
sys.path.insert(0, os.path.dirname(__file__))

from analysis.correlation import (
    CorrelationResult,
    bootstrap_ci,
    compute_shapley_values,
    partial_correlation_controlling_domain,
    spearman_rho,
)
from has_calculator import compute_has_from_episodes
from sample_data import AGENT_PROFILES, generate_study_dataset

# ----------------------------------------------
# 단계 1: 데이터 로드
# ----------------------------------------------


def load_or_generate_dataset(data_path: str | None, quick: bool) -> list[dict]:
    if data_path and os.path.exists(data_path):
        print(f"\n[1/4] 실제 데이터 로드: {data_path}")
        with open(data_path, encoding="utf-8") as f:
            return json.load(f)

    n_agents = 5 if quick else len(AGENT_PROFILES)
    print(f"\n[1/4] 합성 데이터 생성 ({n_agents}개 에이전트)...")
    profiles_subset = AGENT_PROFILES[:n_agents]

    import sample_data as sd

    sd.AGENT_PROFILES = profiles_subset

    os.makedirs("study_results", exist_ok=True)
    dataset = generate_study_dataset(
        output_path=f"study_results/synthetic_dataset_n{n_agents}.json",
        n_episodes_per_agent=300 if quick else 500,
        noise_level=0.05,
        seed=42,
    )
    return dataset


# ----------------------------------------------
# 단계 2: 각 에이전트 HAS 계산
# ----------------------------------------------


def compute_all_has(dataset: list[dict]) -> list[dict]:
    print(f"\n[2/4] HAS 계산 ({len(dataset)}개 에이전트)...")
    results = []

    for item in dataset:
        agent_id = item["agent_id"]
        domain = item["domain"]
        t0 = time.time()

        report = compute_has_from_episodes(
            episodes=item["episodes"],
            agent_id=agent_id,
            domain=domain,
            monthly_budget_usd=item.get("monthly_budget_usd", 200.0),
            harness_rules=item.get("harness_rules"),
            incident_records=item.get("incident_records"),
            counterfactual_records=item.get("counterfactual_records"),
            period_days=30,
        )

        elapsed = time.time() - t0
        print(
            f"  {agent_id:20s}  HAS={report.has:4d}  [{report.grade}]  "
            f"Level={report.level_estimate}  ({elapsed:.1f}s)",
        )

        results.append(
            {
                "agent_id": agent_id,
                "domain": domain,
                "has": report.has,
                "dahas": report.dahas,
                "grade": report.grade,
                "level": report.level_estimate,
                "wmq_score": round(report.wmq_score, 2),
                "alm_score": round(report.alm_score, 2),
                "ohm_score": round(report.ohm_score, 2),
                # 15개 지표 원시값
                "metrics": {
                    "sdr": round(report.wmq.sdr, 4),
                    "ece": round(report.wmq.ece, 4),
                    "pa": round(report.wmq.pa, 4),
                    "odr": round(report.wmq.odr, 4),
                    "pd": round(report.alm.pd, 1),
                    "scr": round(report.alm.scr, 4),
                    "gar": round(report.alm.gar, 4),
                    "as": round(1 - report.alm.hitl_rate, 4),
                    "lcr": round(report.ohm.lcr, 4),
                    "hc": report.ohm.hc,
                    "hr": round(report.ohm.hr, 4),
                    "su": round(report.ohm.su, 4),
                },
                # ground truth (합성 데이터)
                "business_outcome": item.get("business_outcome_score", None),
                "true_level": item.get("true_level", None),
            },
        )

    return results


# ----------------------------------------------
# 단계 3: 통계 분석
# ----------------------------------------------


def run_statistical_analysis(results: list[dict]) -> dict:
    print("\n[3/4] 통계 분석 실행...")

    outcomes = [r["business_outcome"] for r in results if r["business_outcome"] is not None]
    has_with_outcomes = [r["has"] for r in results if r["business_outcome"] is not None]
    domains = [r["domain"] for r in results if r["business_outcome"] is not None]

    n = len(has_with_outcomes)
    print(f"  비즈니스 성과 데이터 있는 에이전트: {n}개")

    # -- H1: 주 상관관계 --
    rho, p_val = spearman_rho(has_with_outcomes, outcomes)
    h1_passed = rho >= 0.60 and p_val < 0.01
    corr_result = CorrelationResult(
        rho=rho,
        p_value=p_val,
        n=n,
        significant=p_val < 0.05,
        h1_passed=h1_passed,
    )

    print("\n  -- H1 검증: rho(HAS, Q) --")
    print(corr_result.summary())

    # -- 부트스트랩 신뢰구간 --
    rho_mean, ci_lo, ci_hi = bootstrap_ci(has_with_outcomes, outcomes, n_bootstrap=1000)
    print(f"  부트스트랩 95% CI: [{ci_lo:.4f}, {ci_hi:.4f}]")

    # -- H3: 도메인 통제 편상관 --
    partial_rho, partial_p = partial_correlation_controlling_domain(
        has_with_outcomes, outcomes, domains,
    )
    print("\n  -- H3 검증: 도메인 통제 편상관 --")
    print(f"  Partial rho = {partial_rho:.4f}  p = {partial_p:.4f}")

    # -- H2: Shapley 값 --
    metric_names = ["SDR", "ECE", "PA", "ODR", "PD", "SCR", "GAR", "AS", "LCR", "HC", "HR", "SU"]
    feature_matrix = [
        [
            r["metrics"].get("sdr", 0),
            r["metrics"].get("ece", 0),
            r["metrics"].get("pa", 0),
            r["metrics"].get("odr", 0),
            r["metrics"].get("pd", 0) / 25,  # 정규화
            r["metrics"].get("scr", 0),
            r["metrics"].get("gar", 0),
            r["metrics"].get("as", 0),
            r["metrics"].get("lcr", 0),
            r["metrics"].get("hc", 0) / 40,  # 정규화
            r["metrics"].get("hr", 0),
            r["metrics"].get("su", 0),
        ]
        for r in results
        if r["business_outcome"] is not None
    ]

    print("\n  -- H2 검증: 지표별 Shapley 중요도 --")
    if len(feature_matrix) >= 5:
        shapley_result = compute_shapley_values(feature_matrix, outcomes, metric_names)
        print(shapley_result.summary())
    else:
        shapley_result = None
        print("  (표본이 부족하여 Shapley 분석 생략)")

    # -- 도메인별 상관관계 --
    print("\n  -- 도메인별 상관관계 --")
    domain_corrs = {}
    unique_domains = sorted(set(domains))
    for domain in unique_domains:
        d_has = [h for h, d in zip(has_with_outcomes, domains, strict=False) if d == domain]
        d_out = [o for o, d in zip(outcomes, domains, strict=False) if d == domain]
        if len(d_has) >= 3:
            d_rho, d_p = spearman_rho(d_has, d_out)
            sig = "[OK]" if d_p < 0.05 else "[WARN] "
            print(f"  {domain:20s}: rho={d_rho:.3f}  p={d_p:.3f}  n={len(d_has)}  {sig}")
            domain_corrs[domain] = {"rho": d_rho, "p": d_p, "n": len(d_has)}

    return {
        "h1": {
            "rho": rho,
            "p_value": p_val,
            "n": n,
            "passed": h1_passed,
            "bootstrap_ci": [ci_lo, ci_hi],
        },
        "h3": {"partial_rho": partial_rho, "partial_p": partial_p},
        "h2": shapley_result.__dict__ if shapley_result else None,
        "domain_correlations": domain_corrs,
    }


# ----------------------------------------------
# 단계 4: 결과 저장
# ----------------------------------------------


def save_results(results: list[dict], analysis: dict, output_dir: str = "study_results"):
    print(f"\n[4/4] 결과 저장: {output_dir}/")
    os.makedirs(output_dir, exist_ok=True)

    # HAS 점수 JSON
    scores_path = os.path.join(output_dir, "has_scores.json")
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  저장: {scores_path}")

    # 텍스트 보고서
    report_path = os.path.join(output_dir, "correlation_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        _write_text_report(f, results, analysis)
    print(f"  저장: {report_path}")

    # HTML 보고서
    html_path = os.path.join(output_dir, "full_report.html")
    with open(html_path, "w", encoding="utf-8") as f:
        _write_html_report(f, results, analysis)
    print(f"  저장: {html_path}")


def _write_text_report(f, results: list[dict], analysis: dict):
    f.write("=" * 60 + "\n")
    f.write("  HAchillesWorld 횡단 타당도 연구 결과 보고서\n")
    f.write(f"  생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write("=" * 60 + "\n\n")

    f.write("## 1. 표본 개요\n\n")
    from collections import Counter

    domain_counts = Counter(r["domain"] for r in results)
    f.write(f"  전체 에이전트 수: {len(results)}\n")
    for domain, cnt in sorted(domain_counts.items()):
        f.write(f"  {domain:25s}: {cnt}개\n")

    f.write("\n## 2. HAS 분포\n\n")
    has_scores = [r["has"] for r in results]
    f.write(f"  평균: {sum(has_scores) / len(has_scores):.1f}\n")
    f.write(f"  최솟값: {min(has_scores)}\n")
    f.write(f"  최댓값: {max(has_scores)}\n")

    f.write("\n## 3. H1 검증 — rho(HAS, Q)\n\n")
    h1 = analysis["h1"]
    f.write(f"  Spearman rho = {h1['rho']:.4f}\n")
    f.write(f"  p-값      = {h1['p_value']:.4f}\n")
    f.write(f"  95% CI    = [{h1['bootstrap_ci'][0]:.4f}, {h1['bootstrap_ci'][1]:.4f}]\n")
    f.write(
        f"  결론: {'[OK] H1 채택 (rho >= 0.60, p < 0.01)' if h1['passed'] else '[FAIL] H1 기각'}\n",
    )

    f.write("\n## 4. H2 — 지표별 중요도\n\n")
    if analysis.get("h2"):
        h2 = analysis["h2"]
        pairs = sorted(
            zip(h2["metric_names"], h2["relative_importance"], strict=False),
            key=lambda x: x[1],
            reverse=True,
        )
        for name, rel in pairs:
            bar = "█" * int(rel / 4)
            f.write(f"  {name:6s} | {bar:<26s} {rel:5.1f}%\n")

    f.write("\n## 5. H3 — 도메인 통제 편상관\n\n")
    h3 = analysis["h3"]
    f.write(f"  Partial rho = {h3['partial_rho']:.4f}\n")
    f.write(f"  p-값      = {h3['partial_p']:.4f}\n")

    f.write("\n## 6. 도메인별 상관관계\n\n")
    for domain, dc in analysis.get("domain_correlations", {}).items():
        sig = "[OK]" if dc["p"] < 0.05 else "[WARN]"
        f.write(f"  {domain:20s}: rho={dc['rho']:.3f}  p={dc['p']:.3f}  {sig}\n")

    f.write("\n" + "=" * 60 + "\n")


def _write_html_report(f, results: list[dict], analysis: dict):
    h1 = analysis["h1"]
    status_color = "#22c55e" if h1["passed"] else "#ef4444"
    status_text = "[OK] H1 채택" if h1["passed"] else "[FAIL] H1 기각"

    rows = ""
    for r in sorted(results, key=lambda x: x["has"], reverse=True):
        grade_color = {
            "A+": "#16a34a",
            "A": "#22c55e",
            "B": "#84cc16",
            "C": "#eab308",
            "D": "#f97316",
            "F": "#ef4444",
            "F-": "#dc2626",
        }.get(r["grade"], "#6b7280")
        rows += f"""
        <tr>
          <td>{r["agent_id"]}</td>
          <td>{r["domain"]}</td>
          <td style="font-weight:bold;color:{grade_color}">{r["has"]} [{r["grade"]}]</td>
          <td>{r["level"]}</td>
          <td>{r["wmq_score"]:.1f}</td>
          <td>{r["alm_score"]:.1f}</td>
          <td>{r["ohm_score"]:.1f}</td>
          <td>{r.get("business_outcome", "N/A")}</td>
        </tr>"""

    shapley_rows = ""
    if analysis.get("h2"):
        h2 = analysis["h2"]
        pairs = sorted(
            zip(h2["metric_names"], h2["relative_importance"], strict=False),
            key=lambda x: x[1],
            reverse=True,
        )
        for name, rel in pairs:
            bar_w = int(rel * 3)
            shapley_rows += f"""
            <tr>
              <td>{name}</td>
              <td><div style="background:#6366f1;height:16px;width:{bar_w}px;border-radius:2px"></div></td>
              <td>{rel:.1f}%</td>
            </tr>"""

    f.write(f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>HAchillesWorld 횡단 타당도 연구 결과</title>
  <style>
    body {{ font-family: 'Segoe UI', sans-serif; background:#0f172a; color:#e2e8f0; margin:0; padding:2rem; }}
    h1 {{ color:#a78bfa; border-bottom:2px solid #334155; padding-bottom:0.5rem; }}
    h2 {{ color:#7dd3fc; margin-top:2rem; }}
    .card {{ background:#1e293b; border-radius:12px; padding:1.5rem; margin:1rem 0; }}
    .stat {{ font-size:2.5rem; font-weight:bold; color:{status_color}; }}
    table {{ width:100%; border-collapse:collapse; }}
    th {{ background:#334155; padding:0.6rem 1rem; text-align:left; }}
    td {{ padding:0.5rem 1rem; border-bottom:1px solid #334155; }}
    tr:hover {{ background:#334155; }}
    .badge {{ display:inline-block; padding:2px 8px; border-radius:4px; }}
  </style>
</head>
<body>
  <h1>HAchillesWorld 횡단 타당도 연구 결과</h1>
  <p style="color:#94a3b8">생성일: {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")} | 에이전트 n={len(results)}</p>

  <div class="card">
    <h2>🎯 H1 검증 결과 — rho(HAS, Q) >= 0.60</h2>
    <div class="stat">{status_text}</div>
    <p>Spearman rho = <strong>{h1["rho"]:.4f}</strong> &nbsp;|&nbsp;
       p-값 = <strong>{h1["p_value"]:.4f}</strong> &nbsp;|&nbsp;
       95% CI = [{h1["bootstrap_ci"][0]:.3f}, {h1["bootstrap_ci"][1]:.3f}]</p>
    <p style="color:#94a3b8">H1 채택 조건: rho >= 0.60 이고 p &lt; 0.01</p>
  </div>

  <div class="card">
    <h2>📊 에이전트별 HAS 점수</h2>
    <table>
      <thead><tr>
        <th>에이전트 ID</th><th>도메인</th><th>HAS</th><th>레벨</th>
        <th>WMQ</th><th>ALM</th><th>OHM</th><th>비즈니스 성과</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>🔬 H2 — 지표별 Shapley 중요도</h2>
    <table>
      <thead><tr><th>지표</th><th>중요도 시각화</th><th>기여도(%)</th></tr></thead>
      <tbody>{shapley_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>📐 H3 — 도메인 통제 편상관</h2>
    <p>Partial rho = <strong>{analysis["h3"]["partial_rho"]:.4f}</strong> &nbsp;
       p-값 = <strong>{analysis["h3"]["partial_p"]:.4f}</strong></p>
    <p style="color:#94a3b8">
      도메인 효과를 통제한 후에도 HAS와 비즈니스 성과 간 상관관계가 유지되는지 확인.
    </p>
  </div>
</body>
</html>""")


# ----------------------------------------------
# 메인 진입점
# ----------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="HAchillesWorld 횡단 타당도 연구")
    parser.add_argument("--data", type=str, default=None, help="실제 데이터 JSON 경로")
    parser.add_argument("--quick", action="store_true", help="5개 에이전트 빠른 테스트")
    parser.add_argument("--out", type=str, default="study_results", help="결과 저장 디렉토리")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print("=" * 60)
    print("  HAchillesWorld 횡단 타당도 연구 파이프라인")
    print("  논문: Levels x Laws Framework (HAW-TR-001)")
    print("=" * 60)

    t_start = time.time()

    dataset = load_or_generate_dataset(args.data, args.quick)
    results = compute_all_has(dataset)
    analysis = run_statistical_analysis(results)
    save_results(results, analysis, args.out)

    elapsed = time.time() - t_start
    print(f"\nDone ({elapsed:.1f}s)")
    print(f"   Output dir: {args.out}/")

    h1 = analysis["h1"]
    verdict = "H1 ACCEPTED" if h1["passed"] else "H1 REJECTED - need more data"
    print(f"\n{'=' * 60}")
    print(f"  Final verdict: {verdict}")
    print(f"  rho = {h1['rho']:.4f}  (threshold: >= 0.60)")
    print(f"  p   = {h1['p_value']:.4f}  (threshold: < 0.01)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
