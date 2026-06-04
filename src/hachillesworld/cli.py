"""HAchillesWorld CLI — hachillesworld 명령어 진입점."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from hachillesworld.collect.episode import EpisodeRecord

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(name="hachillesworld", help="HAchillesWorld — World Model 진단 및 최적화 CLI")
console = Console()

# ── collect 서브앱 ────────────────────────────────────────────────
collect_app = typer.Typer(help="에피소드 로그 수집·전송·통계")
app.add_typer(collect_app, name="collect")


@app.command()
def scan(
    logs: Optional[Path] = typer.Option(
        None, "--logs", "-l", help="에이전트 로그 파일 경로 (JSON)"
    ),
    config: Optional[Path] = typer.Option(
        None, "--config", "-c", help="에이전트 설정 파일 경로 (JSON)"
    ),
    agent_name: str = typer.Option("unnamed-agent", "--name", "-n", help="에이전트 이름"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="리포트 저장 경로 (JSON)"),
) -> None:
    """에이전트 시스템을 진단하고 리포트를 출력한다."""
    from hachillesworld.core.client import HAchillesWorldClient

    console.print(Panel("[bold cyan]HAchillesWorld Scan[/bold cyan]", expand=False))

    log_data = json.loads(logs.read_text(encoding="utf-8")) if logs else []
    config_data = json.loads(config.read_text(encoding="utf-8")) if config else {}

    with HAchillesWorldClient() as client:
        report = client.scan(logs=log_data, config=config_data, agent_name=agent_name)

    # 결과 출력
    console.print(f"\n[bold]에이전트:[/bold] {report.agent_name}")
    console.print(
        f"[bold]현재 Level:[/bold] {report.level_label}  ×  {report.laws_domain.value.title()} Laws"
    )

    table = Table(title="진단 점수", show_header=True, header_style="bold magenta")
    table.add_column("카테고리", style="cyan")
    table.add_column("점수", justify="right")
    table.add_column("상태")
    for cat, score in [
        ("World Model 품질", report.world_model_quality.score),
        ("에이전시 수준", report.agency_level.score),
        ("운영 건전성", report.operational_health.score),
        ("종합", report.composite_score),
    ]:
        emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
        table.add_row(cat, f"{score:.0f}/100", emoji)
    console.print(table)

    if report.critical_issues:
        console.print("\n[bold red]즉시 조치 필요:[/bold red]")
        for issue in report.critical_issues:
            console.print(f"  🔴 {issue.name}: {issue.description}")

    if report.recommendations:
        console.print("\n[bold yellow]권장 조치:[/bold yellow]")
        for rec in report.recommendations[:5]:
            console.print(f"  • {rec}")

    if output:
        data = {
            "agent_name": report.agent_name,
            "level": report.level_label,
            "laws_domain": report.laws_domain.value,
            "composite_score": report.composite_score,
            "recommendations": report.recommendations,
        }
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"\n[green]리포트 저장 완료:[/green] {output}")


@app.command()
def optimize(
    report_file: Path = typer.Argument(..., help="scan 결과 JSON 파일"),
    target_level: Optional[str] = typer.Option(
        None, "--target", "-t", help="목표 Level (L2 또는 L3)"
    ),
) -> None:
    """진단 리포트 기반 최적화 로드맵을 출력한다."""
    from hachillesworld.core.client import HAchillesWorldClient
    from hachillesworld.optimize.roadmap import RoadmapGenerator

    console.print(Panel("[bold green]HAchillesWorld Optimize[/bold green]", expand=False))

    data = json.loads(report_file.read_text(encoding="utf-8"))
    # 간이 리포트 복원 (실제로는 전체 DiagnosticReport 직렬화 사용)
    client = HAchillesWorldClient()
    report = client.scan(logs=[], config={}, agent_name=data.get("agent_name", "unknown"))

    roadmap = RoadmapGenerator().generate(report, target_level=target_level)
    RoadmapGenerator().print_roadmap(roadmap)


@app.command()
def version() -> None:
    """버전 정보를 출력한다."""
    from hachillesworld import __version__

    console.print(f"HAchillesWorld v{__version__}")


# ══════════════════════════════════════════════════════════════════
# collect 서브커맨드
# ══════════════════════════════════════════════════════════════════


def _api_key_from_env(explicit: str | None) -> str:
    """명시 인자 → 환경변수 순으로 API 키를 반환한다."""
    return explicit or os.environ.get("HACHILLESWORLD_API_KEY", "")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """JSONL(한 줄 = 한 오브젝트) 또는 JSON 배열 파일을 로드한다."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        data: list[dict[str, Any]] = json.loads(text)
        return data
    return [json.loads(line) for line in text.splitlines() if line.strip()]


