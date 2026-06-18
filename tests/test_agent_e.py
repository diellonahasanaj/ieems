import json
import tempfile
import unittest
from pathlib import Path

from backend.agents.agent_e import agent_e_duplicate


class AgentEDuplicateDetectionTests(unittest.TestCase):
    def test_detects_cross_report_duplicate_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_storage = Path(temp_dir) / "run_storage"
            previous_metadata = run_storage / "run_previous" / "metadata"
            current_metadata = run_storage / "run_current" / "metadata"
            previous_metadata.mkdir(parents=True)

            (previous_metadata / "normalized_expenses.json").write_text(
                json.dumps(
                    {
                        "vendor": "Restaurant ABC",
                        "amount": 25,
                        "standard_currency": "EUR",
                        "standard_date": "2026-06-16",
                    }
                )
            )

            state = {
                "run_id": "run_current",
                "base_path": str(current_metadata),
                "normalized": {
                    "vendor": "Rest ABC",
                    "amount": "25.00",
                    "standard_currency": "EUR",
                    "standard_date": "2026-06-16",
                },
            }

            result = agent_e_duplicate(state)["duplicate_check"]

            self.assertTrue(result["is_duplicate"])
            self.assertEqual("DUPLICATE_FOUND", result["status"])
            self.assertEqual("run_previous", result["matched_run_id"])
            self.assertGreaterEqual(result["similarity_score"], 85)
            self.assertTrue((current_metadata / "duplicates.md").exists())
            self.assertTrue((current_metadata / "duplicate_results.json").exists())

    def test_clears_distinct_expense(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_storage = Path(temp_dir) / "run_storage"
            previous_metadata = run_storage / "run_previous" / "metadata"
            current_metadata = run_storage / "run_current" / "metadata"
            previous_metadata.mkdir(parents=True)

            (previous_metadata / "extracted_expenses.json").write_text(
                json.dumps(
                    {
                        "vendor": "Hotel Central",
                        "amount": 300,
                        "currency": "EUR",
                        "date": "2026-06-16",
                    }
                )
            )

            result = agent_e_duplicate(
                {
                    "run_id": "run_current",
                    "base_path": str(current_metadata),
                    "normalized": {
                        "vendor": "Office Depot",
                        "amount": 45,
                        "standard_currency": "EUR",
                        "standard_date": "2026-06-20",
                    },
                }
            )["duplicate_check"]

            self.assertFalse(result["is_duplicate"])
            self.assertEqual("CLEAR", result["status"])
            self.assertIsNone(result["matched_run_id"])

    def test_unknown_date_does_not_auto_reject_even_when_vendor_and_amount_match(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_storage = Path(temp_dir) / "run_storage"
            previous_metadata = run_storage / "run_previous" / "metadata"
            current_metadata = run_storage / "run_current" / "metadata"
            previous_metadata.mkdir(parents=True)

            (previous_metadata / "normalized_expenses.json").write_text(
                json.dumps(
                    {
                        "vendor": "Taxi Express",
                        "amount": 15,
                        "standard_currency": "EUR",
                        "standard_date": "UNKNOWN",
                    }
                )
            )

            result = agent_e_duplicate(
                {
                    "run_id": "run_current",
                    "base_path": str(current_metadata),
                    "normalized": {
                        "vendor": "Taxi Express",
                        "amount": 15,
                        "standard_currency": "EUR",
                        "standard_date": "UNKNOWN",
                    },
                }
            )["duplicate_check"]

            self.assertFalse(result["is_duplicate"])
            self.assertEqual("CLEAR", result["status"])
            self.assertGreaterEqual(result["similarity_score"], 70)


if __name__ == "__main__":
    unittest.main()
