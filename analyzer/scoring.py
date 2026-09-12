"""Deterministic quantitative scoring for classified finding groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from classification import ClassifiedFindingGroup


# ====================================================================
# ⚠️ EQUIPE: MUDAR AQUI (PESOS DA EMPRESA) ⚠️
# Estes são os pesos globais. Ajustem conforme a estratégia de vocês.
# ====================================================================
PESOS_AGRAVANTES: dict[str, float] = {
    "financeiro": 1.0,
    "seguranca": 2.5,
    "aumento_problema": 1.2,
    "imagem_empresa": 1.5,
    "emocional": 0.8,
}

# Parâmetros mortos removidos. O único atenuante real é o esforço.
PESOS_ATENUANTES: dict[str, float] = {
    "tempo": 1.0, # Esse peso pode ficar em 1.0, a variação acontece na nota do problema
}

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
        notes.get(name, 1.0) * weight
        for name, weight in PESOS_AGRAVANTES.items()
    )
    
    # Agora pega a nota de 'tempo' que veio dinamicamente, em vez de chumbar 1.0
    mitigating_product = _product(
        notes.get(name, 1.0) * weight
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
        "effort": notes.get("tempo", 1.0), # Salva o esforço no relatório
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
    return [calculate_score(group) for group in classified_groups]


def notes_for_group(classified_group: ClassifiedFindingGroup) -> dict[str, float]:
    concept = classified_group.concept
    category = classified_group.category
    finding = classified_group.group.representative_finding

    # ====================================================================
    # O DESEMPATE DO JSON: Converte HIGH/LOW em um multiplicador matemático
    # ====================================================================
    severidade = str(finding.severity or "LOW").upper()
    if severidade in ["HIGH", "ERROR", "CRITICAL", "A"]:
        peso_sev = 1.0   # Mantém a nota alta (Ex: 5.0 x 1.0 = 5.0)
    elif severidade in ["MEDIUM", "WARNING", "B", "C"]:
        peso_sev = 0.6   # Corta a nota (Ex: 5.0 x 0.6 = 3.0)
    else:
        peso_sev = 0.2   # Esmaece a nota (Ex: 5.0 x 0.2 = 1.0)

    # ====================================================================
    # ⚠️ EQUIPE: MUDAR AS NOTAS AQUI (DE 1.0 A 5.0) ⚠️
    # Os números brutos abaixo são definidos pela equipe. O `peso_sev`
    # cuida de reduzir eles automaticamente se a ferramenta disser que é LOW.
    # ====================================================================
    
    if concept in _SECURITY_CONCEPTS or category == "security":
        notes = {
            "financeiro": 4.0 * peso_sev,
            "seguranca": 5.0 * peso_sev,
            "aumento_problema": 4.0 * peso_sev,
            "imagem_empresa": 4.0 * peso_sev,
            "emocional": 3.0 * peso_sev,
        }
        tempo = 1.0  # Rápido de arrumar, mantém score alto para a auditoria de 30 dias

    elif concept == "cyclomatic_complexity" or category == "maintainability":
        notes = {
            "financeiro": 2.0 * peso_sev,
            "seguranca": 1.0 * peso_sev,
            "aumento_problema": 4.0 * peso_sev,
            "imagem_empresa": 1.0 * peso_sev,
            "emocional": 5.0 * peso_sev,
        }
        tempo = 5.0  # Demora MUITO. O denominador engole a nota para salvar a release de 14 dias

    elif category == "reliability":
        notes = {
            "financeiro": 3.0 * peso_sev,
            "seguranca": 2.0 * peso_sev,
            "aumento_problema": 3.0 * peso_sev,
            "imagem_empresa": 3.0 * peso_sev,
            "emocional": 2.0 * peso_sev,
        }
        tempo = 2.0

    elif category == "environmental":
        # Environmental geralmente não afeta o cliente real
        notes = {
            "financeiro": 1.0 * peso_sev,
            "seguranca": 1.0 * peso_sev,
            "aumento_problema": 2.0 * peso_sev,
            "imagem_empresa": 1.0 * peso_sev,
            "emocional": 2.0 * peso_sev,
        }
        tempo = 1.0

    else:
        # Code Quality e outros
        notes = {
            "financeiro": 1.0 * peso_sev,
            "seguranca": 1.0 * peso_sev,
            "aumento_problema": 2.0 * peso_sev,
            "imagem_empresa": 1.0 * peso_sev,
            "emocional": 2.0 * peso_sev,
        }
        tempo = 2.0

    # Retorna o dicionário com todas as notas + o tempo de esforço
    return {
        "tempo": tempo,
        **notes,
    }


def _priority_for_score(score: float) -> str:
    if score > LIMIAR_ALTO:
        return "alto"
    if score > LIMIAR_MEDIO:
        return "medio"
    return "baixo"


def score_priority_label(score_priority: str) -> str:
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
