from __future__ import annotations

import argparse
import json

from .answer import answer_as_json, explain_as_json
from .ingest import download_pdf, ingest
from .search import search


def main() -> None:
    parser = argparse.ArgumentParser(description="Football rule citation assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("download", help="Download the configured IFAB PDF")
    subparsers.add_parser("ingest", help="Extract and index the configured IFAB PDF")

    search_parser = subparsers.add_parser("search", help="Search law chunks")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=6)

    ask_parser = subparsers.add_parser("ask", help="Answer a referee incident")
    ask_parser.add_argument("incident")

    explain_parser = subparsers.add_parser("explain", help="Explain why a stated call may have been made")
    explain_parser.add_argument("incident")
    explain_parser.add_argument("--call", required=True, help="Call being explained, e.g. 'Penalty kick'")

    eval_parser = subparsers.add_parser("eval", help="Run the seed evaluation set")
    eval_parser.add_argument("--limit", type=int, default=None, help="Only run the first N scenarios")
    eval_parser.add_argument("--save", action="store_true", help="Write the eval report under eval/runs/")
    eval_parser.add_argument("--progress", action="store_true", help="Print per-scenario progress to stderr")

    serve_parser = subparsers.add_parser("serve", help="Run the local web UI")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8765)

    args = parser.parse_args()

    if args.command == "download":
        print(download_pdf())
    elif args.command == "ingest":
        print(ingest())
    elif args.command == "search":
        hits = search(args.query, limit=args.limit)
        print(json.dumps([{"score": hit.score, **hit.chunk} for hit in hits], indent=2))
    elif args.command == "ask":
        print(answer_as_json(args.incident))
    elif args.command == "explain":
        print(explain_as_json(args.incident, args.call))
    elif args.command == "eval":
        from .evaluate import run_eval

        print(json.dumps(run_eval(limit=args.limit, save=args.save, progress=args.progress), indent=2))
    elif args.command == "serve":
        from .web_server import run

        run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
