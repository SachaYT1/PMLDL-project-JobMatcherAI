from __future__ import annotations

import logging
import re
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base import VacancyPayload

logger = logging.getLogger(__name__)


class HabrIngestor:
    BASE_URL = "https://career.habr.com/vacancies"
    SALARY_REGEX = re.compile(
        r"(\d[\d\s]{1,})(?:[-–—](\d[\d\s]{1,}))?\s*(тыс\.?|k)?\s*(руб|₽)?",
        re.IGNORECASE,
    )

    def __init__(self, query: str = "junior", headers: Optional[dict] = None):
        self.query = query
        self.headers = headers or {
            "User-Agent": "Mozilla/5.0 (compatible; JobMatcherBot/1.0)"
        }

    def fetch(self, pages: int = 1) -> List[VacancyPayload]:
        results: List[VacancyPayload] = []
        for page in range(1, pages + 1):
            params = {"page": page, "q": self.query}
            response = requests.get(
                self.BASE_URL, params=params, headers=self.headers, timeout=30
            )
            response.raise_for_status()
            parsed = self._parse_page(response.text)
            logger.info("Habr page %s yielded %s vacancies", page, len(parsed))
            results.extend(parsed)
        return results

    def _parse_page(self, html: str) -> List[VacancyPayload]:
        soup = BeautifulSoup(html, "lxml")
        cards = soup.select("div.vacancy-card")
        payloads: List[VacancyPayload] = []
        for card in cards:
            vacancy_id = card.get("data-vacancy-id")
            title_link = card.select_one("a.vacancy-card__title-link")
            if not vacancy_id or not title_link:
                continue
            title = title_link.get_text(strip=True)
            url = f"https://career.habr.com{title_link.get('href')}"
            company_node = card.select_one(".vacancy-card__company-title a")
            company = company_node.get_text(strip=True) if company_node else "Не указано"
            city_node = card.select_one(".vacancy-card__meta")
            city = city_node.get_text(strip=True) if city_node else None
            salary_node = card.select_one(".vacancy-card__salary")
            salary_text = salary_node.get_text(strip=True) if salary_node else ""
            salary_min, salary_max = self._parse_salary(salary_text)
            description_node = card.select_one(".vacancy-card__description")
            description = description_node.get_text(strip=True) if description_node else ""
            skills = [
                tag.get_text(strip=True)
                for tag in card.select(".vacancy-card__skills span")
            ]
            payloads.append(
                VacancyPayload(
                    id=f"habr_{vacancy_id}",
                    source="habr career",
                    title=title,
                    company=company,
                    city=city,
                    work_format=self._detect_format(description),
                    salary_min=salary_min,
                    salary_max=salary_max,
                    currency="RUB",
                    experience=None,
                    skills=skills,
                    description=description,
                    url=url,
                    raw_payload={"html": str(card)},
                )
            )
        return payloads

    def _parse_salary(self, text: str) -> tuple[Optional[int], Optional[int]]:
        match = self.SALARY_REGEX.search(text)
        if not match:
            return None, None
        min_val = int(match.group(1).replace(" ", ""))
        max_val = match.group(2)
        multiplier = 1000 if match.group(3) else 1
        min_salary = min_val * multiplier
        max_salary = int(max_val.replace(" ", "")) * multiplier if max_val else None
        return min_salary, max_salary

    @staticmethod
    def _detect_format(text: str) -> str:
        lowered = text.lower()
        if "удал" in lowered or "remote" in lowered:
            return "удаленно"
        if "гибрид" in lowered:
            return "гибрид"
        if "офис" in lowered:
            return "офис"
        return "не указано"

