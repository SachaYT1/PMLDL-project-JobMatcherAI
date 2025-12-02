from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, List, Optional


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = BASE_DIR / "data" / "jobmatcher.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS vacancies (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    city TEXT,
    work_format TEXT,
    salary_min INTEGER,
    salary_max INTEGER,
    currency TEXT,
    experience TEXT,
    skills TEXT,
    description TEXT,
    url TEXT,
    raw_payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_vacancies_city ON vacancies(city);
CREATE INDEX IF NOT EXISTS idx_vacancies_format ON vacancies(work_format);
CREATE INDEX IF NOT EXISTS idx_vacancies_salary ON vacancies(salary_min);
"""


class JobDatabase:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    def upsert(self, rows: Iterable[dict]) -> None:
        payloads = [
            {
                **row,
                "skills": json.dumps(row.get("skills") or []),
                "raw_payload": json.dumps(row.get("raw_payload") or {}, ensure_ascii=False),
            }
            for row in rows
        ]
        if not payloads:
            return
        with self.connection() as conn:
            conn.executemany(
                """
                INSERT INTO vacancies (
                    id, source, title, company, city, work_format,
                    salary_min, salary_max, currency, experience,
                    skills, description, url, raw_payload
                )
                VALUES (
                    :id, :source, :title, :company, :city, :work_format,
                    :salary_min, :salary_max, :currency, :experience,
                    :skills, :description, :url, :raw_payload
                )
                ON CONFLICT(id) DO UPDATE SET
                    source=excluded.source,
                    title=excluded.title,
                    company=excluded.company,
                    city=excluded.city,
                    work_format=excluded.work_format,
                    salary_min=excluded.salary_min,
                    salary_max=excluded.salary_max,
                    currency=excluded.currency,
                    experience=excluded.experience,
                    skills=excluded.skills,
                    description=excluded.description,
                    url=excluded.url,
                    raw_payload=excluded.raw_payload
                """,
                payloads,
            )

    def fetch(
        self,
        *,
        city: Optional[str] = None,
        work_format: Optional[str] = None,
        min_salary: Optional[int] = None,
    ) -> List[sqlite3.Row]:
        query = "SELECT * FROM vacancies"
        filters = []
        params = {}
        if city:
            filters.append("LOWER(city) = LOWER(:city)")
            params["city"] = city
        if work_format and work_format != "не указано":
            filters.append("work_format = :work_format")
            params["work_format"] = work_format
        if min_salary:
            filters.append(
                "(salary_min IS NULL OR salary_min >= :salary_min_threshold)"
            )
            params["salary_min_threshold"] = int(min_salary * 0.6)
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY created_at DESC"

        with self.connection() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()
        return rows

    def count(self) -> int:
        with self.connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM vacancies")
            return cur.fetchone()[0]

    def get(self, vacancy_id: str) -> Optional[sqlite3.Row]:
        with self.connection() as conn:
            cur = conn.execute(
                "SELECT * FROM vacancies WHERE id = :id",
                {"id": vacancy_id},
            )
            return cur.fetchone()

