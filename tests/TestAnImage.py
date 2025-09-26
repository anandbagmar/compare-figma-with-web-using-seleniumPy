from __future__ import annotations

import json
import os
import sys
from typing import Tuple

# Ensure the project root (one level above /tests) is in the module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from applitools.images import Eyes, Target, Configuration
from applitools.images import BatchInfo as images_BatchInfo
from applitools.common import RectangleSize

# Optional MatchLevel (older SDKs may differ)
try:
    from applitools.common import MatchLevel  # type: ignore
except Exception:
    MatchLevel = None

from src.utils.ApplitoolsResultsSerializer import serialize_test_results

# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────
_TRUE_LIKE = {"true", "1", "yes", "y", "on"}
_FALSE_LIKE = {"false", "0", "no", "n", "off"}

def _parse_bool(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in _TRUE_LIKE:
        return True
    if s in _FALSE_LIKE:
        return False
    return default

def _safe_setattr(obj, name: str, value) -> None:
    if hasattr(obj, name):
        setattr(obj, name, value)

# ──────────────────────────────────────────────────────────────────────────────
# Public API used by Main.py
# ──────────────────────────────────────────────────────────────────────────────
def run_image_check(
    *,
    app_name: str,
    test_name: str,
    viewport: Tuple[int, int],
    baseline_env_name: str,
    image_path: str,
    applitools_api_key: str,
    applitools_server_url: str,
    match_level: str,
    ignore_displacement: bool,
    batch_name_suffix: str = " - Check against Figma",
    batch_id: str,
) -> dict:
    if not image_path or not image_path.strip():
        raise ValueError("image_path is required.")

    # ─── Applitools Eyes (Images) ───────────────────────────────────────
    eyes = Eyes()
    config = Configuration()
    config.api_key = applitools_api_key
    config.server_url = applitools_server_url

    config.app_name = app_name
    config.test_name = test_name
    config.baseline_env_name = baseline_env_name

    # Optional settings
    _safe_setattr(config, "ignore_displacements", _parse_bool(ignore_displacement, False))
    if match_level and MatchLevel:
        ml = str(match_level).strip().lower()
        ml_map = {
            "exact":   getattr(MatchLevel, "Exact", None),
            "strict":  getattr(MatchLevel, "Strict", None),
            "layout":  getattr(MatchLevel, "Layout", None),
            "content": getattr(MatchLevel, "Content", None),
        }
        mapped = ml_map.get(ml)
        if mapped is not None:
            _safe_setattr(config, "match_level", mapped)

    images_batchInfo = images_BatchInfo()
    images_batchInfo.name = f"{app_name}{batch_name_suffix or ''}" 
    images_batchInfo.id = batch_id
    config.batch = images_batchInfo
    
    # Viewport (Images SDK prefers RectangleSize)
    config.viewport_size = RectangleSize(width=viewport["width"], height=viewport["height"])
    eyes.set_configuration(config)

    # ─── Run the test ───────────────────────────────────────────────────
    all_test_results = None
    applitools_result = None

    eyes.open()
    # For Images SDK, Target.image() can take a path
    eyes.check("Full Image", Target.image(image_path))
    all_test_results = eyes.close(False)
    applitools_result = serialize_test_results(all_test_results)

    # Friendly stderr for humans
    print("📊 Status of comparison against Figma:", file=sys.stderr)
    print(json.dumps(applitools_result, indent=4), file=sys.stderr)

    # Summary for programmatic use / CLI stdout
    summary = {
        "app_name": app_name,
        "test_name": test_name,
        "baseline_env_name": baseline_env_name,
        "status": applitools_result,
        "viewport_size": viewport,
        "app_url": image_path,
        "all_test_results": applitools_result,
    }
    return summary