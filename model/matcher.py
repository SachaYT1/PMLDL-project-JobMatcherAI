from __future__ import annotations

from typing import List, Optional, Tuple

from sentence_transformers import util

from .job_repository import JobRepository, Vacancy
from .main import ResumeProfile
from .preferences import PreferenceVector
from .encoders import get_encoder


class JobMatcher:
    def __init__(
        self,
        repository: Optional[JobRepository] = None,
        model_name: str = "paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self.repository = repository or JobRepository()
        self.vacancies = self.repository.all()
        self.model = get_encoder(model_name)
        self.id_to_index = {vac.id: idx for idx, vac in enumerate(self.vacancies)}

        corpus_texts = [self._vacancy_to_text(v) for v in self.vacancies]
        self.corpus_embeddings = self.model.encode(
            corpus_texts, convert_to_tensor=True, show_progress_bar=False
        )

    def recommend(
        self,
        profile: ResumeProfile,
        preferences: Optional[PreferenceVector] = None,
        limit: int = 10,
    ) -> List[Tuple[Vacancy, float]]:
        preferred_candidates = self.repository.filter(
            city=profile.city,
            work_format=profile.work_format,
            min_salary=profile.salary_expectations,
        )
        candidates = preferred_candidates or self.vacancies
        candidate_indices = [self.id_to_index[v.id] for v in candidates]
        candidate_embeddings = self.corpus_embeddings[candidate_indices]

        query_text = self._profile_to_text(profile)
        query_embedding = self.model.encode(
            query_text, convert_to_tensor=True, show_progress_bar=False
        )

        hits = util.semantic_search(
            query_embedding, candidate_embeddings, top_k=min(limit * 3, len(candidates))
        )[0]

        scored: List[Tuple[Vacancy, float]] = []
        for hit in hits:
            vacancy_idx = candidate_indices[hit["corpus_id"]]
            vacancy = self.vacancies[vacancy_idx]
            similarity = float(hit["score"])
            boost = preferences.boost_for(vacancy) if preferences else 0.0
            scored.append((vacancy, similarity + boost))

        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[:limit]

    def _vacancy_to_text(self, vacancy: Vacancy) -> str:
        skill_line = ", ".join(vacancy.skills)
        return (
            f"{vacancy.title}. Компания: {vacancy.company}. "
            f"Город: {vacancy.city}. Формат: {vacancy.work_format}. "
            f"Навыки: {skill_line}. Описание: {vacancy.description}"
        )

    def _profile_to_text(self, profile: ResumeProfile) -> str:
        skill_line = ", ".join(profile.skills)
        role_line = ", ".join(profile.preferred_roles)
        return (
            f"Кандидат из города {profile.city or 'неизвестно'}, "
            f"формат {profile.work_format}, зарплата {profile.salary_expectations or 'не указано'}. "
            f"Навыки: {skill_line}. Роли: {role_line}. "
            f"Ожидания: {profile.raw_text}"
        )

