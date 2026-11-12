"""Robô de monitoramento de focos de incêndio (NASA FIRMS)."""

from firms_monitor.application import ExecutionReport, FireMonitorService, PeriodicRunner
from firms_monitor.bootstrap import build_fire_monitor
from firms_monitor.config import Settings
from firms_monitor.domain import RiskLevel

__all__ = [
    "ExecutionReport",
    "FireMonitorService",
    "PeriodicRunner",
    "RiskLevel",
    "Settings",
    "build_fire_monitor",
]

__version__ = "1.2.0"
