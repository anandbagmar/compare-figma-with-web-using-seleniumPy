# tests/LoadFromFigma.py
from __future__ import annotations
from urllib.parse import urlparse, parse_qs, unquote

import json
import os
import re
import sys
from io import BytesIO
from typing import Tuple

# Ensure the project root (one level above /tests) is in the module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from PIL import Image

from applitools.images import Eyes, Target
from applitools.images import BatchInfo as images_BatchInfo
from applitools.common.config import Configuration
from applitools.common import RectangleSize

# Optional: match level enum if present
try:
    from applitools.common import MatchLevel  # type: ignore
except Exception:
    MatchLevel = None  # gracefully degrade if not available

from src.utils.ApplitoolsResultsSerializer import serialize_test_results

# -------------------------
# Utilities
# -------------------------
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

_FIGMA_URL_RE = re.compile(
    r"""
    ^https?://(?:www\.)?figma\.com/(?:file|design)/(?P<file_key>[A-Za-z0-9]+)
    /[^?]+
    (?:\?.*?node-id=(?P<node_id>[^&#]+))?
    """,
    re.VERBOSE | re.IGNORECASE,
)

def _normalize_node_id(node_id: str) -> str:
    # Figma URLs often show node-id as "17-4"; API needs "17:4".
    # Also handle percent-encoded ":" (e.g., 17%3A4).
    nid = unquote(node_id.strip())
    # For Figma node ids, hyphens stand in for colons. Replace all.
    return nid.replace("-", ":")

def _parse_figma_url(figma_url: str) -> Tuple[str, str]:
    """
    Extract file_key and node_id from a Figma URL.

    Supports:
      https://www.figma.com/file/<FILE_KEY>/...?...node-id=<NODE_ID>
      https://www.figma.com/design/<FILE_KEY>/...?...node_id=<NODE_ID>
    """

    m = _FIGMA_URL_RE.match(figma_url.strip())
    if not m:
        raise ValueError(f"Invalid Figma URL: {figma_url!r}")
    file_key = m.group("file_key")

    # Parse query robustly and accept node-id or node_id (case-insensitive)
    q = parse_qs(urlparse(figma_url.strip()).query)
    node_id = None
    for k, v in q.items():
        if k.lower() in ("node-id", "node_id"):
            node_id = v[0] if v else None
            break

    if not file_key or not node_id:
        raise ValueError(
            "Could not parse file key or node id from Figma URL. "
            "Ensure it contains ?node-id=... or ?node_id=..."
        )

    return file_key, _normalize_node_id(node_id)

def _safe_setattr(obj, name: str, value) -> None:
    """Set attribute on obj if it exists; ignore otherwise."""
    if hasattr(obj, name):
        setattr(obj, name, value)

