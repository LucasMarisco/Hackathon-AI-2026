"""Deterministic V1 classification for consolidated finding groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from deduplication import FindingGroup
from models import FindingKind, ValidationStatus


CATEGORIES = {
    "security",
    "reliability",
    "availability",
    "maintainability",
    "code_quality",
    "architecture",
    "environmental",
}

# PLACEHOLDER: V1 project decisions, separate from native tool severity.
PRIORITY_BY_CONCEPT: dict[str, str | None] = {
    "dynamic_sql": "critical",
    "hardcoded_secret": "critical",
    "weak_password_hash": "high",
    "missing_timeout": "high",
    "swallowed_exception": "medium",
    "broad_exception": "needs_review",
    "inconsistent_returns": "medium",
    "cyclomatic_complexity": "medium",
    "excessive_returns": "low",
    "excessive_branches": "low",
    "excessive_locals": "low",
    "unnecessary_else_after_return": "low",
    "unused_variable": "low",
    "shadowed_builtin": "low",
    "todo_comment": "low",
    "import_error": "needs_review",
}

# PLACEHOLDER: only C-F are candidates; A/B remain metrics for later analysis.
RADON_CANDIDATE_RANKS = frozenset({"C", "D", "E", "F"})

CONCEPT_CATEGORIES: dict[str, str] = {
    "dynamic_sql": "security",
    "hardcoded_secret": "security",
    "weak_password_hash": "security",
    "swallowed_exception": "reliability",
    "inconsistent_returns": "reliability",
    "missing_timeout": "availability",
    "excessive_returns": "maintainability",
    "excessive_branches": "maintainability",
    "excessive_locals": "maintainability",
    "cyclomatic_complexity": "maintainability",
    "broad_exception": "reliability",
    "unnecessary_else_after_return": "code_quality",
    "unused_variable": "code_quality",
    "shadowed_builtin": "code_quality",
    "todo_comment": "code_quality",
    "import_error": "environmental",
}

PHPSTAN_ENVIRONMENTAL_CONCEPTS = frozenset(
    {
        "phpstan:class.notFound",
        "phpstan:function.notFound",
        "phpstan:method.notFound",
        "phpstan:property.notFound",
        "phpstan:trait.notFound",
    }
)


@dataclass(frozen=True)
class ClassifiedFindingGroup:
    """Classification result that keeps the original group and evidence."""

    group: FindingGroup
    category: str
    priority: str | None
    validation_status: ValidationStatus
    is_candidate: bool
    rationale: str

    @property
    def concept(self) -> str:
        return self.group.concept

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept": self.concept,
            "category": self.category,
            "priority": self.priority,
            "validation_status": self.validation_status.value,
            "is_candidate": self.is_candidate,
            "rationale": self.rationale,
            "group": self.group.to_dict(),
        }


def classify_groups(
    groups: list[FindingGroup],
) -> list[ClassifiedFindingGroup]:
    """Classify groups using only the explicit V1 policy."""

    return [classify_group(group) for group in groups]


def classify_group(group: FindingGroup) -> ClassifiedFindingGroup:
    """Classify one group without changing its findings or evidence."""

    category = _category_for(group)
    status = _classification_status(group, category)
    is_candidate = _is_candidate(group, category)
    priority = _priority_for(group, category, is_candidate)
    rationale = _rationale_for(group, category, is_candidate, status)

    return ClassifiedFindingGroup(
        group=group,
        category=category,
        priority=priority,
        validation_status=status,
        is_candidate=is_candidate,
        rationale=rationale,
    )


def _category_for(group: FindingGroup) -> str:
    if group.validation_status == ValidationStatus.ENVIRONMENTAL:
        return "environmental"
    if group.concept in PHPSTAN_ENVIRONMENTAL_CONCEPTS:
        return "environmental"
    if group.concept in CONCEPT_CATEGORIES:
        return CONCEPT_CATEGORIES[group.concept]
    if group.representative_finding.kind == FindingKind.METRIC:
        return "maintainability"
    return group.representative_finding.category or "code_quality"


def _classification_status(
    group: FindingGroup, category: str
) -> ValidationStatus:
    return group.validation_status


def _is_candidate(group: FindingGroup, category: str) -> bool:
    if group.representative_finding.kind != FindingKind.METRIC:
        return True
    if group.concept == "cyclomatic_complexity":
        rank = group.representative_finding.severity
        return rank in RADON_CANDIDATE_RANKS
    return False


def _priority_for(
    group: FindingGroup, category: str, is_candidate: bool
) -> str | None:
    if category == "environmental":
        return None
    if group.representative_finding.kind == FindingKind.METRIC and not is_candidate:
        return None
    if group.concept in PRIORITY_BY_CONCEPT:
        return PRIORITY_BY_CONCEPT[group.concept]
    return "needs_review"


def _rationale_for(
    group: FindingGroup,
    category: str,
    is_candidate: bool,
    status: ValidationStatus,
) -> str:
    if status == ValidationStatus.ENVIRONMENTAL:
        return "Classified as environmental because the evidence status is environmental."
    if group.representative_finding.kind == FindingKind.METRIC:
        if is_candidate:
            return "Radon rank C-F is a V1 maintainability candidate; threshold is a project placeholder."
        return "Metric retained for analysis; Radon rank A-B is not classified as a debt candidate in V1."
    return f"Mapped concept '{group.concept}' to the V1 category '{category}'."
