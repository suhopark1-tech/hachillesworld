"""HAchillesWorld — World Model 진단 및 최적화 플랫폼."""

from hachillesworld.core.client import HAchillesWorldClient
from hachillesworld.core.models import DiagnosticReport, Level, LawsDomain
from hachillesworld.core.instrument import instrument
from hachillesworld.collect import (
    EpisodeRecord,
    EpisodeContext,
    LogCollector,
    StudyClient,
)

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