# ── collect ingest ───────────────────────────────────────────────


@collect_app.command("ingest")
def collect_ingest(
    files: list[Path] = typer.Argument(..., help="JSONL 또는 JSON 로그 파일 경로 (1개 이상)"),
    api_key: Optional[str] = typer.Option(
        None, "--api-key", "-k", help="API 키 (미지정 시 HACHILLESWORLD_API_KEY 환경변수 사용)"
    ),
    ingest_url: str = typer.Option(
        "https://ingest.hachillesworld.ai/v1", "--url", "-u", help="인제스트 엔드포인트 URL"
    ),
    agent_id: Optional[str] = typer.Option(
        None, "--agent-id", "-a", help="로그 전체에 적용할 agent_id (미지정 시 파일 내 값 사용)"
    ),
    domain: Optional[str] = typer.Option(
        None,
        "--domain",
        "-d",
        help="도메인 덮어쓰기 (supply_chain | customer_service | finance | code | research)",
    ),
    study_id: Optional[str] = typer.Option(
        None, "--study-id", "-s", help="HAW-STUDY-001 연구 참여 ID"
    ),
    batch_size: int = typer.Option(50, "--batch", "-b", help="배치 크기"),
    fallback: Optional[Path] = typer.Option(
        None, "--fallback", "-f", help="전송 실패 시 기록할 JSONL 파일 경로"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="전송 없이 유효성 검사 및 통계만 출력"),
) -> None:
    """JSONL/JSON 로그 파일을 파싱해 인제스트 엔드포인트로 배치 전송한다."""
    from hachillesworld.collect.episode import EpisodeRecord
    from hachillesworld.collect.flush import BatchFlusher

    console.print(Panel("[bold cyan]HAchillesWorld Collect — Ingest[/bold cyan]", expand=False))

    # ── 파일 로드 ─────────────────────────────────────────────────
    raw_records: list[dict[str, Any]] = []
    for fp in files:
        if not fp.exists():
            console.print(f"[red]파일 없음:[/red] {fp}")
            raise typer.Exit(1)
        loaded = _load_jsonl(fp)
        console.print(f"  [dim]로드:[/dim] {fp.name}  ({len(loaded)}건)")
        raw_records.extend(loaded)

    if not raw_records:
        console.print("[yellow]로드된 레코드가 없습니다.[/yellow]")
        raise typer.Exit(0)

    # ── EpisodeRecord 변환 + 필드 덮어쓰기 ──────────────────────
    records: list[EpisodeRecord] = []
    parse_errors = 0
    for raw in raw_records:
        try:
            if agent_id:
                raw["agent_id"] = agent_id
            if domain:
                raw["domain"] = domain
            if study_id:
                raw["study_id"] = study_id
            records.append(EpisodeRecord.from_dict(raw))
        except (KeyError, TypeError) as exc:
            parse_errors += 1
            if parse_errors <= 3:
                console.print(
                    f"  [red]파싱 오류:[/red] {exc}  (episode_id={raw.get('episode_id', '?')})"
                )

    if parse_errors:
        console.print(f"  [red]파싱 실패:[/red] {parse_errors}건 (건너뜀)")

    console.print(f"\n[bold]총 레코드:[/bold] {len(records)}건 (파싱 실패 {parse_errors}건 제외)")

    # ── 유효성 통계 ───────────────────────────────────────────────
    _print_ingest_stats(records)

    if dry_run:
        console.print("\n[yellow]--dry-run 모드: 전송하지 않습니다.[/yellow]")
        raise typer.Exit(0)

    # ── 배치 전송 ─────────────────────────────────────────────────
    key = _api_key_from_env(api_key)
    if not key:
        console.print("[yellow]API 키 없음 → 폴백 파일에만 기록합니다.[/yellow]")

    flusher = BatchFlusher(
        api_key=key,
        ingest_url=ingest_url,
        fallback_path=fallback,
    )

    total_sent = 0
    batches = [records[i : i + batch_size] for i in range(0, len(records), batch_size)]
    with typer.progressbar(batches, label="전송 중") as progress:
        for batch in progress:
            total_sent += flusher.flush(batch)
    flusher.close()

    failed = len(records) - total_sent
    console.print(f"\n[green]전송 완료:[/green] {total_sent}건")
    if failed:
        dest = fallback or Path("haw_fallback.jsonl")
        console.print(f"[yellow]전송 실패:[/yellow] {failed}건 → {dest}")