# -------------------------
# Upload a Figma node image to Applitools Images.
# -------------------------
def upload_figma_to_applitools(
    *,
    figma_url: str,
    figma_token: str,
    applitools_api_key: str,
    applitools_server_url: str,
    images_batch_name_suffix: str = " - Check with Figma", 
    images_batch_id: str,
    viewport: Tuple[int, int],
    match_level: str,
    ignore_displacement: bool = False,
) -> dict:

    # Resolve file key & node id
    if figma_url:
        try:
            file_key, node_id = _parse_figma_url(figma_url)
        except RuntimeError as e:
            raise ValueError("Provide a valid figma_url")

    # FIGMA: Fetch file (for app/project name)
    file_endpoint = f"https://api.figma.com/v1/files/{file_key}"
    file_resp = requests.get(file_endpoint, headers={"X-Figma-Token": figma_token})
    file_resp.raise_for_status()
    app_name = file_resp.json().get("name", "<unnamed project>")

    # FIGMA: Fetch node (dimensions & name)
    nodes_endpoint = f"https://api.figma.com/v1/files/{file_key}/nodes"
    node_resp = requests.get(
        nodes_endpoint,
        headers={"X-Figma-Token": figma_token},
        params={"ids": node_id}
    )
    node_resp.raise_for_status()
    node_doc = node_resp.json()["nodes"][node_id]["document"]
    test_name = node_doc.get("name", "<unnamed>")
    if viewport == (0, 0):
        viewport = (int(node_doc["absoluteBoundingBox"]["width"]), int(node_doc["absoluteBoundingBox"]["height"]))
    use_width, use_height = viewport

    baseline_env_name = f"{app_name}_{test_name}_{str(use_width).split('.', 1)[0]}"

    # FIGMA: Get export URL and download PNG (scale=2 for quality)
    images_endpoint = f"https://api.figma.com/v1/images/{file_key}"
    images_resp = requests.get(
        images_endpoint,
        headers={"X-Figma-Token": figma_token},
        params={"ids": node_id, "format": "png", "scale": 2}
    )
    images_resp.raise_for_status()
    image_url = images_resp.json()["images"].get(node_id)
    if not image_url:
        raise RuntimeError(f"No image URL returned for node {node_id}")

    img_resp = requests.get(image_url)
    img_resp.raise_for_status()
    figma_image = Image.open(BytesIO(img_resp.content))

    # Resize while preserving aspect ratio to target width
    actual_width, actual_height = figma_image.size
    w_percent = use_width / float(actual_width)
    target_height = int(float(actual_height) * w_percent)
    resized_img = figma_image.resize((use_width, target_height))

    # APPLITOOLS: configure eyes
    eyes = Eyes()
    config = Configuration()

    images_batchInfo = images_BatchInfo()
    images_batchInfo.name = f"{app_name}{images_batch_name_suffix or ''}" 
    images_batchInfo.id = images_batch_id
    config.batch = images_batchInfo

    config.api_key = applitools_api_key
    config.server_url = applitools_server_url

    config.app_name = app_name
    config.test_name = test_name
    config.host_app = "figma"
    config.baseline_env_name = baseline_env_name
    config.viewport_size = RectangleSize(width=use_width, height=use_height)

    # Optional matching configuration
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

    _safe_setattr(config, "ignore_displacements", _parse_bool(ignore_displacement, False))

    eyes.set_configuration(config)

    # Execute check
    all_test_results = None
    try:
        print("\n" + "-" * 75 + "\n", file=sys.stderr)
        print("LoadFromFigma.py - Starting script execution", file=sys.stderr)
        if figma_url:
            print(f"FIGMA_URL              : {figma_url}", file=sys.stderr)
        print(f"App Name               : {app_name}", file=sys.stderr)
        print(f"Test Name              : {test_name}", file=sys.stderr)
        print(f"Node                   : {node_id}", file=sys.stderr)
        print(f"Original dimensions    : {actual_width}x{actual_height}", file=sys.stderr)
        print(f"Using dimensions       : {use_width}x{use_height}", file=sys.stderr)
        print(f"Baseline Env Name      : {baseline_env_name}", file=sys.stderr)
        if applitools_server_url:
            print(f"Applitools Server URL  : {applitools_server_url}", file=sys.stderr)

        eyes.open()
        print(f"Checking Figma Node {node_id} at {use_width}x{use_height}", file=sys.stderr)
        eyes.check("Figma Node Image", Target.image(resized_img))
        all_test_results = eyes.close(False)

        applitools_result = serialize_test_results(all_test_results)
        print("📊 Status of uploading Figma image to Applitools:", file=sys.stderr)
        print(json.dumps(applitools_result, indent=4), file=sys.stderr)
    except Exception as e:
        print(f"Abort the test: {e}", file=sys.stderr)
        eyes.abort()

    print("-" * 75 + "\n", file=sys.stderr)

    # Return a structured summary (also printed by CLI)
    summary = {
        "app_name": app_name,
        "test_name": test_name,
        "viewport": {"width": use_width, "height": use_height},
        "baseline_env_name": baseline_env_name,
        "upload_from_figma_results": {
            "name": getattr(all_test_results, "name", "N/A"),
            "status": getattr(getattr(all_test_results, "status", None), "value", "N/A"),
            "url": getattr(all_test_results, "url", None),
            "all_test_results": serialize_test_results(all_test_results) if all_test_results else None,
        },
    }
    return summary
