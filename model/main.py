from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

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

ROLE_KEYWORDS = [
    "qa",
    "тестировщик",
    "data",
    "devops",
    "ml",
    "аналитик",
    "backend",
    "frontend",
    "fullstack",
    "android",
    "ios",
    "product",
    "pm",
]


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

        prediction: SkillQualityPrediction = self.classifier.predict(text)
        profile = ResumeProfile(raw_text=text)

        profile.name = self._extract_name(text)
        profile.age = self._extract_age(text)
        profile.city = self._extract_city(text)
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
    def _extract_name(text: str) -> str:
        match = re.search(
            r"(?:Я\s[-—]\s|Меня зовут|Имя[:\s]|ФИО[:\s]|Зовут меня)\s*([А-ЯЁ][а-яё]+(?: [А-ЯЁ][а-яё]+){1,2})",
            text,
            re.IGNORECASE,
        )
        return match.group(1).strip() if match else "Не указано"

    @staticmethod
    def _extract_age(text: str) -> Optional[int]:
        match = re.search(r"(\d{2})\s*(?:лет|года|год)", text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _extract_city(text: str) -> Optional[str]:
        match = re.search(
            r"(?:город|г\.|живу в|проживаю в|находжусь в|based in)\s*([А-ЯЁA-Za-z\- ]+)",
            text,
            re.IGNORECASE,
        )
        if match:
            return match.group(1).strip().title()
        for city in CITY_LIST:
            if city.lower() in text.lower():
                return city
        return None

    @staticmethod
    def _extract_education(text: str) -> Optional[str]:
        match = re.search(
            r"(?:Образование|Факультет|Высшее образование|Институт|Университет)[:\s]+([А-ЯЁA-Za-z0-9 ,.\-]+)",
            text,
        )
        return match.group(1).strip() if match else None

    @staticmethod
    def _extract_salary(text: str) -> tuple[Optional[int], str]:
        match = re.search(
            r"(?:зарплат[аы]|ожидани[ея]|компенсаци[яи]|оплата)\D*(\d[\d\s]{3,})(?:\s*(k|тыс\.|тысяч))?\s*(руб|₽|usd|\$|eur|€)?",
            text,
            re.IGNORECASE,
        )
        if not match:
            return None, "RUB"
        raw_value = match.group(1).replace(" ", "")
        multiplier = 1000 if match.group(2) else 1
        currency_group = match.group(3) or "RUB"
        mapping = {"usd": "USD", "$": "USD", "eur": "EUR", "€": "EUR", "руб": "RUB", "₽": "RUB"}
        currency = mapping.get(currency_group.lower() if currency_group else "RUB", "RUB")
        try:
            return int(raw_value) * multiplier, currency
        except ValueError:
            return None, currency

    @staticmethod
    def _detect_work_format(text: str) -> str:
        lowered = text.lower()
        if any(word in lowered for word in ["удал", "remote", "wfh"]):
            return "удаленно"
        if any(word in lowered for word in ["гибрид", "hybrid"]):
            return "гибрид"
        if any(word in lowered for word in ["офис", "on-site", "офлайн"]):
            return "офис"
        return "не указано"

    @staticmethod
    def _detect_relocation(text: str) -> bool:
        lowered = text.lower()
        return "готов к релокации" in lowered or "релокац" in lowered or "готов переехать" in lowered

    @staticmethod
    def _detect_roles(text: str) -> List[str]:
        lowered = text.lower()
        roles = []
        for role in ROLE_KEYWORDS:
            if role in lowered:
                roles.append(role)
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