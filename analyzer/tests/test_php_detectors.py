import json
import unittest
from pathlib import Path

from detectors.php import parse_phpmetrics, parse_phpstan
from models import FindingKind


class PhpDetectorTests(unittest.TestCase):
    def setUp(self):
        self.output_dir = (
            Path(__file__).resolve().parents[2]
            / "Hackathon-Ufsc-main"
            / "analyzer-env"
            / "workspace"
            / "output"
        )

    def test_phpstan_parses_messages_as_findings(self):
        data = json.loads((self.output_dir / "phpstan.json").read_text())
        findings = parse_phpstan(data)
        self.assertEqual(len(findings), 90)
        self.assertEqual(findings[0].source_tool, "phpstan")
        self.assertEqual(findings[0].file_path, "/repos/php/app/Console/Commands/SyncData.php")
        self.assertEqual(findings[0].line, 9)
        self.assertEqual(findings[0].rule_id, "class.notFound")
        self.assertEqual(findings[0].category, "environmental")

    def test_phpmetrics_parses_only_class_ccn_metrics(self):
        data = json.loads((self.output_dir / "phpmetrics.json").read_text())
        findings = parse_phpmetrics(data)
        self.assertEqual(len(findings), 12)
        self.assertTrue(all(item.kind == FindingKind.METRIC for item in findings))
        self.assertEqual({item.source_tool for item in findings}, {"phpmetrics"})
        self.assertEqual(max(item.metric_value for item in findings), 36)

    def test_phpstan_rejects_missing_files_object(self):
        with self.assertRaises(ValueError):
            parse_phpstan({})


if __name__ == "__main__":
    unittest.main()