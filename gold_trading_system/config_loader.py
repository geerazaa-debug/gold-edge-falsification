"""
Thin YAML-loading layer shared by core/strategies and core/risk_engine.
Kept intentionally dumb (just dict access via dataclasses.field defaults
matched to the YAML keys) -- the YAML files in config/ are the single
source of truth; these loaders just give type-checked, IDE-navigable
access to them instead of raw dict lookups scattered through the code.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).resolve().parent / "config"


def load_yaml(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)
