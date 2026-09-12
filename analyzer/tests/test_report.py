import unittest

from report import CONCEPT_GUIDANCE, render_json, render_markdown
from scoring import ScoredFindingGroup


class ReportTests(unittest.TestCase):
    def make_result(self, concept="dynamic_sql"):
        return ScoredFindingGroup(
            group_id=f"{concept}@app.py:10",
            concept=concept,
            category="security",
            classification_priority="critical",
            score=3456.0,
            score_priority="alto",
            score_priority_mapped="high",
            notes={"financeiro": 4.0},
            formula="deterministic",
            factors={"source_tools": ["bandit", "semgrep"], "evidence_count": 2},
        )

    def test_guidance_covers_required_concepts(self):
        required = {
            "dynamic_sql", "hardcoded_secret", "weak_password_hash",
            "missing_timeout", "broad_exception", "swallowed_exception",
            "inconsistent_returns", "import_error", "cyclomatic_complexity",
            "excessive_branches", "excessive_returns", "excessive_locals",
            "unused_variable", "shadowed_builtin", "unnecessary_else_after_return",
            "todo_comment",
        }
        self.assertTrue(required.issubset(CONCEPT_GUIDANCE))
        for guidance in CONCEPT_GUIDANCE.values():
            self.assertTrue(all(guidance[field] for field in ("description", "impact", "recommendation")))

    def test_json_preserves_scoring_fields_and_adds_guidance(self):
        result = self.make_result()
        payload = render_json([result])
        self.assertIn('"score": 3456.0', payload)
        self.assertIn('"score_priority_mapped": "high"', payload)
        self.assertIn('"description":', payload)
        self.assertIn('"recommendation":', payload)

    def test_markdown_has_business_sections_and_full_traceability(self):
        markdown = render_markdown([self.make_result()])
        for heading in (
            "## Resumo executivo", "## Principais problemas", "## Plano de ação",
            "## Origem das recomendações", "## Limitações", "## Grupos e evidências",
        ):
            self.assertIn(heading, markdown)
        self.assertIn("evidence_count", markdown)
        self.assertIn("bandit, semgrep", markdown)
        self.assertNotIn("O que a IA sugeriu", markdown)


if __name__ == "__main__":
    unittest.main()