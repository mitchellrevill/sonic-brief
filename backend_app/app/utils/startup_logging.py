"""Simple helpers for structured startup logging."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Optional


@dataclass
class _PhaseRecord:
    """Tracking information for a startup phase."""

    name: str
    start: float
    end: Optional[float] = None
    description: Optional[str] = None

    @property
    def duration_ms(self) -> float:
        finish = self.end if self.end is not None else time.perf_counter()
        return (finish - self.start) * 1000


class StartupLogger:
    """Lightweight logger that records startup phases and timing."""

    def __init__(self, logger: logging.Logger):
        self._logger = logger
        self._startup_start: Optional[float] = None
        self._phases: Dict[str, _PhaseRecord] = {}
        self._phase_order: list[str] = []

    def start_startup(self) -> None:
        """Record the beginning of startup."""
        self._startup_start = time.perf_counter()
        self._phases.clear()
        self._phase_order.clear()
        self._logger.info("🚀 Starting Sonic Brief API application startup...")

    def start_phase(self, phase_name: str, description: Optional[str] = None) -> None:
        """Mark the beginning of a startup phase."""
        now = time.perf_counter()
        record = _PhaseRecord(name=phase_name, start=now, description=description)
        self._phases[phase_name] = record
        self._phase_order.append(phase_name)

        self._logger.info(f"🏁 Entering startup phase: {phase_name}")
        if description:
            self._logger.info(f"� {description}")

    def end_phase(self, phase_name: str) -> None:
        """Mark the completion of a startup phase."""
        record = self._phases.get(phase_name)
        if record is None or record.end is not None:
            return

        record.end = time.perf_counter()
        self._logger.info(f"✅ Phase '{phase_name}' completed in {record.duration_ms:.1f}ms")

    def log_config_info(self, config: object) -> None:
        """Emit a short configuration summary useful during startup."""
        self._logger.info("⚙️ Configuration Summary:")

        storage_url = getattr(config, "azure_storage_account_url", None)
        storage_container = getattr(config, "azure_storage_recordings_container", None)
        if storage_url:
            self._logger.info(f"  Storage Account: {storage_url}")
        if storage_container:
            self._logger.info(f"  Recordings Container: {storage_container}")

    def finish_startup(self, success: bool = True) -> None:
        """Emit a final summary once startup has completed."""
        if self._startup_start is None:
            return

        total_time_ms = (time.perf_counter() - self._startup_start) * 1000
        prefix = "🎉" if success else "⚠️"
        self._logger.info(f"{prefix} Application startup completed in {total_time_ms:.1f}ms")

        if not self._phase_order:
            return

        self._logger.info("📈 Startup Summary:")
        for phase_name in self._phase_order:
            record = self._phases[phase_name]
            self._logger.info(f"  - {phase_name}: {record.duration_ms:.1f}ms")


@lru_cache(maxsize=1)
def get_startup_logger() -> StartupLogger:
    """Return a cached instance so phases share the same logger."""
    return StartupLogger(logging.getLogger("startup"))
