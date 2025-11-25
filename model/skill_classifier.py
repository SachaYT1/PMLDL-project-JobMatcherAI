from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import List

from sentence_transformers import util

from .data import (
    quality_aliases,
    quality_classes,
    skill_aliases,
    skill_classes,
)
from .encoders import get_encoder


@dataclass
class SkillQualityPrediction:
    skills: List[str]
    qualities: List[str]


class SkillQualityClassifier:
    """Embedding-based matcher that maps résumé text to curated skill dictionaries."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        self.skill_classes = skill_classes
        self.quality_classes = quality_classes
        self.encoder = get_encoder(model_name)
        self.skill_embeddings = self.encoder.encode(
            self.skill_classes, convert_to_tensor=True, show_progress_bar=False
        )
        self.quality_embeddings = self.encoder.encode(
            self.quality_classes, convert_to_tensor=True, show_progress_bar=False
        )

    def predict(
        self,
        text: str,
        skill_threshold: float = 0.38,
        quality_threshold: float = 0.35,
    ) -> SkillQualityPrediction:
        chunks = self._chunk_text(text)
        if not chunks:
            return SkillQualityPrediction(skills=[], qualities=[])

        text_lower = text.lower()
        chunk_embeddings = self.encoder.encode(
            chunks, convert_to_tensor=True, show_progress_bar=False
        )

        skill_hits = util.semantic_search(
            self.skill_embeddings, chunk_embeddings, top_k=1
        )
        quality_hits = util.semantic_search(
            self.quality_embeddings, chunk_embeddings, top_k=1
        )

        predicted_skills = [
            self.skill_classes[idx]
            for idx, matches in enumerate(skill_hits)
            if matches and matches[0]["score"] >= skill_threshold
        ]
        predicted_qualities = [
            self.quality_classes[idx]
            for idx, matches in enumerate(quality_hits)
            if matches and matches[0]["score"] >= quality_threshold
        ]

        keyword_skills = self._keyword_scan(
            text_lower, self.skill_classes, skill_aliases
        )
        keyword_qualities = self._keyword_scan(
            text_lower, self.quality_classes, quality_aliases
        )

        predicted_skills.extend(keyword_skills)
        predicted_qualities.extend(keyword_qualities)

        # Deduplicate while preserving order
        skills_unique = list(dict.fromkeys(predicted_skills))[:25]
        qualities_unique = list(dict.fromkeys(predicted_qualities))[:15]

        return SkillQualityPrediction(skills=skills_unique, qualities=qualities_unique)

    @staticmethod
    def _chunk_text(text: str) -> List[str]:
        # Split by sentences/paragraphs and filter very short fragments
        rough_chunks = re.split(r"[.\n\r]+", text)
        chunks = [chunk.strip() for chunk in rough_chunks if len(chunk.strip()) > 3]
        return chunks[:80]

    @staticmethod
    def _keyword_scan(
        text_lower: str,
        classes: List[str],
        aliases: dict,
    ) -> List[str]:
        hits = []
        for canonical in classes:
            patterns = aliases.get(canonical, [canonical])
            for pattern in patterns:
                normalized = pattern.lower().strip()
                if not normalized:
                    continue
                if re.search(rf"\b{re.escape(normalized)}\b", text_lower):
                    hits.append(canonical)
                    break
        return hits


@lru_cache(maxsize=1)
def get_classifier() -> SkillQualityClassifier:
    return SkillQualityClassifier()

