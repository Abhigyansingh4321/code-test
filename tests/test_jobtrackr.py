import csv
import tempfile
import unittest
from pathlib import Path

from jobtrackr.db import add_application, export_csv, list_applications, stats_by_status


class JobTrackrTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.tempdir.name) / "jobs.db")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_add_and_list(self) -> None:
        app_id = add_application(
            self.db_path,
            company="OpenAI",
            role="Software Engineer",
            status="applied",
            applied_on="2026-04-03",
            notes="Referral",
        )
        self.assertEqual(app_id, 1)

        rows = list_applications(self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "OpenAI")

    def test_stats(self) -> None:
        add_application(self.db_path, company="A", role="R1", status="applied", applied_on="2026-01-01")
        add_application(self.db_path, company="B", role="R2", status="interview", applied_on="2026-01-02")
        add_application(self.db_path, company="C", role="R3", status="applied", applied_on="2026-01-03")

        total, grouped = stats_by_status(self.db_path)
        self.assertEqual(total, 3)
        self.assertIn(("applied", 2), grouped)
        self.assertIn(("interview", 1), grouped)

    def test_export_csv(self) -> None:
        add_application(self.db_path, company="A", role="R1", status="applied", applied_on="2026-01-01")
        output = Path(self.tempdir.name) / "out.csv"
        count = export_csv(self.db_path, str(output))

        self.assertEqual(count, 1)
        with output.open("r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["company"], "A")


if __name__ == "__main__":
    unittest.main()
