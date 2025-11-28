"""Utility to persist reasoning traces and evaluation artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .utils import ensure_directory


class RunLogger:
    """Simple logger that writes JSON artifacts per question/run."""

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = Path(run_dir)
        ensure_directory(self.run_dir)
        self.traces_dir = self.run_dir / "reasoning_traces"
        ensure_directory(self.traces_dir)
        self.metadata_file = self.run_dir / "metadata.json"

    def save_trace(self, question_id: str, trace: Dict[str, Any]) -> Path:
        """Persist a reasoning trace to disk."""
        filepath = self.traces_dir / f"{question_id}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(trace, f, indent=2, ensure_ascii=False)
        return filepath

    def append_metadata(self, record: Dict[str, Any]) -> None:
        """Append a record to metadata.json"""
        existing = []
        if self.metadata_file.exists():
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
        existing.append(record)
        with open(self.metadata_file, "w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
