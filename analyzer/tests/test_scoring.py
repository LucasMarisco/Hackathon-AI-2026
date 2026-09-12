import unittest
from unittest.mock import patch

from classification import classify_group
from deduplication import FindingGroup
from models import Finding, FindingKind, ValidationStatus
from scoring import calculate_score, notes_for_group, score_priority_label


class ScoringTests(unittest.TestCase):
    def make_group(
        self,
        concept,
        *,
        category="security",
        kind=FindingKind.FINDING,
        metric_value=None,
        severity=None,
        status=ValidationStatus.NEEDS_VALIDATION,
    ):
        finding = Finding(
            source_tool="radon" if kind == FindingKind.METRIC else "bandit",
            rule_id="radon.cc" if kind == FindingKind.METRIC else "B608",
            category=category,
            file_path="file.py",
            line=10,
            description=concept,
            kind=kind,
            metric_value=metric_value,
            severity=severity,
            validation_status=status,
        )
        return classify_group(
            FindingGroup(
                concept=concept,
                representative_finding=finding,
                evidences=[finding],
                validation_status=status,
            )
        )

    def test_security_concepts_receive_explicit_high_risk_score(self):
        result = calculate_score(self.make_group("dynamic_sql"))
        self.assertEqual(score_priority_label(result.score_priority), "high")
        self.assertEqual(result.notes["seguranca"], 5.0)
        self.assertIn("aggravating_weights", result.factors)

    def test_hardcoded_secret_is_scored_separately_from_tool_severity(self):
        result = calculate_score(self.make_group("hardcoded_secret"))
        self.assertGreater(result.score, 300)
        self.assertEqual(result.factors["native_severity"], None)

    def test_missing_timeout_and_swallowed_exception_have_policy_notes(self):
        timeout = calculate_score(self.make_group("missing_timeout", category="availability"))
        swallowed = calculate_score(self.make_group("swallowed_exception", category="reliability"))
        self.assertEqual(timeout.notes["aumento_problema"], 3.0)
        self.assertEqual(swallowed.notes["aumento_problema"], 3.0)
        self.assertGreater(timeout.score, swallowed.score)

    def test_complexity_29_uses_metric_value(self):
        result = calculate_score(
            self.make_group(
                "cyclomatic_complexity",
                category="maintainability",
                kind=FindingKind.METRIC,
                metric_value=29,
                severity="F",
            )
        )
        self.assertEqual(result.score_priority, "medio")

    def test_unused_variable_is_low_and_import_error_is_medium(self):
        unused = calculate_score(self.make_group("unused_variable", category="code_quality"))
        environmental = calculate_score(
            self.make_group("import_error", category="environmental")
        )
        self.assertEqual(unused.score_priority, "baixo")
        self.assertEqual(environmental.score_priority, "medio")

    def test_needs_validation_does_not_reduce_score(self):
        result = calculate_score(self.make_group("dynamic_sql"))
        self.assertEqual(result.validation_status, "needs_validation")
        self.assertGreater(result.score, 300)

    def test_missing_notes_are_neutral_and_zero_denominator_is_protected(self):
        result = calculate_score(self.make_group("unused_variable", category="code_quality"))
        notes = notes_for_group(self.make_group("unused_variable", category="code_quality"))
        self.assertEqual(notes["tempo"], 1.0)
        self.assertGreater(result.score, 0)
        with patch("scoring.PESOS_ATENUANTES", {"tempo": 0.0}):
            protected = calculate_score(
                self.make_group("unused_variable", category="code_quality")
            )
        self.assertGreater(protected.score, 0)

    def test_same_input_is_deterministic(self):
        group = self.make_group("dynamic_sql")
        self.assertEqual(calculate_score(group), calculate_score(group))

    def test_priority_threshold_order_is_high_medium_low(self):
        self.assertEqual(score_priority_label(calculate_score(self.make_group("dynamic_sql")).score_priority), "high")
        self.assertEqual(
            score_priority_label(
                calculate_score(
                    self.make_group("cyclomatic_complexity", category="maintainability", kind=FindingKind.METRIC, metric_value=29, severity="F")
                ).score_priority
            ),
            "medium",
        )
        self.assertEqual(score_priority_label(calculate_score(self.make_group("unused_variable", category="code_quality")).score_priority), "low")


if __name__ == "__main__":
    unittest.main()