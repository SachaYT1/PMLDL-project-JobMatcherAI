from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List, Optional

from data.database import JobDatabase


FIELD_MAP = {
    "id": "id",
    "name": "title",
    "area_name": "city",
    "employer_name": "company",
    "salary_from": "salary_min",
    "salary_to": "salary_max",
    "salary_currency": "currency",
    "schedule_name": "work_format",
    "experience_name": "experience",
    "snippet_requirement": "requirements",
    "snippet_responsibility": "responsibility",
    "work_format": "work_format_override",
    "professional_roles": "professional_roles",
}


def load_csv(csv_path: Path, db_path: Path) -> None:
    db = JobDatabase(db_path)
    rows: List[Dict] = []
    with csv_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            mapped = map_row(raw)
            rows.append(mapped)
    db.upsert(rows)
    print(f"Loaded {len(rows)} vacancies into {db_path}")


def map_row(raw: Dict[str, str]) -> Dict:
    work_format = (
        raw.get("work_format_override")
        or raw.get("work_format")
        or raw.get("schedule_name")
    )
    work_format = normalize_work_format(work_format or "")
    description_parts = [
        raw.get("requirements") or raw.get("snippet_requirement"),
        raw.get("responsibility") or raw.get("snippet_responsibility"),
    ]
    description = "\n".join(part for part in description_parts if part)

    return {
        "id": f"hhcsv_{raw['id']}",
        "source": "hh.ru",
        "title": raw.get("title") or raw.get("name"),
        "company": raw.get("company") or raw.get("employer_name"),
        "city": raw.get("city") or raw.get("area_name"),
        "work_format": work_format,
        "salary_min": parse_int(raw.get("salary_min") or raw.get("salary_from")),
        "salary_max": parse_int(raw.get("salary_max") or raw.get("salary_to")),
        "currency": raw.get("currency") or raw.get("salary_currency") or "RUR",
        "experience": raw.get("experience") or raw.get("experience_name"),
        "skills": extract_skills(raw),
        "description": description,
        "url": raw.get("url") or "https://hh.ru",
        "raw_payload": raw,
    }


def parse_int(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    value = value.replace(" ", "")
    try:
        return int(value)
    except ValueError:
        return None


def normalize_work_format(value: str) -> str:
    lowered = value.lower()
    if "удал" in lowered:
        return "удаленно"
    if "гибрид" in lowered:
        return "гибрид"
    if "офис" in lowered or "месте" in lowered:
        return "офис"
    return "не указано"


def extract_skills(raw: Dict[str, str]) -> List[str]:
    duties = (raw.get("requirements") or raw.get("snippet_requirement") or "").lower()
    resp = (raw.get("responsibility") or raw.get("snippet_responsibility") or "").lower()
    text = f"{duties}\n{resp}"
    known_skills = [
        "python",
        "java",
        "kotlin",
        "swift",
        "flutter",
        "dart",
        "react",
        "vue",
        "angular",
        "typescript",
        "docker",
        "kubernetes",
        "ci/cd",
        "graphql",
        "rest",
        "websocket",
        "firebase",
        "postgresql",
        "mysql",
        "mongodb",
        "fastapi",
        "django",
        "laravel",
        "php",
        "go",
        "c#",
        ".net",
    ]
    result = [skill for skill in known_skills if skill in text]
    return result


def main():
    parser = argparse.ArgumentParser(description="Load CSV vacancies into SQLite database")
    parser.add_argument(
        "--csv",
        default="data/vacancies_full.csv",
        help="Path to vacancies CSV file",
    )
    parser.add_argument(
        "--db",
        default="data/jobmatcher.db",
        help="Path to SQLite database",
    )
    args = parser.parse_args()
    load_csv(Path(args.csv), Path(args.db))


if __name__ == "__main__":
    main()

