#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main orchestrator for:
  - Loading config (Config.json) & test rows (TestData.csv)
  - Deciding FIGMA_ONLY vs. compare mode
  - Routing each row to: LoadFromFigma / TestInBrowser / TestAnImage
  - Normalizing booleans, viewport, match level, and per-row flags
  - Clear, structured logging & error handling

Assumptions come from the repo README (paths/columns): 
  tests/resources/Config.json
  tests/resources/TestData.csv
  CSV columns: FIGMA_URL, APP_URL, VIEWPORT_SIZE, IGNORE_DISPLACEMENT, MATCH_LEVEL, SKIP
"""

from __future__ import annotations
from urllib.parse import urlparse, unquote
import argparse
import csv
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import uuid

# -------------------------
# Logging
# -------------------------
def _make_logger(verbosity: int) -> logging.Logger:
    level = logging.DEBUG if verbosity > 0 else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("main")


# -------------------------
# Helpers / parsing
# -------------------------
_TRUE_LIKE = {"true", "1", "yes", "y", "on"}
_FALSE_LIKE = {"false", "0", "no", "n", "off"}
_COMPARE_WITH_FIGMA_BATCH_ID = str(uuid.uuid4())
_FIGMA_BATCH_ID = str(uuid.uuid4())

def _is_http_url(s: str) -> bool:
    return urlparse(s.strip()).scheme in ("http", "https")

def _as_local_path(uri_or_path: str) -> str:
    raw = uri_or_path.strip()
    parsed = urlparse(raw)

    # Leave http/https alone
    if parsed.scheme in ("http", "https"):
        return raw

    # file: URIs -> filesystem path
    if parsed.scheme == "file":
        candidate = ""
        if parsed.netloc and parsed.netloc.lower() != "localhost":
            candidate = f"/{parsed.netloc}{parsed.path}"
        else:
            candidate = parsed.path or raw[5:]
        local_path = unquote(candidate)
        if os.name == "nt" and local_path.startswith("/") and len(local_path) > 2 and local_path[2] == ":":
            local_path = local_path.lstrip("/")
        return str(Path(local_path).expanduser().resolve())

    # Plain path -> normalize
    return str(Path(raw).expanduser().resolve())

def _exists_file(s: str) -> bool:
    try:
        return Path(s).expanduser().resolve().exists()
    except Exception:
        return False
    
def parse_bool(value: object, default: bool = False) -> bool:
    """
    Accepts many user-friendly representations:
    true/True/TRUE/yes/YES/1 -> True
    Anything else (including empty/None) -> False (unless default is given)
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    if s in _TRUE_LIKE:
        return True
    if s in _FALSE_LIKE:
        return False
    # Fall back to default if it's something unexpected
    return default

def parse_match_level(value: Optional[str]) -> Optional[str]:
    """
    Normalize Applitools MatchLevel token to lowercase;
    return None if empty -> let downstream code decide default.
    Typical values per README: 'layout' | 'strict' | 'exact'
    """
    if not value:
        return None
    return str(value).strip().lower()

def parse_viewport(value: str) -> Optional[Tuple[int, int]]:
    """
    'USE_SOURCE' -> None (let downstream use image-native size)
    '1600x900'   -> (1600, 900)
    """
    if not value:
        return None
    v = value.strip()
    if v.upper() == "USE_SOURCE":
        return int(0), int(0)
    if "x" in v.lower():
        try:
            w, h = v.lower().split("x", 1)
            return int(w.strip()), int(h.strip())
        except Exception:
            pass
    raise ValueError(f"Invalid VIEWPORT_SIZE: {value!r}. Expected 'USE_SOURCE' or 'WIDTHxHEIGHT' (e.g., '1600x900').")


# -------------------------
# IO
# -------------------------
def load_json(path: Path) -> Dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)

def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        rows = [dict({k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}) for row in reader]
        return rows


