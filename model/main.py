from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from natasha import (
    AddrExtractor,
    Doc,
    MorphVocab,
    NamesExtractor,
    NewsEmbedding,
    NewsNERTagger,
    Segmenter,
)

from .skill_classifier import SkillQualityPrediction, get_classifier


CITY_LIST = [
    "Москва",
    "Санкт-Петербург",
    "Казань",
    "Новосибирск",
    "Екатеринбург",
    "Нижний Новгород",
    "Самара",
    "Ростов-на-Дону",
    "Пермь",
    "Челябинск",
    "Краснодар",
    "Владивосток",
    "Омск",
    "Томск",
    "Уфа",
]

ROLE_KEYWORDS: Dict[str, List[str]] = {
    "flutter разработчик": ["flutter", "flutter developer"],
    "мобильный разработчик": ["мобильный разработчик", "mobile developer", "ios/android"],
    "android разработчик": ["android разработчик", "android developer"],
    "ios разработчик": ["ios разработчик", "ios developer"],
    "qa инженер": ["qa", "тестировщик", "qa engineer"],
    "devops engineer": ["devops"],
    "data analyst": ["data", "аналитик", "data analyst"],
    "ml engineer": ["ml", "machine learning"],
    "backend разработчик": ["backend"],
    "frontend разработчик": ["frontend"],
    "fullstack разработчик": ["fullstack"],
    "product manager": ["product", "pm"],
}

SALARY_PATTERN = re.compile(
    r"(?:зарплат[аы]|ожидани[ея]|компенсаци[яи]|оплата|доход|ставка|получать)\D*"
    r"(\d[\d\s]{2,})(?:\s*[-–—]\s*(\d[\d\s]{2,}))?\s*(тыс(?:яч)?|k)?\s*(руб|₽|usd|\$|eur|€)?",
    re.IGNORECASE,
)

WORK_FORMATS = {
    "удаленно": ["удален", "remote", "wfh", "работать удаленно"],
    "гибрид": ["гибрид", "hybrid"],
    "офис": ["офис", "офлайн", "on-site", "в офисе"],
}

SEGMENTER = Segmenter()
EMBEDDING = NewsEmbedding()
NER_TAGGER = NewsNERTagger(EMBEDDING)
MORPH_VOCAB = MorphVocab()
NAMES_EXTRACTOR = NamesExtractor(MORPH_VOCAB)
ADDR_EXTRACTOR = AddrExtractor(MORPH_VOCAB)


@dataclass
class ResumeProfile:
    raw_text: str
    name: str = "Не указано"
    age: Optional[int] = None
    city: Optional[str] = None
    education: Optional[str] = None
    salary_expectations: Optional[int] = None
    salary_currency: str = "RUB"
    work_format: str = "не указано"
    relocation_ready: bool = False
    preferred_roles: List[str] = field(default_factory=list)
    experience_years: Optional[int] = None
    skills: List[str] = field(default_factory=list)
    qualities: List[str] = field(default_factory=list)

    def to_message(self) -> str:
        salary = (
            f"{self.salary_expectations} {self.salary_currency}"
            if self.salary_expectations
            else "Не указано"
        )
        experience = f"{self.experience_years} лет" if self.experience_years else "Не указано"
        preferred_roles = ", ".join(self.preferred_roles) or "Не указано"
        skills = ", ".join(self.skills) or "Не указано"
        qualities = ", ".join(self.qualities) or "Не указано"

        return (
            f"Имя: {self.name}\n"
            f"Возраст: {self.age or 'Не указано'}\n"
            f"Город проживания: {self.city or 'Не указано'}\n"
            f"Образование: {self.education or 'Не указано'}\n"
            f"Ожидания по зарплате: {salary}\n"
            f"Формат работы: {self.work_format}\n"
            f"Готовность к релокации: {'Да' if self.relocation_ready else 'Нет'}\n"
            f"Опыт (лет): {experience}\n"
            f"Целевые роли: {preferred_roles}\n"
            f"Навыки: {skills}\n"
            f"Личные качества: {qualities}"
        )


