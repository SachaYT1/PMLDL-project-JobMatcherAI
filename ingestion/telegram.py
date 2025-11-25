from __future__ import annotations

import asyncio
import logging
import re
from typing import List, Optional, Sequence

from telethon import TelegramClient

from model.main import CITY_LIST
from model.skill_classifier import get_classifier

from .base import VacancyPayload

logger = logging.getLogger(__name__)

SALARY_PATTERN = re.compile(
    r"(\d[\d\s]{2,})(?:\s*[-–—]\s*(\d[\d\s]{2,}))?\s*(тыс(?:яч)?|k)?\s*(руб|₽|usd|\$|eur|€)?",
    re.IGNORECASE,
)


class TelegramIngestor:
    def __init__(
        self,
        api_id: Optional[int],
        api_hash: Optional[str],
        channels: Optional[Sequence[str]] = None,
        session_path: str = "data/telegram.session",
    ):
        self.api_id = api_id
        self.api_hash = api_hash
        self.channels = list(channels or [])
        self.session_path = session_path
        self.skill_classifier = get_classifier()
        if self.api_id and self.api_hash:
            self.client = TelegramClient(self.session_path, self.api_id, self.api_hash)
        else:
            self.client = None

    def is_configured(self) -> bool:
        return bool(self.client and self.channels)

    def collect(self, limit_per_channel: int = 100) -> List[VacancyPayload]:
        if not self.is_configured():
            logger.warning("Telegram credentials or channels are missing; skipping ingestion.")
            return []
        return asyncio.run(self._collect(limit_per_channel))

    async def _collect(self, limit_per_channel: int) -> List[VacancyPayload]:
        assert self.client  # guarded by is_configured
        results: List[VacancyPayload] = []
        async with self.client:
            for channel in self.channels:
                logger.info("Fetching Telegram messages from %s", channel)
                async for message in self.client.iter_messages(channel, limit=limit_per_channel):
                    text = message.message
                    if not text:
                        continue
                    payload = self._parse_message(channel, message.id, text)
                    if payload:
                        results.append(payload)
        return results

    def _parse_message(self, channel: str, message_id: int, text: str) -> Optional[VacancyPayload]:
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return None
        title = lines[0][:120]
        salary_min, salary_max, currency = self._parse_salary(text)
        skills_prediction = self.skill_classifier.predict(text)
        city = self._detect_city(text)
        work_format = self._detect_work_format(text)
        url_channel = channel.lstrip("@")
        url = f"https://t.me/{url_channel}/{message_id}"

        return VacancyPayload(
            id=f"tg_{url_channel}_{message_id}",
            source="telegram",
            title=title,
            company=url_channel,
            city=city,
            work_format=work_format,
            salary_min=salary_min,
            salary_max=salary_max,
            currency=currency,
            experience=None,
            skills=skills_prediction.skills,
            description=text,
            url=url,
            raw_payload={"channel": channel, "message_id": message_id},
        )

    @staticmethod
    def _detect_city(text: str) -> Optional[str]:
        lowered = text.lower()
        for city in CITY_LIST:
            if city.lower() in lowered:
                return city
        return None

    @staticmethod
    def _detect_work_format(text: str) -> str:
        lowered = text.lower()
        if "удал" in lowered or "remote" in lowered:
            return "удаленно"
        if "гибрид" in lowered:
            return "гибрид"
        if "офис" in lowered:
            return "офис"
        return "не указано"

    @staticmethod
    def _parse_salary(text: str) -> tuple[Optional[int], Optional[int], str]:
        match = SALARY_PATTERN.search(text)
        if not match:
            return None, None, "RUB"
        min_value = int(match.group(1).replace(" ", ""))
        max_value = int(match.group(2).replace(" ", "")) if match.group(2) else None
        multiplier = 1000 if match.group(3) else 1
        currency_map = {"usd": "USD", "$": "USD", "eur": "EUR", "€": "EUR", "руб": "RUB", "₽": "RUB"}
        currency = currency_map.get((match.group(4) or "руб").lower(), "RUB")
        min_salary = min_value * multiplier
        max_salary_value = max_value * multiplier if max_value else None
        return min_salary, max_salary_value, currency

