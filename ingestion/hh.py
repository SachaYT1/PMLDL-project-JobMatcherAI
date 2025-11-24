from __future__ import annotations

import logging
from typing import List, Optional

import requests

from .base import VacancyPayload

logger = logging.getLogger(__name__)


class HHIngestor:
    BASE_URL = "https://api.hh.ru/vacancies"

    def __init__(self, area: int = 113, text: str = "junior", per_page: int = 20):
        self.area = area
        self.text = text
        self.per_page = per_page

    def fetch(self, pages: int = 1) -> List[VacancyPayload]:
        payloads: List[VacancyPayload] = []
        for page in range(pages):
            params = {
                "area": self.area,
                "text": self.text,
                "per_page": self.per_page,
                "page": page,
                "only_with_salary": False,
            }
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            logger.info("Fetched %s HH vacancies on page %s", len(items), page)
            for item in items:
                payload = self._parse_item(item)
                if payload:
                    payloads.append(payload)
        return payloads

    def _parse_item(self, item: dict) -> Optional[VacancyPayload]:
        try:
            vacancy_id = f"hh_{item['id']}"
            title = item["name"]
            company = (
                item.get("employer", {}).get("name")
                or item.get("department", {}).get("name")
                or "Не указано"
            )
            city = item.get("area", {}).get("name")
            schedule_name = (item.get("schedule") or {}).get("name", "").lower()
            work_format = self._map_schedule(schedule_name)
            salary_block = item.get("salary") or {}
            salary_min = salary_block.get("from")
            salary_max = salary_block.get("to")
            currency = salary_block.get("currency", "RUR")
            skills = [skill["name"] for skill in item.get("key_skills", [])]
            description_parts = [
                (item.get("snippet") or {}).get("responsibility"),
                (item.get("snippet") or {}).get("requirement"),
            ]
            description = "\n".join(part for part in description_parts if part)
            url = item.get("alternate_url") or item.get("url")

            return VacancyPayload(
                id=vacancy_id,
                source="hh.ru",
                title=title.strip(),
                company=company.strip(),
                city=city,
                work_format=work_format,
                salary_min=salary_min,
                salary_max=salary_max,
                currency=currency or "RUR",
                experience=(item.get("experience") or {}).get("name"),
                skills=skills,
                description=description.strip(),
                url=url,
                raw_payload=item,
            )
        except KeyError as exc:
            logger.warning("Failed to parse HH vacancy: %s", exc)
            return None

    @staticmethod
    def _map_schedule(schedule_name: str) -> str:
        if "удален" in schedule_name:
            return "удаленно"
        if "гибрид" in schedule_name or "частично" in schedule_name:
            return "гибрид"
        if schedule_name:
            return "офис"
        return "не указано"