# -------------------------
# Data models
# -------------------------
@dataclass
class Config:
    FIGMA_TOKEN: str
    APPLITOOLS_API_KEY: str
    APPLITOOLS_SERVER_URL: Optional[str] = None
    HEADLESS: bool = True
    FIGMA_ONLY: bool = False

    @staticmethod
    def from_dict(d: Dict[str, str]) -> "Config":
        return Config(
            FIGMA_TOKEN=d.get("FIGMA_TOKEN", "").strip(),
            APPLITOOLS_API_KEY=d.get("APPLITOOLS_API_KEY", "").strip(),
            APPLITOOLS_SERVER_URL=d.get("APPLITOOLS_SERVER_URL", "").strip() or None,
            HEADLESS=parse_bool(d.get("HEADLESS"), default=True),
            FIGMA_ONLY=parse_bool(d.get("FIGMA_ONLY"), default=False),
        )

@dataclass
class TestRow:
    figma_url: str
    app_url: str
    viewport: Optional[Tuple[int, int]]  # None => USE_SOURCE
    ignore_displacement: bool
    match_level: Optional[str]
    skip: bool

    @staticmethod
    def from_dict(d: Dict[str, str]) -> "TestRow":
        figma_url = d.get("FIGMA_URL", "").strip()       
        app_url = d.get("APP_URL", "").strip()
        if not figma_url:
            raise ValueError("CSV row missing required field: FIGMA_URL")
        if not app_url:
            raise ValueError("CSV row missing required field: APP_URL")

        vp_raw = d.get("VIEWPORT_SIZE", "").strip()
        viewport = parse_viewport(vp_raw) if vp_raw else None

        ignore_displacement = parse_bool(d.get("IGNORE_DISPLACEMENT", "false"))
        match_level = parse_match_level(d.get("MATCH_LEVEL", ""))
        skip = parse_bool(d.get("SKIP", "false"))
        # If the value looks like a comment (starts with #, // or /*), raise a Skip signal.
        cleaned = figma_url.strip()
        if cleaned.startswith("#") or cleaned.startswith("//") or cleaned.startswith("/*"):
            # treat this as a skipped row
            skip = True

        return TestRow(
            figma_url=figma_url,
            app_url=app_url,
            viewport=viewport,
            ignore_displacement=ignore_displacement,
            match_level=match_level,
            skip=skip,
        )


# -------------------------
# Adapters to your existing modules
# -------------------------
# NOTE:
# Update these three functions if your current method names differ.
# They are isolated here on purpose so the rest of Main.py stays clean.

def _upload_from_figma_adapter(
    figma_url: str, 
    *, 
    match_level: Optional[str],
    ignore_displacement: bool,
    cfg: Config,
    logger: logging.Logger,
    viewport: Tuple[int, int]
) -> Dict[str, Any]:
    """
    Calls your existing Figma->Applitools uploader (tests/LoadFromFigma.py).
    If your module exposes a different function name/signature, tweak here only.
    """
    try:
        from LoadFromFigma import upload_figma_to_applitools  # type: ignore
    except Exception as e:
        logger.error("Cannot import LoadFromFigma.upload_figma_to_applitools. Please update _upload_from_figma_adapter().")
        raise

    summary = upload_figma_to_applitools(
        figma_url=figma_url,
        figma_token=cfg.FIGMA_TOKEN,
        applitools_api_key=cfg.APPLITOOLS_API_KEY,
        applitools_server_url=cfg.APPLITOOLS_SERVER_URL,
        images_batch_id=_FIGMA_BATCH_ID,
        viewport=viewport,
        match_level=match_level,
        ignore_displacement=ignore_displacement
    )
    return summary


