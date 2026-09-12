"""Markdown and JSON rendering for the analyzer pipeline."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from scoring import ScoredFindingGroup, score_priority_label


def report_payload(results: list[ScoredFindingGroup]) -> dict[str, Any]:
    distribution = Counter(
        score_priority_label(result.score_priority) for result in results
    )
    return {
        "summary": {
            "scored_groups": len(results),
            "high": distribution["high"],
            "medium": distribution["medium"],
            "low": distribution["low"],
            "without_priority": 0,
        },
        "results": [result.to_dict() for result in results],
    }


def render_json(results: list[ScoredFindingGroup]) -> str:
    return json.dumps(report_payload(results), ensure_ascii=False, indent=2) + "\n"


def render_markdown(results: list[ScoredFindingGroup]) -> str:
    payload = report_payload(results)
    summary = payload["summary"]
    lines = [
        "# HourTrack analyzer report",
        "",
        f"Scored groups: {summary['scored_groups']}",
        "",
        "| ID | conceito | categoria | score | prioridade V1 | prioridade scoring |",
        "|---|---|---|---:|---|---|",
    ]
    for result in results:
        lines.append(
            "| {group_id} | {concept} | {category} | {score:.2f} | {v1} | {scoring} |".format(
                group_id=result.group_id,
                concept=result.concept,
                category=result.category,
                score=result.score,
                v1=result.classification_priority or "sem prioridade",
                scoring=score_priority_label(result.score_priority),
            )
        )
    lines.extend(
        [
            "",
            "## Distribuição",
            "",
            f"- high: {summary['high']}",
            f"- medium: {summary['medium']}",
            f"- low: {summary['low']}",
            f"- sem prioridade: {summary['without_priority']}",
            "",
        ]
    )
    return "\n".join(lines)