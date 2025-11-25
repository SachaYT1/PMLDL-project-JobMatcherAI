#!/usr/bin/env python
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List

from data.database import JobDatabase
from ingestion.base import VacancyPayload
from ingestion.habr import HabrIngestor
from ingestion.hh import HHIngestor
from ingestion.telegram import TelegramIngestor


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ingest")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest jobs into SQLite database.")
    parser.add_argument(
        "--sources",
        default="hh,habr",
        help="Comma-separated sources: hh,habr,telegram",
    )
    parser.add_argument("--query", default="junior developer", help="Search query text")
    parser.add_argument("--pages", type=int, default=1, help="Pages per source")
    parser.add_argument("--per-page", type=int, default=20, help="HH vacancies per page")
    parser.add_argument("--db-path", default="data/jobmatcher.db", help="SQLite path")
    parser.add_argument("--hh-area", type=int, default=113, help="HH area id (113=Russia)")
    parser.add_argument("--telegram-api-id", type=int, help="Telegram API ID")
    parser.add_argument("--telegram-api-hash", help="Telegram API hash")
    parser.add_argument(
        "--telegram-channels",
        default="",
        help="Comma-separated Telegram channel usernames (@channel)",
    )
    parser.add_argument(
        "--telegram-limit",
        type=int,
        default=50,
        help="Messages per Telegram channel",
    )
    return parser.parse_args()


def ingest(args: argparse.Namespace) -> None:
    sources = {src.strip() for src in args.sources.split(",") if src.strip()}
    db = JobDatabase(Path(args.db_path))
    rows: List[dict] = []

    if "hh" in sources:
        hh_ingestor = HHIngestor(area=args.hh_area, text=args.query, per_page=args.per_page)
        hh_payloads = hh_ingestor.fetch(pages=args.pages)
        rows.extend(payload.to_row() for payload in hh_payloads)

    if "habr" in sources:
        habr_ingestor = HabrIngestor(query=args.query)
        habr_payloads = habr_ingestor.fetch(pages=args.pages)
        rows.extend(payload.to_row() for payload in habr_payloads)

    if "telegram" in sources:
        channels = [ch.strip() for ch in args.telegram_channels.split(",") if ch.strip()]
        tg_ingestor = TelegramIngestor(
            api_id=args.telegram_api_id,
            api_hash=args.telegram_api_hash,
            channels=channels,
        )
        if tg_ingestor.is_configured():
            tg_payloads = tg_ingestor.collect(limit_per_channel=args.telegram_limit)
            rows.extend(payload.to_row() for payload in tg_payloads)
        else:
            logger.warning("Telegram ingestion requested but not configured; skipping.")

    if not rows:
        logger.warning("No vacancies fetched. Check source configuration.")
        return

    db.upsert(rows)
    logger.info("Ingested %s vacancies into %s", len(rows), args.db_path)


if __name__ == "__main__":
    ingest(parse_args())

