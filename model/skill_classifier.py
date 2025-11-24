from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline

from .data import data, quality_classes, skill_classes


@dataclass
class SkillQualityPrediction:
    skills: List[str]
    qualities: List[str]


class SkillQualityClassifier:
    """Small multi-label classifier trained on curated Russian résumés."""

    def __init__(self):
        df = pd.DataFrame(data)
        self.skill_classes = skill_classes
        self.quality_classes = quality_classes

        # Build dense label matrix
        skill_labels = pd.DataFrame(0, index=df.index, columns=self.skill_classes)
        for i, skills in enumerate(df["skills"]):
            for skill in skills:
                if skill in skill_labels.columns:
                    skill_labels.at[i, skill] = 1

        quality_labels = pd.DataFrame(0, index=df.index, columns=self.quality_classes)
        for i, qualities in enumerate(df["qualities"]):
            for quality in qualities:
                if quality in quality_labels.columns:
                    quality_labels.at[i, quality] = 1

        self.label_df = pd.concat([skill_labels, quality_labels], axis=1)
        active_mask = (self.label_df.sum(axis=0) > 0)
        self.active_indices = np.where(active_mask)[0]
        self.label_active = self.label_df.loc[:, active_mask]

        self.pipeline = Pipeline(
            steps=[
                ("vect", CountVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True)),
                (
                    "clf",
                    MultiOutputClassifier(
                        LogisticRegression(
                            max_iter=2000,
                            class_weight="balanced",
                            solver="lbfgs",
                        )
                    ),
                ),
            ]
        )
        self.pipeline.fit(df["text"], self.label_active)

    def predict(self, text: str, min_prob: float = 0.35) -> SkillQualityPrediction:
        """Return predicted skills and soft qualities."""
        probabilities = self.pipeline.predict_proba([text])
        # MultiOutputClassifier returns list of arrays
        probs = np.array([p[:, 1] for p in probabilities]).flatten()

        full_probs = np.zeros(len(self.label_df.columns))
        full_probs[self.active_indices] = probs

        num_skills = len(self.skill_classes)
        skill_probs = full_probs[:num_skills]
        quality_probs = full_probs[num_skills:]

        predicted_skills = [
            self.skill_classes[i]
            for i, prob in enumerate(skill_probs)
            if prob >= min_prob
        ]
        predicted_qualities = [
            self.quality_classes[i]
            for i, prob in enumerate(quality_probs)
            if prob >= min_prob
        ]

        return SkillQualityPrediction(
            skills=predicted_skills[:10], qualities=predicted_qualities[:10]
        )


@lru_cache
def get_classifier() -> SkillQualityClassifier:
    return SkillQualityClassifier()

