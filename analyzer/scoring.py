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
from deadlines import (
    blocks_release,
    deadline_tier,
    questionnaire_items,
    tier_label,
    tier_rationale,
)


# Team placeholders. Calibrate after reviewing real pipeline results.
PESOS_AGRAVANTES: dict[str, float] = {
    "financeiro": 1.0,
    "seguranca": 2.5,
    "aumento_problema": 1.2,
    "imagem_empresa": 1.5,
    "emocional": 0.8,
}

# Atenuantes. "custo_tempo" carrega o esforço estimado, já elevado ao expoente do
# tier (ver EXPOENTE_ESFORCO_POR_TIER). "tempo" e "saber_cliente" seguem neutros:
# não há dado objetivo por item no modelo de Finding.
PESOS_ATENUANTES: dict[str, float] = {
    "tempo": 1.0,
    "custo_tempo": 1.0,
    "saber_cliente": 1.0,
}

# Esforço estimado por conceito, em story points.
#
# Calibrado contra a capacidade real descrita no business-context: 2 devs, ~6
# pontos por semana (reuniões, suporte e bugs consomem ~40%). Então 3 pontos é
# cerca de meia semana de trabalho do time inteiro.
ESFORCO_BY_CONCEPT: dict[str, float] = {
    "debug_enabled": 0.5,               # remover debug=True de run.py
    "missing_timeout": 0.5,             # acrescentar timeout= na chamada
    "unnecessary_else_after_return": 0.5,
    "unused_variable": 0.5,
    "shadowed_builtin": 0.5,
    "todo_comment": 0.5,
    "import_error": 0.5,                # instalar dep ou corrigir o import
    "hardcoded_secret": 1.0,            # mover para variável de ambiente
    "swallowed_exception": 1.0,
    "broad_exception": 1.0,
    "dynamic_sql": 2.0,                 # parametrizar a query
    "inconsistent_returns": 2.0,
    "excessive_returns": 2.0,
    "excessive_locals": 2.0,
    "excessive_branches": 3.0,
    "weak_password_hash": 3.0,          # trocar hash + migrar senhas existentes
    "cyclomatic_complexity": 5.0,       # refatorar função grande sem rede de testes
}
ESFORCO_DEFAULT = 2.0

# Expoente do esforço por tier.
#
# Um FATOR constante por tier não serviria de nada: como o tier é a chave primária
# da ordenação, multiplicar todos os scores de um tier pela mesma constante escala
# tudo igualmente e não reordena nada (A/2 vs B/2 tem a mesma ordem que A vs B).
# O expoente sim -- ele muda o trade-off entre gravidade e custo, porque
# A1/E1**k vs A2/E2**k troca de vencedor conforme k quando A e E divergem.
#
# Tiers 0 e 1 vão ser feitos de todo jeito para desbloquear o release, então o
# esforço só sequencia. O tier 2 (questionário) concorre com o release pela mesma
# capacidade do time, então ali o esforço domina: barato primeiro.
EXPOENTE_ESFORCO_POR_TIER: dict[int, float] = {
    0: 0.5,
    1: 0.5,
    2: 1.5,
    3: 1.0,
}

# Team placeholders. Revisit only after observing the distribution in real runs.
LIMIAR_ALTO = 300.0
LIMIAR_MEDIO = 200.0

# Conceitos que recebem as notas de risco de segurança. São exatamente os que
# respondem perguntas do questionário do cliente enterprise -- ver
# deadlines.QUESTIONNAIRE_CONCEPTS. debug_enabled entra aqui porque debug ligado
# em produção vaza stack trace e habilita o debugger do Werkzeug (execução
# remota), não é só ruído de configuração.
_SECURITY_CONCEPTS = {
    "dynamic_sql",
    "hardcoded_secret",
    "weak_password_hash",
    "debug_enabled",
}


