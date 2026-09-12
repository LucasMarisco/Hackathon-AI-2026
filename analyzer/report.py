"""Markdown and JSON rendering for the analyzer pipeline."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from deadlines import TIER_NOMES
from scoring import ScoredFindingGroup, rank_groups, score_priority_label


def report_payload(results: list[ScoredFindingGroup]) -> dict[str, Any]:
    # Fonte única de ordenação: qualquer render sai na ordem de prioridade por
    # prazo, sem depender de quem chamou ter ordenado antes.
    ordered = rank_groups(results)
    distribution = Counter(result.priority for result in ordered)
    por_tier = Counter(result.deadline_tier for result in ordered)
    return {
        "summary": {
            "scored_groups": len(ordered),
            "critical": distribution["critical"],
            "high": distribution["high"],
            "medium": distribution["medium"],
            "low": distribution["low"],
            "por_tier": {
                TIER_NOMES[tier]: por_tier.get(tier, 0)
                for tier in sorted(TIER_NOMES)
            },
        },
        "ordering_rule": (
            "Ordem lexicográfica (deadline_tier, -score, group_id). O tier vem "
            "primeiro para garantir que nenhum finding que não bloqueia o release "
            "de 14 dias fique acima de um que bloqueia. Dentro do tier 2 "
            "(questionário) o esforço domina: mais barato primeiro, porque "
            "concorre com o release pela mesma capacidade do time."
        ),
        "results": [result.to_dict() for result in ordered],
    }


def render_json(results: list[ScoredFindingGroup]) -> str:
    return json.dumps(report_payload(results), ensure_ascii=False, indent=2) + "\n"


def render_markdown(results: list[ScoredFindingGroup]) -> str:
    payload = report_payload(results)
    summary = payload["summary"]
    ordered = rank_groups(results)
    lines = [
        "# HourTrack analyzer report",
        "",
        f"Scored groups: {summary['scored_groups']}",
        "",
        "Ordenado por prazo: primeiro o que bloqueia o release de 14 dias, depois o",
        "questionário de segurança de 30 dias (mais barato primeiro).",
        "",
        "| # | ID | conceito | categoria | prioridade | prazo | release | questionário | esforço | score |",
        "|---:|---|---|---|---|---|---|---|---:|---:|",
    ]
    for position, result in enumerate(ordered, start=1):
        lines.append(
            "| {pos} | {group_id} | {concept} | {category} | {priority} | {prazo} "
            "| {release} | {questionario} | {esforco:g} | {score:.2f} |".format(
                pos=position,
                group_id=result.group_id,
                concept=result.concept,
                category=result.category,
                priority=result.priority,
                prazo=TIER_NOMES[result.deadline_tier],
                release="sim" if result.blocks_release else "—",
                questionario=(
                    ", ".join(f"Q{item}" for item in result.questionnaire_items)
                    or "—"
                ),
                esforco=result.esforco_pontos,
                score=result.score,
            )
        )
    lines.extend(
        [
            "",
            "## Distribuição",
            "",
            f"- critical: {summary['critical']}",
            f"- high: {summary['high']}",
            f"- medium: {summary['medium']}",
            f"- low: {summary['low']}",
            "",
            "### Por prazo",
            "",
        ]
    )
    lines.extend(
        f"- {nome}: {total}" for nome, total in summary["por_tier"].items()
    )
    lines.extend(["", "## Regra de ordenação", "", payload["ordering_rule"], ""])
    return "\n".join(lines)
