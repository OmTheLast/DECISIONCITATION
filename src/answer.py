from __future__ import annotations

import json
import re

from .ollama_client import extract_json, generate
from .search import SearchHit, search


def format_evidence(hits: list[SearchHit]) -> str:
    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        chunk = hit.chunk
        law = f"Law {chunk['law_number']}" if chunk.get("law_number") else "Law unknown"
        title = chunk.get("law_title") or "Untitled"
        blocks.append(
            "\n".join(
                [
                    f"[{index}] {law}: {title}",
                    f"Page: {chunk['page']}",
                    f"Section hint: {chunk.get('section_hint') or 'unknown'}",
                    f"Source: {chunk['canonical_page']}",
                    "Text:",
                    chunk["text"][:1600],
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def build_prompt(incident: str, hits: list[SearchHit]) -> str:
    return f"""
/no_think
You are a football referee law citation assistant.

Use ONLY the evidence below. If the evidence is insufficient, say so in the uncertainty field.
Do not cite laws that are not in the evidence. Do not invent page numbers.
Return valid JSON only. No markdown. No chain of thought.

Incident:
{incident}

Evidence:
{format_evidence(hits)}

JSON schema:
{{
  "decision": "short decision",
  "restart": "restart of play, or unknown",
  "disciplinary_action": "card/no card/unknown with caveat",
  "laws_applied": [
    {{
      "law": "Law number and title",
      "page": 0,
      "section_hint": "section title or hint",
      "source": "source URL",
      "why_it_applies": "brief grounded explanation"
    }}
  ],
  "uncertainty": ["missing fact or interpretation issue"],
  "confidence": "high|medium|low"
}}
""".strip()


def build_explain_prompt(incident: str, call: str, hits: list[SearchHit]) -> str:
    return f"""
/no_think
You are a football referee call explanation assistant.

Your job is educational: explain why the stated call may have been made and cite the IFAB Laws that support that explanation.
Do not claim the referee is right or wrong. Do not use words like "correct", "incorrect", "right", or "wrong" about the call. Do not make yourself the referee.
Use ONLY the evidence below. If the evidence is insufficient, say so in uncertainties.
Do not cite laws that are not in the evidence. Do not invent page numbers.
Alternate explanations must not contradict the incident facts. Phrase alternates as possible explanation paths, not verdicts on the referee. For example, if the incident is inside the penalty area, do not suggest only a direct free kick unless the alternate changes the location or whether an offence occurred.
If card severity changes from careless to reckless to excessive force, keep the restart consistent unless another fact changes.
For physical challenges: careless does not require a card by itself; reckless means caution/yellow card; using excessive force means sending-off/red card.
Do not say a careless foul is cautioned unless a separate cautionable reason is clearly supported by the evidence, such as stopping a promising attack.
Return valid JSON only. No markdown. No chain of thought.

Call being explained:
{call}

Incident:
{incident}

Evidence:
{format_evidence(hits)}

JSON schema:
{{
  "call_explained": "the stated call",
  "why_this_call_may_have_been_made": "brief explanation grounded in the evidence",
  "citations": [
    {{
      "law": "Law number and title",
      "page": 0,
      "section_hint": "section title or hint",
      "source": "source URL",
      "relevance": "why this law supports explaining the call"
    }}
  ],
  "uncertainties": ["missing fact or interpretation issue"],
  "alternate_explanations": [
    {{
      "if": "fact changes or is unclear",
      "then": "how the explanation could change"
    }}
  ],
  "confidence": "high|medium|low"
}}
""".strip()


def answer_incident(incident: str, limit: int = 8, model: str | None = None) -> dict:
    hits = search(incident, limit=limit)
    if not hits:
        return {
            "decision": "unknown",
            "restart": "unknown",
            "disciplinary_action": "unknown",
            "laws_applied": [],
            "uncertainty": ["No relevant law chunks were retrieved."],
            "confidence": "low",
        }
    raw = generate(build_prompt(incident, hits), model=model)
    parsed = extract_json(raw)
    apply_source_metadata(parsed, hits, incident)
    parsed["_retrieved_chunk_ids"] = [hit.chunk["id"] for hit in hits]
    return parsed


def explain_call(incident: str, call: str, limit: int = 8, model: str | None = None) -> dict:
    query = f"{call}. {incident}"
    hits = search(query, limit=limit)
    if not hits:
        return {
            "call_explained": call,
            "why_this_call_may_have_been_made": "No relevant law chunks were retrieved.",
            "citations": [],
            "uncertainties": ["No relevant law chunks were retrieved."],
            "alternate_explanations": [],
            "confidence": "low",
        }
    raw = generate(build_explain_prompt(incident, call, hits), model=model)
    parsed = extract_json(raw)
    parsed["call_explained"] = parsed.get("call_explained") or call
    apply_source_metadata(parsed, hits, query, citation_key="citations")
    ensure_supporting_citations(parsed, hits, incident, call)
    sanitize_explanation(parsed, incident, call)
    parsed["_retrieved_chunk_ids"] = [hit.chunk["id"] for hit in hits]
    return parsed


def law_number_from_label(label: str) -> str | None:
    match = re.search(r"Law\s+(\d{1,2})", label)
    return match.group(1) if match else None


def apply_source_metadata(
    answer: dict,
    hits: list[SearchHit],
    incident: str,
    citation_key: str = "laws_applied",
) -> None:
    evidence = hits[0].chunk if hits else {}
    for law in answer.get(citation_key, []):
        cited_law = law_number_from_label(law.get("law", ""))
        candidates = [hit for hit in hits if not cited_law or hit.chunk.get("law_number") == cited_law]
        matching = max(candidates, key=lambda hit: hit.score, default=None)
        matching = matching.chunk if matching else None
        matching = matching or next((hit.chunk for hit in hits if hit.chunk.get("page") == law.get("page")), None)
        matching = matching or evidence
        law["page"] = matching.get("page", law.get("page"))
        law["section_hint"] = matching.get("section_hint", law.get("section_hint"))
        law["source"] = matching.get("canonical_page", law.get("source"))


def cited_law_numbers(answer: dict, citation_key: str = "citations") -> set[str]:
    return {
        law_number
        for citation in answer.get(citation_key, [])
        if (law_number := law_number_from_label(citation.get("law", "")))
    }


def best_chunk_for_law(hits: list[SearchHit], law_number: str) -> dict | None:
    match = max(
        (hit for hit in hits if hit.chunk.get("law_number") == law_number),
        key=lambda hit: hit.score,
        default=None,
    )
    return match.chunk if match else None


def append_citation(answer: dict, chunk: dict, relevance: str) -> None:
    answer.setdefault("citations", []).append(
        {
            "law": f"Law {chunk.get('law_number')}: {chunk.get('law_title')}",
            "page": chunk.get("page"),
            "section_hint": chunk.get("section_hint"),
            "source": chunk.get("canonical_page"),
            "relevance": relevance,
        }
    )


def ensure_supporting_citations(answer: dict, hits: list[SearchHit], incident: str, call: str) -> None:
    lowered = f"{incident} {call}".lower()
    cited = cited_law_numbers(answer)

    needs_law12 = (
        any(term in lowered for term in ["penalty", "direct free kick", "indirect free kick"])
        and any(
            term in lowered
            for term in [
                "contact",
                "fall",
                "falls",
                "foul",
                "trip",
                "trips",
                "goalkeeper",
                "deliberately kicked",
                "backpass",
            ]
        )
    )
    if needs_law12 and "12" not in cited:
        law12 = best_chunk_for_law(hits, "12")
        if law12:
            append_citation(
                answer,
                law12,
                "Provides the Law 12 offence basis that must exist before the stated restart or disciplinary explanation applies.",
            )
            cited.add("12")

    needs_law14 = "penalty" in call.lower() and "14" not in cited
    if needs_law14:
        law14 = best_chunk_for_law(hits, "14")
        if law14:
            append_citation(
                answer,
                law14,
                "Provides the Law 14 restart basis for a direct free kick offence committed inside the penalty area.",
            )


def sanitize_explanation(answer: dict, incident: str, call: str) -> None:
    lowered_incident = incident.lower()
    lowered_call = call.lower()
    if "penalty" not in lowered_call:
        answer["citations"] = [
            citation
            for citation in answer.get("citations", [])
            if law_number_from_label(citation.get("law", "")) != "14"
        ]

    sanitized = []

    for alternate in answer.get("alternate_explanations", []):
        if_text = str(alternate.get("if", ""))
        then_text = str(alternate.get("then", ""))
        combined = f"{if_text} {then_text}".lower()

        contradictory_penalty_alternate = (
            "penalty" in lowered_call
            and "inside" in lowered_incident
            and "penalty area" in lowered_incident
            and "direct free kick" in combined
            and "instead of a penalty" in combined
            and "outside" not in combined
            and "not a foul" not in combined
            and "no offence" not in combined
        )
        if contradictory_penalty_alternate:
            continue

        for banned in ["incorrect", "correct", "right", "wrong"]:
            if_text = if_text.replace(banned, "different").replace(banned.title(), "Different")
            then_text = then_text.replace(banned, "different").replace(banned.title(), "Different")
        alternate["if"] = if_text
        alternate["then"] = then_text
        sanitized.append(alternate)

    answer["alternate_explanations"] = sanitized


def answer_as_json(incident: str, model: str | None = None) -> str:
    return json.dumps(answer_incident(incident, model=model), indent=2)


def explain_as_json(incident: str, call: str, model: str | None = None) -> str:
    return json.dumps(explain_call(incident, call, model=model), indent=2)