# ── collect record ───────────────────────────────────────────────


@collect_app.command("record")
def collect_record(
    agent_id: str = typer.Option(..., "--agent-id", "-a", help="에이전트 식별자"),
    domain: str = typer.Option("", "--domain", "-d", help="에이전트 도메인"),
    confidence: Optional[float] = typer.Option(
        None, "--confidence", "-c", help="행동 확신도 [0–1]"
    ),
    goal_achieved: bool = typer.Option(True, "--goal/--no-goal", help="목표 달성 여부"),
    tokens: int = typer.Option(0, "--tokens", "-t", help="LLM 토큰 수"),
    flag: Optional[str] = typer.Option(
        None, "--flag", "-f", help="내부 플래그 유형 (confidence | prediction | counterfactual)"
    ),
    correction_source: Optional[str] = typer.Option(
        None, "--correction", help="수정 출처 (self | harness | hitl)"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="기록할 JSONL 파일 (미지정 시 stdout)"
    ),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k", help="API 키"),
    ingest_url: str = typer.Option("https://ingest.hachillesworld.ai/v1", "--url"),
    send: bool = typer.Option(False, "--send", help="기록 즉시 인제스트 엔드포인트로 전송"),
) -> None:
    """단일 에피소드를 CLI에서 직접 기록한다. JSONL 파일 또는 인제스트로 저장."""
    from hachillesworld.collect.episode import EpisodeRecord
    from hachillesworld.collect.flush import BatchFlusher

    console.print(Panel("[bold cyan]HAchillesWorld Collect — Record[/bold cyan]", expand=False))

    record = EpisodeRecord(
        agent_id=agent_id,
        domain=domain,
        confidence=confidence,
        goal_achieved=goal_achieved,
        episode_success=goal_achieved,
        llm_tokens=tokens,
        internal_flag_raised=flag is not None,
        flag_types=[flag] if flag else [],
        correction_source=correction_source,
        agent_self_flagged=(correction_source == "self"),
        harness_reject_triggered=(correction_source == "harness"),
        hitl_required=(correction_source == "hitl"),
    )

    line = json.dumps(record.to_dict(), ensure_ascii=False)

    if output:
        with output.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        console.print(f"[green]기록 완료:[/green] {output}  (episode_id={record.episode_id})")
    else:
        console.print("\n[bold]생성된 EpisodeRecord:[/bold]")
        console.print_json(line)

    if send:
        key = _api_key_from_env(api_key)
        flusher = BatchFlusher(api_key=key, ingest_url=ingest_url)
        sent = flusher.flush([record])
        flusher.close()
        if sent:
            console.print("[green]인제스트 전송 완료.[/green]")
        else:
            console.print("[yellow]전송 실패 → 폴백 파일 확인.[/yellow]")


# ── collect replay ───────────────────────────────────────────────


@collect_app.command("replay")
def collect_replay(
    fallback_file: Path = typer.Argument(..., help="재전송할 폴백 JSONL 파일"),
    api_key: Optional[str] = typer.Option(None, "--api-key", "-k"),
    ingest_url: str = typer.Option("https://ingest.hachillesworld.ai/v1", "--url"),
    batch_size: int = typer.Option(50, "--batch", "-b"),
    delete_on_success: bool = typer.Option(
        False, "--delete", help="전송 성공한 레코드를 파일에서 삭제"
    ),
) -> None:
    """폴백 JSONL 파일의 레코드를 인제스트 엔드포인트로 재전송한다."""
    from hachillesworld.collect.episode import EpisodeRecord
    from hachillesworld.collect.flush import BatchFlusher

    console.print(Panel("[bold cyan]HAchillesWorld Collect — Replay[/bold cyan]", expand=False))

    if not fallback_file.exists():
        console.print(f"[red]파일 없음:[/red] {fallback_file}")
        raise typer.Exit(1)

    raw_records = _load_jsonl(fallback_file)
    if not raw_records:
        console.print("[yellow]재전송할 레코드가 없습니다.[/yellow]")
        raise typer.Exit(0)

    console.print(f"[bold]재전송 대상:[/bold] {len(raw_records)}건 ({fallback_file})")

    records = [EpisodeRecord.from_dict(r) for r in raw_records]
    key = _api_key_from_env(api_key)
    flusher = BatchFlusher(api_key=key, ingest_url=ingest_url)

    total_sent = 0
    failed_raw: list[dict[str, Any]] = []
    batches = [records[i : i + batch_size] for i in range(0, len(records), batch_size)]

    with typer.progressbar(batches, label="재전송 중") as progress:
        for i, batch in enumerate(progress):
            sent = flusher.flush(batch)
            total_sent += sent
            if sent < len(batch):
                # 이 배치에서 실패한 레코드 추적
                failed_raw.extend(raw_records[i * batch_size : i * batch_size + len(batch)])

    flusher.close()

    console.print(f"\n[green]전송 완료:[/green] {total_sent}건")
    failed_count = len(records) - total_sent
    if failed_count:
        console.print(f"[yellow]전송 실패:[/yellow] {failed_count}건 (폴백 파일에 유지)")

    if delete_on_success and total_sent > 0:
        if failed_raw:
            # 실패 레코드만 남겨 파일을 덮어씀
            with fallback_file.open("w", encoding="utf-8") as f:
                for r in failed_raw:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            console.print(f"[dim]폴백 파일 갱신 ({len(failed_raw)}건 잔존):[/dim] {fallback_file}")
        else:
            fallback_file.unlink()
            console.print(f"[dim]폴백 파일 삭제 (전체 전송 성공):[/dim] {fallback_file}")


