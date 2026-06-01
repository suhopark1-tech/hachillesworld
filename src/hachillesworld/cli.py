"""HAchillesWorld CLI — hachillesworld 명령어 진입점."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app     = typer.Typer(name="hachillesworld", help="HAchillesWorld — World Model 진단 및 최적화 CLI")
console = Console()


@app.command()
def scan(
    logs: Optional[Path] = typer.Option(None, "--logs", "-l", help="에이전트 로그 파일 경로 (JSON)"),
    config: Optional[Path] = typer.Option(None, "--config", "-c", help="에이전트 설정 파일 경로 (JSON)"),
    agent_name: str = typer.Option("unnamed-agent", "--name", "-n", help="에이전트 이름"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="리포트 저장 경로 (JSON)"),
) -> None:
    """에이전트 시스템을 진단하고 리포트를 출력한다."""
    from hachillesworld.core.client import HAchillesWorldClient

    console.print(Panel("[bold cyan]HAchillesWorld Scan[/bold cyan]", expand=False))

    log_data    = json.loads(logs.read_text(encoding="utf-8"))    if logs   else []
    config_data = json.loads(config.read_text(encoding="utf-8")) if config else {}

    with HAchillesWorldClient() as client:
        report = client.scan(logs=log_data, config=config_data, agent_name=agent_name)

    # 결과 출력
    console.print(f"\n[bold]에이전트:[/bold] {report.agent_name}")
    console.print(f"[bold]현재 Level:[/bold] {report.level_label}  ×  {report.laws_domain.value.title()} Laws")

    table = Table(title="진단 점수", show_header=True, header_style="bold magenta")
    table.add_column("카테고리", style="cyan")
    table.add_column("점수", justify="right")
    table.add_column("상태")
    for cat, score in [
        ("World Model 품질", report.world_model_quality.score),
        ("에이전시 수준",    report.agency_level.score),
        ("운영 건전성",      report.operational_health.score),
        ("종합",             report.composite_score),
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
            "agent_name":      report.agent_name,
            "level":           report.level_label,
            "laws_domain":     report.laws_domain.value,
            "composite_score": report.composite_score,
            "recommendations": report.recommendations,
        }
        output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"\n[green]리포트 저장 완료:[/green] {output}")


@app.command()
def optimize(
    report_file: Path = typer.Argument(..., help="scan 결과 JSON 파일"),
    target_level: Optional[str] = typer.Option(None, "--target", "-t", help="목표 Level (L2 또는 L3)"),
) -> None:
    """진단 리포트 기반 최적화 로드맵을 출력한다."""
    from hachillesworld.core.client import HAchillesWorldClient
    from hachillesworld.optimize.roadmap import RoadmapGenerator
    from hachillesworld.core.models import Level, LawsDomain

    console.print(Panel("[bold green]HAchillesWorld Optimize[/bold green]", expand=False))

    data   = json.loads(report_file.read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    app()
