"""
Threshold loading utilities for suitability scoring.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_THRESHOLDS_PATH = PROJECT_ROOT / "configs" / "thresholds.yaml"


def load_thresholds(path: Path | str | None = DEFAULT_THRESHOLDS_PATH) -> Dict[str, Any]:
    """
    Load threshold definitions from a YAML file.
    """
    if path is None:
        path = DEFAULT_THRESHOLDS_PATH

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Thresholds file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError("Thresholds file must contain a dictionary at the root.")

    return data


def get_property_thresholds(
    thresholds: Mapping[str, Any],
    property_name: str
) -> Dict[str, Any]:
    """
    Retrieve thresholds for a specific property.
    """
    try:
        prop_thresholds = thresholds[property_name]
    except KeyError as exc:
        raise KeyError(
            f"Thresholds for property '{property_name}' were not found."
        ) from exc

    if not isinstance(prop_thresholds, dict):
        raise ValueError(
            f"Thresholds for property '{property_name}' must be a dictionary."
        )

    return prop_thresholds