def _compare_in_browser_adapter(
    *, 
    app_name: str, 
    test_name: str, 
    viewport: Tuple[int, int],
    baseline_env_name: str, 
    app_url: str, 
    headless: bool,
    match_level: str, 
    ignore_displacement: bool, 
    cfg: Config, 
    logger: logging.Logger
) -> Dict[str, Any]:
    """
    Calls your existing Selenium+Applitools flow (tests/TestInBrowser.py).
    Update here if the symbol names differ.
    """
    try:
        from TestInBrowser import run_visual_check  # type: ignore
    except Exception:
        # Fallback to a common alt name:
        try:
            from TestInBrowser import main as run_visual_check  # type: ignore
        except Exception as e:
            logger.error("Cannot import TestInBrowser.run_visual_check (or .main). Please update _compare_in_browser_adapter().")
            raise

    summary = run_visual_check(
        app_name=app_name,
        test_name=test_name,
        viewport=viewport,
        baseline_env_name=baseline_env_name,
        app_url=app_url,
        applitools_api_key=cfg.APPLITOOLS_API_KEY,
        applitools_server_url=cfg.APPLITOOLS_SERVER_URL,
        headless=cfg.HEADLESS,
        match_level=match_level,
        ignore_displacement=ignore_displacement,
        batch_id=_COMPARE_WITH_FIGMA_BATCH_ID,
    )
    return summary


def _compare_image_adapter(
    *,
    app_name: str, 
    test_name: str, 
    baseline_env_name: str,
    viewport: Tuple[int, int],
    image_path: str, 
    match_level: str, 
    ignore_displacement: bool, 
    cfg: Config, 
    logger: logging.Logger
) -> Dict[str, Any]:
    
    """
    Calls your existing local-image+Applitools flow (tests/TestAnImage.py).
    Update here if the symbol names differ.
    """
    try:
        from TestAnImage import run_image_check  # type: ignore
    except Exception:
        try:
            from TestAnImage import main as run_image_check  # type: ignore
        except Exception as e:
            logger.error("Cannot import TestAnImage.run_image_check (or .main). Please update _compare_image_adapter().")
            raise

    run_image_check(
        app_name = app_name,
        test_name = test_name,
        viewport=viewport,
        baseline_env_name = baseline_env_name,
        image_path=image_path,
        applitools_api_key=cfg.APPLITOOLS_API_KEY,
        applitools_server_url=cfg.APPLITOOLS_SERVER_URL,
        match_level=match_level,
        ignore_displacement=ignore_displacement,
        batch_id=_COMPARE_WITH_FIGMA_BATCH_ID,
    )


# -------------------------
# Execution
# -------------------------
# def _is_url(s: str) -> bool:
#     return s.lower().startswith(("http://", "https://"))

def _exists_file(s: str) -> bool:
    try:
        return Path(s).expanduser().resolve().exists()
    except Exception:
        return False