# ── collect stats ────────────────────────────────────────────────


@collect_app.command("stats")
def collect_stats(
    files: list[Path] = typer.Argument(..., help="분석할 JSONL 파일 경로 (1개 이상)"),
    theta_drift: float = typer.Option(
        0.15, "--drift-threshold", help="예측-관측 괴리 임계값 (분모 판단 기준)"
    ),
    min_improvement: float = typer.Option(
        0.05, "--min-improvement", help="자기 수정 최소 개선 비율"
    ),
    show_episodes: bool = typer.Option(False, "--episodes", help="에피소드 목록 출력"),
) -> None:
    """수집된 JSONL 로그 파일의 PD·SCR 관련 통계를 출력한다."""
    from hachillesworld.collect.episode import EpisodeRecord

    console.print(Panel("[bold cyan]HAchillesWorld Collect — Stats[/bold cyan]", expand=False))

    all_records: list[EpisodeRecord] = []
    for fp in files:
        if not fp.exists():
            console.print(f"[red]파일 없음:[/red] {fp}")
            raise typer.Exit(1)
        raw = _load_jsonl(fp)
        all_records.extend(EpisodeRecord.from_dict(r) for r in raw)
        console.print(f"  [dim]로드:[/dim] {fp.name}  ({len(raw)}건)")

    if not all_records:
        console.print("[yellow]레코드가 없습니다.[/yellow]")
        raise typer.Exit(0)

    _print_collect_stats(all_records, theta_drift, min_improvement, show_episodes)


# ── 공통 출력 헬퍼 ────────────────────────────────────────────────


def _print_ingest_stats(records: list[EpisodeRecord]) -> None:
    """ingest 전 유효성 및 간단 통계를 출력한다."""

    total = len(records)
    with_agent = sum(1 for r in records if r.agent_id)
    with_confidence = sum(1 for r in records if r.confidence is not None)
    with_prediction = sum(1 for r in records if r.predicted_next_state)
    flagged = sum(1 for r in records if r.internal_flag_raised)

    table = Table(title="레코드 필드 커버리지", show_header=True, header_style="bold blue")
    table.add_column("필드", style="cyan")
    table.add_column("건수", justify="right")
    table.add_column("비율", justify="right")
    for label, count in [
        ("agent_id 있음", with_agent),
        ("confidence 있음", with_confidence),
        ("predicted_state 있음", with_prediction),
        ("internal_flag_raised=True", flagged),
    ]:
        pct = f"{count / total * 100:.1f}%"
        table.add_row(label, str(count), pct)
    console.print(table)


