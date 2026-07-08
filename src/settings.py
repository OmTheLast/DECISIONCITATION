from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
INDEX_DIR = DATA_DIR / "index"

SOURCE_CONFIG = CONFIG_DIR / "sources.json"
PDF_PATH = RAW_DIR / "ifab-laws-2026-27.pdf"
CHUNKS_PATH = INDEX_DIR / "chunks.json"

