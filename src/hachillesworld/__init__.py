"""HAchillesWorld — World Model 진단 및 최적화 플랫폼."""

from hachillesworld.collect import (
    EpisodeContext,
    EpisodeRecord,
    LogCollector,
    StudyClient,
)
from hachillesworld.core.client import HAchillesWorldClient
from hachillesworld.core.instrument import instrument
from hachillesworld.core.models import DiagnosticReport, LawsDomain, Level

__version__ = "0.1.0"
__all__ = [
    # 기존
    "HAchillesWorldClient",
    "DiagnosticReport",
    "Level",
    "LawsDomain",
    "instrument",
    # Log Collector SDK
    "EpisodeRecord",
    "EpisodeContext",
    "LogCollector",
    "StudyClient",
]