def _print_collect_stats(
    records: list[EpisodeRecord],
    theta_drift: float,
    min_improvement: float,
    show_episodes: bool,
) -> None:
    from collections import Counter

    total = len(records)
    denom = [r for r in records if r.has_detectable_error(theta_drift)]
    self_corrected = [r for r in denom if r.is_self_correction(min_improvement)]
    scr = len(self_corrected) / len(denom) if denom else 0.0

    goal_achieved = sum(1 for r in records if r.goal_achieved)
    gar = goal_achieved / total if total else 0.0

    avg_tokens = sum(r.llm_tokens for r in records) / total if total else 0.0
    hitl_count = sum(1 for r in records if r.hitl_required)
    hitl_rate = hitl_count / total if total else 0.0

    avg_pd = None
    pd_values = [r.planning_depth_used for r in records if r.planning_depth_used is not None]
    if pd_values:
        avg_pd = sum(pd_values) / len(pd_values)

    domains = Counter(r.domain for r in records if r.domain)
    flag_types = Counter(ft for r in records for ft in r.flag_types)
    correction_sources = Counter(r.correction_source for r in records if r.correction_source)

    # ── 종합 지표 테이블 ─────────────────────────────────────────
    summary = Table(title=f"수집 통계 ({total}개 에피소드)", header_style="bold magenta")
    summary.add_column("지표", style="cyan")
    summary.add_column("값", justify="right")
    summary.add_column("상태")

    def _status(val: float, good: float, warn: float, lower_is_better: bool = False) -> str:
        if lower_is_better:
            return "🟢" if val <= good else "🟡" if val <= warn else "🔴"
        return "🟢" if val >= good else "🟡" if val >= warn else "🔴"

    summary.add_row("총 에피소드", str(total), "")
    summary.add_row("SCR 분모 (오류 에피소드)", str(len(denom)), "")
    summary.add_row("Self-Correction Rate", f"{scr:.3f}", _status(scr, 0.25, 0.10))
    summary.add_row("Goal Achievement Rate", f"{gar:.3f}", _status(gar, 0.90, 0.70))
    summary.add_row(
        "HITL 비율", f"{hitl_rate:.3f}", _status(hitl_rate, 0.05, 0.20, lower_is_better=True)
    )
    summary.add_row("평균 LLM 토큰", f"{avg_tokens:.0f}", "")
    if avg_pd is not None:
        summary.add_row("평균 Planning Depth", f"{avg_pd:.1f}", _status(avg_pd, 20, 5))
    console.print(summary)

    # ── 도메인 분포 ───────────────────────────────────────────────
    if domains:
        dom_table = Table(title="도메인 분포", header_style="bold blue", show_header=True)
        dom_table.add_column("도메인", style="cyan")
        dom_table.add_column("건수", justify="right")
        dom_table.add_column("비율", justify="right")
        for domain, count in domains.most_common():
            dom_table.add_row(domain, str(count), f"{count / total * 100:.1f}%")
        console.print(dom_table)

    # ── 플래그·수정 분포 ─────────────────────────────────────────
    if flag_types or correction_sources:
        detail = Table(title="플래그·수정 분포", header_style="bold blue")
        detail.add_column("유형", style="cyan")
        detail.add_column("구분")
        detail.add_column("건수", justify="right")
        for ft, count in flag_types.most_common():
            detail.add_row(ft, "플래그", str(count))
        for src, count in correction_sources.most_common():
            detail.add_row(src, "수정 출처", str(count))
        console.print(detail)

    # ── SCR Wilson 신뢰구간 ───────────────────────────────────────
    if len(denom) >= 10:
        import math

        n, p, z = len(denom), scr, 1.96
        denom_val = 1 + z**2 / n
        center = (p + z**2 / (2 * n)) / denom_val
        margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom_val
        ci_lo = max(0.0, center - margin)
        ci_hi = min(1.0, center + margin)
        console.print(f"\n  SCR 95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]  (n_denom={len(denom)})")
        if len(denom) < 100:
            console.print(
                f"  [yellow]⚠  분모 {len(denom)}개 — 최소 100개 권장 (신뢰도 낮음)[/yellow]"
            )

    # ── 에피소드 목록 ─────────────────────────────────────────────
    if show_episodes:
        ep_table = Table(title="에피소드 목록", header_style="bold", show_header=True)
        ep_table.add_column("episode_id", style="dim", no_wrap=True)
        ep_table.add_column("agent_id")
        ep_table.add_column("goal", justify="center")
        ep_table.add_column("flag", justify="center")
        ep_table.add_column("scr", justify="center")
        ep_table.add_column("tokens", justify="right")
        for r in records[:50]:
            ep_table.add_row(
                r.episode_id[:16] + "…",
                r.agent_id,
                "✅" if r.goal_achieved else "❌",
                "🚩" if r.internal_flag_raised else "",
                "✓" if r.is_self_correction(min_improvement) else "",
                str(r.llm_tokens),
            )
        if len(records) > 50:
            console.print(f"  [dim](처음 50개만 표시, 전체 {total}개)[/dim]")
        console.print(ep_table)


if __name__ == "__main__":
    app()
