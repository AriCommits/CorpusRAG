import csv
import json
from pathlib import Path


class QuizExporter:
    """Export quizzes to JSON or CSV format."""

    def export_json(self, quiz_data: list[dict], output_path: Path | str):
        """Export quiz to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(quiz_data, f, indent=2, ensure_ascii=False)

    def export_csv(self, quiz_data: list[dict], output_path: Path | str):
        """Export quiz to CSV file."""
        if not quiz_data:
            return

        keys = quiz_data[0].keys()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(quiz_data)