def run_row(row: TestRow, cfg: Config, logger: logging.Logger, dry_run: bool = False) -> None:
    if row.skip:
        logger.info("")
        logger.info("⏭️  SKIP=true -> skipping row: %s", row)
        return

    logger.info("▶️   FIGMA               : %s", row.figma_url)
    logger.info("    APP                 : %s", row.app_url)
    if (row.viewport== (0,0)):
        logger.info("    VIEWPORT            : USE_SOURCE (from Figma)")
    else:
        logger.info("    VIEWPORT            : %s", row.viewport if row.viewport else "USE_SOURCE")
    logger.info("    IGNORE_DISPLACEMENT : %s | MATCH_LEVEL: %s", row.ignore_displacement, row.match_level)

    if cfg.FIGMA_ONLY:
        logger.info("FIGMA_ONLY=true -> uploading Figma design(s) to Applitools without comparing in browser.")
        if dry_run:
            return
        _upload_from_figma_adapter(
            row.figma_url,
            match_level=row.match_level,
            ignore_displacement=row.ignore_displacement,
            cfg=cfg,
            logger=logger,
            viewport=row.viewport
        )
        return

    if not cfg.FIGMA_ONLY:
        # FIGMA_ONLY = True: perform comparison
        if dry_run:
            return
        summary = _upload_from_figma_adapter(
            row.figma_url,
            match_level=row.match_level,
            ignore_displacement=row.ignore_displacement,
            cfg=cfg,
            logger=logger,
            viewport=row.viewport
        )
        
        app_raw = row.app_url.strip()
        # Not http(s): treat as a local file path or file: URI
        local_path = _as_local_path(app_raw)   # handles file: and plain paths
        
        if _is_http_url(app_raw):
            # Browser compare (URL)
            logger.info("Mode: Compare in Browser (Selenium)")
            if dry_run:
                return
            _compare_in_browser_adapter(
                app_name = summary["app_name"],
                test_name = summary["test_name"],
                viewport = summary["viewport"],
                baseline_env_name = summary["baseline_env_name"],
                app_url=app_raw,
                headless=cfg.HEADLESS,
                match_level=row.match_level,
                ignore_displacement=row.ignore_displacement,
                cfg=cfg,
                logger=logger,
            )
            return
        elif _exists_file(local_path):
            # Local image compare (PNG path)
            logger.info("Mode: Compare a Local Image file with Figma")
            if dry_run:
                return
            _compare_image_adapter(
                app_name = summary["app_name"],
                test_name = summary["test_name"],
                viewport = summary["viewport"],
                baseline_env_name = summary["baseline_env_name"],
                image_path=local_path,
                match_level=row.match_level,
                ignore_displacement=row.ignore_displacement,
                cfg=cfg,
                logger=logger,
            )
        else:
            logger.error(
                "Skipping row: APP_URL is neither a URL nor an existing file path: %r. "
                "Expected a web URL or FULL_PATH_TO_PNG_FILE.",
                row.app_url,
            )
            return


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Compare Figma with Web (or local images) using Selenium + Applitools")
    default_root = Path(__file__).resolve().parent
    parser.add_argument("--config", default=str(default_root / "resources" / "Config.json"), help="Path to Config.json")
    parser.add_argument("--data",   default=str(default_root / "resources" / "TestData.csv"), help="Path to TestData.csv")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (-v)")
    parser.add_argument("--dry-run", action="store_true", help="Parse & log but do not execute any test actions")

    args = parser.parse_args(argv)
    logger = _make_logger(args.verbose)

    cfg_dict = load_json(Path(args.config))
    cfg = Config.from_dict(cfg_dict)

    # Minimal sanity checks for credentials
    if not cfg.FIGMA_TOKEN:
        logger.error("FIGMA_TOKEN is required in Config.json")
        return 2
    if not cfg.APPLITOOLS_API_KEY:
        logger.error("APPLITOOLS_API_KEY is required in Config.json")
        return 2

    # Surface HEADLESS/FIGMA_ONLY decisions up-front
    logger.info("HEADLESS=%s | FIGMA_ONLY=%s | APPLITOOLS_SERVER_URL=%s", cfg.HEADLESS, cfg.FIGMA_ONLY, cfg.APPLITOOLS_SERVER_URL or "(default)")

    # Load CSV rows
    rows_raw = load_csv(Path(args.data))
    if not rows_raw:
        logger.warning("No rows found in TestData.csv -> nothing to do.")
        return 0

    # Parse rows with validation
    rows: List[TestRow] = []
    for i, rd in enumerate(rows_raw, start=1):
        try:
            rows.append(TestRow.from_dict(rd))
        except Exception as e:
            logger.error("Row %d invalid: %s", i, e)
            return 3

    # Execute rows (stop-on-fail)
    for i, row in enumerate(rows, start=1):
        try:
            print("")
            print("=" * 75 + "\n", file=sys.stderr)
            print("")
            logger.info("──────── Row %d/%d ────────", i, len(rows))
            run_row(row, cfg, logger, dry_run=args.dry_run)
        except Exception as e:
            logger.exception("❌ Row %d failed: %s", i, e)
            print("")
            print("-" * 75 + "\n", file=sys.stderr)

    logger.info("✅ All rows completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
