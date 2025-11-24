from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional


BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_PATH = BASE_DIR / "data" / "jobs_sample.json"


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
    experience: str
    skills: List[str]
    description: str
    source: str
    url: str

    def to_message(self) -> str:
        salary = "Не указано"
        if self.salary_min:
            salary = f"{self.salary_min}-{self.salary_max or self.salary_min} {self.currency}"
        skill_line = ", ".join(self.skills[:8])
        return (
            f"<b>{self.title}</b> в {self.company}\n"
            f"📍 {self.city} · {self.work_format}\n"
            f"💰 {salary}\n"
            f"🛠 Навыки: {skill_line}\n"
            f"{self.description}\n"
            f"🔗 {self.url}"
        )


class JobRepository:
    def __init__(self, dataset_path: Path = DATASET_PATH):
        self.dataset_path = dataset_path
        self._vacancies = self._load()
        self._index = {vac.id: vac for vac in self._vacancies}

    def _load(self) -> List[Vacancy]:
        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset {self.dataset_path} not found")
        with self.dataset_path.open(encoding="utf-8") as f:
            data = json.load(f)
        return [Vacancy(**item) for item in data]

    def all(self) -> List[Vacancy]:
        return list(self._vacancies)

    def get(self, vacancy_id: str) -> Optional[Vacancy]:
        return self._index.get(vacancy_id)

    def filter(
        self,
        *,
        city: Optional[str] = None,
        work_format: Optional[str] = None,
        min_salary: Optional[int] = None,
    ) -> List[Vacancy]:
        candidates: Iterable[Vacancy] = self._vacancies
        if city:
            candidates = [v for v in candidates if v.city.lower() == city.lower()]
        if work_format and work_format != "не указано":
            candidates = [v for v in candidates if v.work_format == work_format]
        if min_salary:
            candidates = [
                v
                for v in candidates
                if v.salary_min and v.salary_min >= min_salary * 0.6
            ]
        return list(candidates)

