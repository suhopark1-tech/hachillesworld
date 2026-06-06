#!/usr/bin/env python3
# Copyright 2026 HAchillesWorld (박성훈)
# SPDX-License-Identifier: Apache-2.0

"""HAW-STUDY-001 다중공선성 분석 실행 스크립트.

사용법:
    python scripts/run_multicollinearity.py

결과:
    docs/analysis/multicollinearity_study001.md 에 저장
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hachillesworld.analyze.multicollinearity import MulticollinearityAnalyzer
from hachillesworld.analyze.study_analysis import ALL_METRICS, StudyAnalyzer


def build_metric_matrix(
    study_id: str = "HAW-STUDY-001",
) -> tuple[list[list[float]], list[str]]:
    """StudyDataset에서 (n_agents, 15) 지표 점수 행렬 구성."""
    sa = StudyAnalyzer()
    dataset = sa.load_study_data(study_id)
    matrix: list[list[float]] = []
    for record in dataset.records:
        row = [record.metric_scores.get(m, 0.5) for m in ALL_METRICS]
        matrix.append(row)
    print(f"데이터 소스: {dataset.data_source}  n={dataset.n}")
    return matrix, list(ALL_METRICS)


def main() -> None:
    print("=" * 60)
    print("HAW-STUDY-001 다중공선성 분석")
    print("=" * 60)

    matrix, metric_names = build_metric_matrix()
    print(f"행렬 크기: {len(matrix)} × {len(metric_names)}")

    analyzer = MulticollinearityAnalyzer()
    report = analyzer.analyze(matrix, metric_names)

    # ── 콘솔 요약 출력 ──────────────────────────────────────
    print("\n[VIF 상위 5개 지표]")
    top_vif = sorted(report.vif_scores.items(), key=lambda x: -x[1])[:5]
    for name, vif in top_vif:
        flag = " ⚠️" if vif > analyzer.HIGH_VIF_THRESHOLD else ""
        print(f"  {name:6s}  VIF={vif:.2f}{flag}")

    print(
        f"\n[고상관 쌍] {len(report.high_correlation_pairs)}개 (|r| > {analyzer.HIGH_CORR_THRESHOLD})"
    )
    for a, b, r in sorted(report.high_correlation_pairs, key=lambda x: -abs(x[2]))[:5]:
        print(f"  {a} ↔ {b}  r={r:+.4f}")
    if len(report.high_correlation_pairs) > 5:
        print(f"  ... 외 {len(report.high_correlation_pairs) - 5}개")

    if report.problematic_metrics:
        print(
            f"\n[경고] VIF > {analyzer.HIGH_VIF_THRESHOLD} 지표: {', '.join(report.problematic_metrics)}"
        )
    else:
        print(f"\n[OK] 모든 지표 VIF < {analyzer.HIGH_VIF_THRESHOLD}")

    print(f"\n[권고사항]\n{report.recommendation}")

    # ── 마크다운 보고서 저장 ─────────────────────────────────
    output_dir = Path(__file__).parent.parent / "docs" / "analysis"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "multicollinearity_study001.md"

    md = report.generate_report_markdown()
    output_path.write_text(md, encoding="utf-8")
    print(f"\n보고서 저장: {output_path}")

    # ── Shapley 조정 가중치 출력 ─────────────────────────────
    from hachillesworld.analyze.study_analysis import StudyAnalyzer as SA2

    sa2 = SA2()
    dataset = sa2.load_study_data("HAW-STUDY-001")
    adjusted = sa2.shapley_with_correlation_adjustment(dataset, report)
    print("\n[상관 조정 Shapley 가중치]")
    print(adjusted.summary())


if __name__ == "__main__":
    main()
