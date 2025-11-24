from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VacancyPayload:
    id: str
    source: str
    title: str
    company: str
    city: Optional[str]
    work_format: Optional[str]
    salary_min: Optional[int]
    salary_max: Optional[int]
    currency: str
    experience: Optional[str]
    skills: List[str]
    description: str
    url: str
    raw_payload: Dict

    def to_row(self) -> Dict:
        return {
            "id": self.id,
            "source": self.source,
            "title": self.title,
            "company": self.company,
            "city": self.city,
            "work_format": self.work_format,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "currency": self.currency,
            "experience": self.experience,
            "skills": self.skills,
            "description": self.description,
            "url": self.url,
            "raw_payload": self.raw_payload,
        }