class ResumeExtractor:
    def __init__(self):
        self.classifier = get_classifier()

    def parse(self, text: str) -> ResumeProfile:
        doc = self._build_doc(text)
        prediction: SkillQualityPrediction = self.classifier.predict(text)
        profile = ResumeProfile(raw_text=text)

        profile.name = self._extract_name(doc, text)
        profile.age = self._extract_age(text)
        profile.city = self._extract_city(doc, text)
        profile.education = self._extract_education(text)
        salary, currency = self._extract_salary(text)
        profile.salary_expectations = salary
        profile.salary_currency = currency
        profile.work_format = self._detect_work_format(text)
        profile.relocation_ready = self._detect_relocation(text)
        profile.preferred_roles = self._detect_roles(text)
        profile.experience_years = self._detect_experience(text)
        profile.skills = prediction.skills
        profile.qualities = prediction.qualities

        return profile

    @staticmethod
    def _build_doc(text: str) -> Doc:
        doc = Doc(text)
        doc.segment(SEGMENTER)
        doc.tag_ner(NER_TAGGER)
        return doc

    @staticmethod
    def _extract_name(doc: Doc, text: str) -> str:
        for span in doc.spans:
            if span.type == "PER":
                span.normalize(MORPH_VOCAB)
                return span.normal.title()
        matches = list(NAMES_EXTRACTOR(text))
        if matches:
            fact = matches[0].fact
            parts = [fact.first, fact.last, fact.middle]
            name = " ".join(part for part in parts if part)
            return name.strip()
        match = re.search(
            r"(?:Я\s[-—]\s|Меня зовут|Имя[:\s]|ФИО[:\s]|Зовут меня)\s*([А-ЯЁ][а-яё]+(?: [А-ЯЁ][а-яё]+){1,2})",
            text,
            re.IGNORECASE,
        )
        return match.group(1).strip() if match else "Не указано"

    @staticmethod
    def _extract_age(text: str) -> Optional[int]:
        match = re.search(r"(\d{1,2})\s*(?:лет|года|год)", text)
        if match:
            age = int(match.group(1))
            if 14 <= age <= 70:
                return age
        return None

    @staticmethod
    def _extract_city(doc: Doc, text: str) -> Optional[str]:
        for span in doc.spans:
            if span.type == "LOC":
                span.normalize(MORPH_VOCAB)
                return span.normal.title()
        matches = list(ADDR_EXTRACTOR(text))
        for match in matches:
            city = match.fact.city or match.fact.settlement or match.fact.country
            if city:
                return city.title()
        for city in CITY_LIST:
            if city.lower() in text.lower():
                return city
        return None

    @staticmethod
    def _extract_education(text: str) -> Optional[str]:
        education_patterns = [
            r"(?:закончил[аи]?|окончил[аи]?|учился в|по образованию)\s+([^.\n]+)",
            r"(?:факультет|специальность)[:\s]+([^.\n]+)",
        ]
        for pattern in education_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip().rstrip(".")
        return None

    @staticmethod
    def _extract_salary(text: str) -> tuple[Optional[int], str]:
        match = SALARY_PATTERN.search(text)
        if not match:
            return None, "RUB"
        raw_min = int(match.group(1).replace(" ", ""))
        raw_max = match.group(2)
        max_value = int(raw_max.replace(" ", "")) if raw_max else None
        multiplier = 1000 if match.group(3) else 1
        currency_group = match.group(4) or "RUB"
        mapping = {"usd": "USD", "$": "USD", "eur": "EUR", "€": "EUR", "руб": "RUB", "₽": "RUB"}
        currency = mapping.get(currency_group.lower(), "RUB")

        min_salary = raw_min * multiplier
        max_salary = max_value * multiplier if max_value else None
        if max_salary:
            salary = int((min_salary + max_salary) / 2)
        else:
            salary = min_salary
        return salary, currency

    @staticmethod
    def _detect_work_format(text: str) -> str:
        lowered = text.lower()
        for format_name, synonyms in WORK_FORMATS.items():
            if any(word in lowered for word in synonyms):
                return format_name
        return "не указано"

    @staticmethod
    def _detect_relocation(text: str) -> bool:
        lowered = text.lower()
        return "готов к релокации" in lowered or "релокац" in lowered or "готов переехать" in lowered

    @staticmethod
    def _detect_roles(text: str) -> List[str]:
        lowered = text.lower()
        roles = []
        for canonical, keywords in ROLE_KEYWORDS.items():
            if any(keyword in lowered for keyword in keywords):
                roles.append(canonical)
        return roles[:5]

    @staticmethod
    def _detect_experience(text: str) -> Optional[int]:
        match = re.search(
            r"(?:опыт|experience)\s*(?:работы)?\s*(\d{1,2})\s*(?:лет|года|years)",
            text,
            re.IGNORECASE,
        )
        return int(match.group(1)) if match else None


def extract_resume_info(text: str) -> ResumeProfile:
    extractor = ResumeExtractor()
    return extractor.parse(text)