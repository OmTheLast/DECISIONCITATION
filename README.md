# Football Rule Cite

Local-first referee call explanation assistant grounded in the IFAB Laws of the Game.

The MVP flow is:

1. Download the official IFAB Laws PDF.
2. Extract page text with page numbers.
3. Build a local BM25-style search index.
4. Retrieve relevant law excerpts for an incident and stated call.
5. Ask a local Ollama model to explain the call only from retrieved evidence.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m src.cli ingest
python -m src.cli explain --call "Penalty kick" "A defender trips an attacker inside the penalty area while challenging for the ball."
```

By default, the assistant uses `qwen3.6:27b` via Ollama.

```bash
OLLAMA_MODEL=qwen3:latest python -m src.cli ask "An attacker in an offside position interferes with a defender."
```

## Commands

Explain why a stated call may have been made:

```bash
python -m src.cli explain --call "Penalty kick" "A defender trips an attacker inside the penalty area while challenging for the ball."
```

Ask for a direct decision from the incident text:

```bash
python -m src.cli ask "A defender trips an attacker inside the penalty area while challenging for the ball."
```

Run the seed evaluation set:

```bash
OLLAMA_MODEL=qwen3:latest python -m src.cli eval --limit 3
```

## Source

Default source: IFAB Laws of the Game 2026/27, single-page English PDF.

The source URL can be changed in `config/sources.json`.

## Repository Notes

Downloaded PDFs and generated search indexes are intentionally not committed.
Run `python -m src.cli ingest` after cloning to recreate local data under `data/`.
