from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
from pypdf import PdfReader

from .settings import CHUNKS_PATH, PDF_PATH, RAW_DIR, SOURCE_CONFIG


@dataclass
class LawChunk:
    id: str
    season: str
    title: str
    source_url: str
    canonical_page: str
    page: int
    law_number: str | None
    law_title: str | None
    section_hint: str | None
    text: str


LAW_BAR_RE = re.compile(r"Law\s+(\d{1,2})\s*\|\s*([A-Za-z ,'/()-]+)")
LAW_HEADING_RE = re.compile(r"^Law\s+(\d{1,2})\s*[-–:]?\s*(.+)?$", re.IGNORECASE)
NUMBERED_LAW_RE = re.compile(r"^(\d{1,2})\s+([A-Z][A-Za-z ,'/()-]{4,})$")
SECTION_RE = re.compile(r"^(\d+)\.\s+(.+)$")
KNOWN_SECTION_TITLES = [
    "Direct free kick",
    "Indirect free kick",
    "Disciplinary action",
    "Cautionable offences",
    "Sending-off offences",
    "Restart of play after fouls and misconduct",
    "Offside position",
    "Offside offence",
    "No offence",
    "Procedure",
    "Offences and sanctions",
]


def load_source_config() -> dict:
    return json.loads(SOURCE_CONFIG.read_text())


def download_pdf() -> Path:
    cfg = load_source_config()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    response = requests.get(cfg["source_url"], timeout=60, allow_redirects=True)
    response.raise_for_status()
    PDF_PATH.write_bytes(response.content)
    return PDF_PATH


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def infer_law(text: str, lines: list[str], current_law: tuple[str | None, str | None]) -> tuple[str | None, str | None]:
    law_number, law_title = current_law
    bar_match = LAW_BAR_RE.search(text)
    if bar_match:
        return bar_match.group(1), bar_match.group(2).strip()

    for raw in lines[:12]:
        line = raw.strip()
        match = LAW_HEADING_RE.match(line)
        if match:
            return match.group(1), (match.group(2) or "").strip() or law_title
        match = NUMBERED_LAW_RE.match(line)
        if match and 1 <= int(match.group(1)) <= 17:
            return match.group(1), match.group(2).strip()
    return law_number, law_title


def clean_line(line: str) -> str:
    clean = line.strip()
    clean = re.sub(r"^\d+(?=Laws of the Game)", "", clean)
    clean = re.sub(r"^Laws of the Game \d{4}/\d{2}\s*\|\s*", "", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def section_hint(text: str, law_number: str | None, law_title: str | None) -> str | None:
    fallback = f"Law {law_number}: {law_title}" if law_number and law_title else None
    lines = [clean_line(line) for line in text.splitlines() if clean_line(line)]

    for line in lines:
        match = SECTION_RE.match(line)
        if match and len(match.group(2)) <= 80:
            section = f"{match.group(1)}. {match.group(2)}"
            return f"{fallback} > {section}" if fallback else section

    flattened = " ".join(lines)
    for title in KNOWN_SECTION_TITLES:
        match = re.search(rf"\b(\d+)\.\s+{re.escape(title)}\b", flattened, re.IGNORECASE)
        if match:
            section = f"{match.group(1)}. {title}"
            return f"{fallback} > {section}" if fallback else section

    for title in KNOWN_SECTION_TITLES:
        if re.search(rf"\b{re.escape(title)}\b", flattened, re.IGNORECASE):
            return f"{fallback} > {title}" if fallback else title

    for line in lines:
        if line.lower().startswith("law "):
            continue
        if 6 <= len(line) <= 80 and not line.endswith("."):
            return f"{fallback} > {line}" if fallback and line != law_title else fallback or line
    return fallback


def chunk_page(text: str, max_chars: int = 1800) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        if current and current_len + len(paragraph) > max_chars:
            chunks.append("\n\n".join(current))
            current = []
            current_len = 0
        current.append(paragraph)
        current_len += len(paragraph)

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def extract_chunks() -> list[LawChunk]:
    cfg = load_source_config()
    reader = PdfReader(str(PDF_PATH))
    chunks: list[LawChunk] = []
    current_law: tuple[str | None, str | None] = (None, None)

    for page_index, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        if not text:
            continue
        lines = [line for line in text.splitlines() if line.strip()]
        current_law = infer_law(text, lines, current_law)
        for chunk_index, chunk_text in enumerate(chunk_page(text), start=1):
            chunks.append(
                LawChunk(
                    id=f"p{page_index:03d}-{chunk_index:02d}",
                    season=cfg["season"],
                    title=cfg["title"],
                    source_url=cfg["source_url"],
                    canonical_page=cfg["canonical_page"],
                    page=page_index,
                    law_number=current_law[0],
                    law_title=current_law[1],
                    section_hint=section_hint(chunk_text, current_law[0], current_law[1]),
                    text=chunk_text,
                )
            )
    return chunks


def ingest() -> Path:
    if not PDF_PATH.exists():
        download_pdf()
    chunks = extract_chunks()
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_PATH.write_text(json.dumps([asdict(chunk) for chunk in chunks], indent=2))
    return CHUNKS_PATH
