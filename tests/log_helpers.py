from datetime import UTC, datetime
import json
from pathlib import Path

from src.config import LoggingSettings


def logging_settings_for(tmp_path: Path, *, format: str = "text") -> LoggingSettings:
    return LoggingSettings(
        enabled=True,
        level="INFO",
        format=format,
        redact=True,
        directory=str(tmp_path / "logs"),
    )


def read_log(tmp_path: Path, level: str) -> str:
    log_path = (
        tmp_path
        / "logs"
        / datetime.now(UTC).date().isoformat()
        / f"{level.lower()}.log"
    )
    return log_path.read_text(encoding="utf-8")


def log_path(tmp_path: Path, level: str) -> Path:
    return (
        tmp_path
        / "logs"
        / datetime.now(UTC).date().isoformat()
        / f"{level.lower()}.log"
    )


def read_debug_events(tmp_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in read_log(tmp_path, "DEBUG").splitlines()
        if line.strip()
    ]
