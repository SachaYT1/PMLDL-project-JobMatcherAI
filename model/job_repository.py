from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from data.database import JobDatabase

BASE_DIR = Path(__file__).resolve().parents[1]
CSV_DATASET_PATH = BASE_DIR / "data" / "vacancies_full.csv"
SAMPLE_DATASET_PATH = BASE_DIR / "data" / "jobs_sample.json"


@dataclass
class Vacancy:
    id: str
    title: str
    company: str
    city: str
    work_format: str
    salary_min: Optional[int]
    salary_max: Optional[int]
    currency: str
    experience: Optional[str]
    skills: List[str]
    description: str
    source: str
    url: str

    def to_message(self) -> str:
        salary = "Не указано"
        if self.salary_min:
            max_part = self.salary_max or self.salary_min
            salary = f"{self.salary_min}-{max_part} {self.currency}"
        skill_line = ", ".join(self.skills[:8]) or "—"
        return (
            f"<b>{self.title}</b> в {self.company}\n"
            f"📍 {self.city or '—'} · {self.work_format or '—'}\n"
            f"💰 {salary}\n"
            f"🛠 Навыки: {skill_line}\n"
            f"{self.description}\n"
            f"🔗 {self.url}"
        )


class JobRepository:
    def __init__(
        self,
        database: Optional[JobDatabase] = None,
        seed_dataset: Path = SAMPLE_DATASET_PATH,
    ):
        self.database = database or JobDatabase()
        self.seed_dataset = seed_dataset
        self._ensure_seed()

    def _ensure_seed(self) -> None:
        if self.database.count() > 0:
            return

        if CSV_DATASET_PATH.exists():
            rows = self._load_csv_seed(CSV_DATASET_PATH)
            if rows:
                self.database.upsert(rows)
                return

        if self.seed_dataset.exists():
            with self.seed_dataset.open(encoding="utf-8") as f:
                data = json.load(f)
            self.database.upsert(data)

    def all(self) -> List[Vacancy]:
        rows = self.database.fetch()
        return [self._row_to_vacancy(row) for row in rows]

    def get(self, vacancy_id: str) -> Optional[Vacancy]:
        row = self.database.get(vacancy_id)
        if not row:
            return None
        return self._row_to_vacancy(row)

    def filter(
        self,
        *,
        city: Optional[str] = None,
        work_format: Optional[str] = None,
        min_salary: Optional[int] = None,
    ) -> List[Vacancy]:
        rows = self.database.fetch(
            city=city,
            work_format=work_format,
            min_salary=min_salary,
        )
        return [self._row_to_vacancy(row) for row in rows]

    @staticmethod
    def _row_to_vacancy(row) -> Vacancy:
        skills = []
        if row["skills"]:
            try:
                skills = json.loads(row["skills"])
            except json.JSONDecodeError:
                skills = []
        return Vacancy(
            id=row["id"],
            title=row["title"],
            company=row["company"] or "Не указано",
            city=row["city"] or "—",
            work_format=row["work_format"] or "не указано",
            salary_min=row["salary_min"],
            salary_max=row["salary_max"],
            currency=row["currency"] or "RUB",
            experience=row["experience"],
            skills=skills,
            description=row["description"] or "",
            source=row["source"],
            url=row["url"],
        )

    @staticmethod
    def _load_csv_seed(csv_path: Path) -> List[dict]:
        rows: List[dict] = []
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                description = "\n".join(
                    part
                    for part in [
                        raw.get("snippet_requirement") or raw.get("requirements"),
                        raw.get("snippet_responsibility") or raw.get("responsibility"),
                    ]
                    if part
                )
                rows.append(
                    {
                        "id": f"hhcsv_{raw['id']}",
                        "source": "hh.ru",
                        "title": raw.get("name") or raw.get("title"),
                        "company": raw.get("employer_name") or raw.get("company"),
                        "city": raw.get("area_name") or raw.get("city"),
                        "work_format": JobRepository._normalize_work_format(
                            raw.get("work_format") or raw.get("schedule_name") or ""
                        ),
                        "salary_min": JobRepository._parse_int(
                            raw.get("salary_from")
                        ),
                        "salary_max": JobRepository._parse_int(
                            raw.get("salary_to")
                        ),
                        "currency": raw.get("salary_currency") or "RUR",
                        "experience": raw.get("experience_name"),
                        "skills": [],
                        "description": description,
                        "url": raw.get("url") or "https://hh.ru",
                        "raw_payload": raw,
                    }
                )
        return rows

    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        if not value:
            return None
        value = value.replace(" ", "")
        try:
            return int(value)
        except ValueError:
            return None

    @staticmethod
    def _normalize_work_format(value: str) -> str:
        lowered = value.lower()
        if "удал" in lowered or "remote" in lowered:
            return "удаленно"
        if "гибрид" in lowered:
            return "гибрид"
        if "офис" in lowered or "месте" in lowered:
            return "офис"
        return "не указано"

