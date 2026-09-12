"""Deterministic quantitative scoring for classified finding groups.

The values in this module are team placeholders. They should be calibrated
after observing real results, but must remain explicit and deterministic.
Native tool severity, corroborating tools, and effort are
kept separate from the quantitative score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from classification import ClassifiedFindingGroup


# Team placeholders. Calibrate after reviewing real pipeline results.
PESOS_AGRAVANTES: dict[str, float] = {
    "financeiro": 1.0,
    "seguranca": 2.5,
    "aumento_problema": 1.2,
    "imagem_empresa": 1.5,
    "emocional": 0.8,
}

# Team placeholders. No objective effort or mitigation data exists in the
# current Finding model, so these remain neutral until the team defines it.
PESOS_ATENUANTES: dict[str, float] = {
    "tempo": 1.0,
    "custo_tempo": 1.0,
    "saber_cliente": 1.0,
}

# Team placeholders. Revisit only after observing the distribution in real runs.
LIMIAR_ALTO = 300.0
LIMIAR_MEDIO = 200.0

_SECURITY_CONCEPTS = {
    "dynamic_sql",
    "hardcoded_secret",
    "weak_password_hash",
}


@dataclass(frozen=True)
class ScoredFindingGroup:
    """Serializable scoring result layered on top of Classification V1."""

    group_id: str
    concept: str
    category: str
    classification_priority: str | None
    score: float
    score_priority: str
    score_priority_mapped: str
    notes: dict[str, float]
    formula: str
    factors: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "concept": self.concept,
            "category": self.category,
            "classification_priority": self.classification_priority,
            "score": self.score,
            "score_priority": self.score_priority,
            "score_priority_mapped": self.score_priority_mapped,
            "notes": self.notes,
            "formula": self.formula,
            "factors": self.factors,
        }


def calculate_score(classified_group: ClassifiedFindingGroup) -> ScoredFindingGroup:
    """Calculate one deterministic score without changing the V1 result."""

    notes = notes_for_group(classified_group)
    aggravating_product = _product(
        notes[name] * weight
        for name, weight in PESOS_AGRAVANTES.items()
    )
    mitigating_notes = {name: 1.0 for name in PESOS_ATENUANTES}
    mitigating_product = _product(
        mitigating_notes[name] * weight
        for name, weight in PESOS_ATENUANTES.items()
    )
    if mitigating_product == 0:
        mitigating_product = 0.0001

    score = aggravating_product / mitigating_product
    score_priority = _priority_for_score(score)
    finding = classified_group.group.representative_finding
    group_id = _group_id(classified_group)
    formula = (
        "product(note * aggravating_weight) / "
        "product(note * mitigating_weight)"
    )
    factors = {
        "aggravating_weights": dict(PESOS_AGRAVANTES),
        "mitigating_weights": dict(PESOS_ATENUANTES),
        "aggravating_product": aggravating_product,
        "mitigating_product": mitigating_product,
        "native_severity": finding.severity,
        "source_tools": classified_group.group.source_tools,
        "evidence_count": len(classified_group.group.evidences),
        "effort": None,
    }
    return ScoredFindingGroup(
        group_id=group_id,
        concept=classified_group.concept,
        category=classified_group.category,
        classification_priority=classified_group.priority,
        score=score,
        score_priority=score_priority,
        score_priority_mapped=score_priority_label(score_priority),
        notes=notes,
        formula=formula,
        factors=factors,
    )


def score_groups(
    classified_groups: list[ClassifiedFindingGroup],
) -> list[ScoredFindingGroup]:
    """Score groups in their supplied order without cross-group effects."""

    return [calculate_score(group) for group in classified_groups]


def notes_for_group(classified_group: ClassifiedFindingGroup) -> dict[str, float]:
    """Apply the team's initial risk-note policy.

    Notes represent estimated potential risk in the HourTrack context, not
    proven loss. Security issues affect enterprise questionnaire exposure;
    reliability/availability issues affect a release serving concentrated
    enterprise revenue; maintainability issues are amplified by the release
    window and the upcoming developer departure. Missing inputs use 1.0.
    """

    concept = classified_group.concept
    category = classified_group.category
    finding = classified_group.group.representative_finding

    if concept in _SECURITY_CONCEPTS:
        notes = {
            "financeiro": 4.0,
            "seguranca": 5.0,
            "aumento_problema": 4.0,
            "imagem_empresa": 4.0,
            "emocional": 3.0,
        }
    elif concept == "missing_timeout":
        notes = {
            "financeiro": 3.0,
            "seguranca": 3.0,
            "aumento_problema": 3.0,
            "imagem_empresa": 3.0,
            "emocional": 2.0,
        }
    elif concept == "cyclomatic_complexity":
        complexity = finding.metric_value or 0
        severe = complexity >= 20
        notes = {
            "financeiro": 3.0 if severe else 1.0,
            "seguranca": 1.0,
            "aumento_problema": 4.0 if severe else 1.0,
            "imagem_empresa": 2.0 if severe else 1.0,
            "emocional": 3.0 if severe else 1.0,
        }
    elif category == "reliability":
        notes = {
            "financeiro": 2.0,
            "seguranca": 1.0,
            "aumento_problema": 3.0,
            "imagem_empresa": 2.0,
            "emocional": 2.0,
        }
    elif category == "environmental":
        notes = {
            "financeiro": 2.0,
            "seguranca": 2.0,
            "aumento_problema": 3.0,
            "imagem_empresa": 3.0,
            "emocional": 2.0,
        }
    else:
        notes = {
            "financeiro": 2.0,
            "seguranca": 1.0,
            "aumento_problema": 2.0,
            "imagem_empresa": 2.0,
            "emocional": 2.0,
        }

    return {
        **{name: 1.0 for name in PESOS_ATENUANTES},
        **notes,
    }


def _priority_for_score(score: float) -> str:
    if score > LIMIAR_ALTO:
        return "alto"
    if score > LIMIAR_MEDIO:
        return "medio"
    return "baixo"


def score_priority_label(score_priority: str) -> str:
    """Map quantitative Portuguese labels to the pipeline labels."""

    return {"alto": "high", "medio": "medium", "baixo": "low"}[score_priority]


def _group_id(classified_group: ClassifiedFindingGroup) -> str:
    finding = classified_group.group.representative_finding
    location = f"{finding.file_path or '<unknown>'}:{finding.line or 0}"
    return f"{classified_group.concept}@{location}"


def _product(values: Any) -> float:
    result = 1.0
    for value in values:
        result *= value
    return result