@dataclass(frozen=True)
class ScoredFindingGroup:
    """Serializable scoring result layered on top of Classification V1."""

    group_id: str
    concept: str
    category: str
    classification_priority: str | None
    priority: str
    deadline_tier: int
    blocks_release: bool
    questionnaire_items: tuple[int, ...]
    esforco_pontos: float
    deadline_rationale: str
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
            "priority": self.priority,
            "deadline_tier": self.deadline_tier,
            "blocks_release": self.blocks_release,
            "questionnaire_items": list(self.questionnaire_items),
            "esforco_pontos": self.esforco_pontos,
            "deadline_rationale": self.deadline_rationale,
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
    # Antes isto era código morto: as notas atenuantes eram forçadas a 1.0 e o
    # retorno de notes_for_group era ignorado, então a divisão nunca fazia nada.
    # Agora custo_tempo carrega esforco_pontos ** expoente_do_tier.
    mitigating_product = _product(
        notes[name] * weight
        for name, weight in PESOS_ATENUANTES.items()
    )
    if mitigating_product == 0:
        mitigating_product = 0.0001

    score = aggravating_product / mitigating_product
    score_priority = _priority_for_score(score)
    finding = classified_group.group.representative_finding
    concept = classified_group.concept
    tier = deadline_tier(concept, finding.file_path)
    esforco = esforco_pontos(concept)
    group_id = _group_id(classified_group)
    formula = (
        "product(note * aggravating_weight) / product(note * mitigating_weight), "
        "com custo_tempo = esforco_pontos ** expoente_do_tier"
    )
    factors = {
        "aggravating_weights": dict(PESOS_AGRAVANTES),
        "mitigating_weights": dict(PESOS_ATENUANTES),
        "aggravating_product": aggravating_product,
        "mitigating_product": mitigating_product,
        "native_severity": finding.severity,
        "source_tools": classified_group.group.source_tools,
        "evidence_count": len(classified_group.group.evidences),
        "esforco_pontos": esforco,
        "expoente_esforco": EXPOENTE_ESFORCO_POR_TIER[tier],
    }
    return ScoredFindingGroup(
        group_id=group_id,
        concept=classified_group.concept,
        category=classified_group.category,
        classification_priority=classified_group.priority,
        priority=tier_label(tier, score, LIMIAR_ALTO),
        deadline_tier=tier,
        blocks_release=blocks_release(concept, finding.file_path),
        questionnaire_items=questionnaire_items(concept),
        esforco_pontos=esforco,
        deadline_rationale=tier_rationale(concept, finding.file_path),
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


def rank_groups(scored: list[ScoredFindingGroup]) -> list[ScoredFindingGroup]:
    """Ordena pela regra de priorização por prazo.

    A chave é lexicográfica: ``(deadline_tier, -score, group_id)``.

    - ``deadline_tier`` primeiro é o que **garante** a regra do time: nenhum finding
      que não bloqueia o release fica acima de um que bloqueia, qualquer que seja o
      score. Nenhum ajuste de peso consegue dar essa garantia.
    - ``group_id`` como desempate final é obrigatório, não cosmético: existem scores
      que colidem exatamente (o bucket de métrica severa e o environmental dão ambos
      259.20). Sem ele a ordem dependeria da ordem de entrada, e scoring não
      determinístico é desclassificação pelo briefing.
    """

    return sorted(
        scored,
        key=lambda item: (item.deadline_tier, -item.score, item.group_id),
    )


def esforco_pontos(concept: str) -> float:
    """Esforço estimado em story points, com default explícito."""

    return ESFORCO_BY_CONCEPT.get(concept, ESFORCO_DEFAULT)


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
    tier = deadline_tier(concept, finding.file_path)

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

    atenuantes = {
        "tempo": 1.0,
        "custo_tempo": esforco_pontos(concept) ** EXPOENTE_ESFORCO_POR_TIER[tier],
        "saber_cliente": 1.0,
    }
    return {**atenuantes, **notes}


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