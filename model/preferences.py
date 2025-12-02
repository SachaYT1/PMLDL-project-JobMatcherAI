from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, Set

from .job_repository import Vacancy


@dataclass
class PreferenceVector:
    liked_skills: Counter = field(default_factory=Counter)
    disliked_skills: Counter = field(default_factory=Counter)
    liked_vacancies: Set[str] = field(default_factory=set)
    disliked_vacancies: Set[str] = field(default_factory=set)
    favorite_vacancies: Set[str] = field(default_factory=set)

    @classmethod
    def from_payload(cls, payload: Dict) -> "PreferenceVector":
        return cls(
            liked_skills=Counter(payload.get("liked_skills", {})),
            disliked_skills=Counter(payload.get("disliked_skills", {})),
            liked_vacancies=set(payload.get("liked_vacancies", [])),
            disliked_vacancies=set(payload.get("disliked_vacancies", [])),
            favorite_vacancies=set(payload.get("favorite_vacancies", [])),
        )

    def to_payload(self) -> Dict:
        return {
            "liked_skills": dict(self.liked_skills),
            "disliked_skills": dict(self.disliked_skills),
            "liked_vacancies": list(self.liked_vacancies),
            "disliked_vacancies": list(self.disliked_vacancies),
            "favorite_vacancies": list(self.favorite_vacancies),
        }

    def update_from_vacancy(self, vacancy: Vacancy, feedback: str) -> None:
        if feedback == "like":
            self.liked_vacancies.add(vacancy.id)
            for skill in vacancy.skills:
                self.liked_skills[skill] += 1
        elif feedback == "dislike":
            self.disliked_vacancies.add(vacancy.id)
            for skill in vacancy.skills:
                self.disliked_skills[skill] += 1
        elif feedback == "favorite":
            self.favorite_vacancies.add(vacancy.id)

    def remove_favorite(self, vacancy_id: str) -> None:
        self.favorite_vacancies.discard(vacancy_id)

    def boost_for(self, vacancy: Vacancy) -> float:
        if vacancy.id in self.disliked_vacancies:
            return -0.5
        base = 0.0
        if vacancy.id in self.favorite_vacancies or vacancy.id in self.liked_vacancies:
            base += 0.2

        liked_skill_hits = sum(self.liked_skills.get(skill, 0) for skill in vacancy.skills)
        disliked_hits = sum(self.disliked_skills.get(skill, 0) for skill in vacancy.skills)

        return base + 0.02 * liked_skill_hits - 0.01 * disliked_hits

