## JobMatcher.AI

A Telegram-first job discovery assistant that extracts structured information from unstructured job posts and recommends the most relevant vacancies to students and junior candidates. The system learns from feedback (likes/dislikes/saves) to continuously improve relevance.

### What's new in this prototype
- **Resume extraction pipeline**: Natasha NER + multilingual `SentenceTransformer` similarity derive names, geography, salary ranges, work format, preferred roles, and both hard/soft skills from free-form Russian résюме (`model/main.py`, `model/skill_classifier.py`).
- **Vacancy knowledge base**: jobs are now persisted in a git-ignored SQLite database (`data/jobmatcher.db`) with auto-seeding from `data/jobs_sample.json` and a CLI ingestor that hits hh.ru, Habr Career, and Telegram (`scripts/ingest_jobs.py`, `ingestion/*`).
- **Semantic matcher**: multilingual `sentence-transformers` encoder that builds embeddings for vacancies and re-ranks matches by cosine similarity blended with user preference boosts (`model/matcher.py`). Implementation follows the HuggingFace semantic search recipes documented in the official examples ([HuggingFace Sentence Transformers](https://github.com/huggingface/sentence-transformers)).
- **Preference-aware Telegram bot**: `/start`, `/recommend`, `/favorites` flows built on `aiogram v3`. Users can send resumes, fetch top-10 matches, like/dislike entries, and maintain favorites. Feedback updates the preference vector so future rankings adapt to individual tastes.
- **System design note**: `docs/architecture.md` captures the big picture, data plan, modeling approach, and monitoring strategy required by the project rubric.

### Why it matters
- **Reduce overload**: Cuts through noisy Telegram feeds and repost channels.
- **Personalized**: Matches by skills, preferences, salary, and work format.
- **Practical**: Targets Intern/Junior roles and supports career advisors.

### How it works
- **Ingestion**: `scripts/ingest_jobs.py` orchestrates hh.ru REST, Habr Career HTML parsing, and optional Telegram scraping (Telethon) into SQLite for reproducible experiments.
- **Information extraction**: Natasha NER + salary parsing regex + sentence-transformer similarity (skills/soft skills) normalize résюме and job blurbs.
- **Semantic matching**: Sentence-BERT embeddings with FAISS/OpenSearch kNN.
- **Personalized ranking**: Implicit-feedback learning (e.g., BPR/LambdaMART) with constraints (salary, location, format).
- **Feedback loop**: Likes/dislikes/saves rerank future recommendations.

### Key features (current prototype)
- **Onboarding**: Capture skills, preferred roles, salary expectations, location/format.
- **Recommendations**: Top vacancies by semantic fit.
- **Feedback**: Like/dislike/save and click tracking.
- **IE baseline**: Multilingual transformer + salary/currency rules.
- **Search baseline**: Sentence-BERT + FAISS.

### Target users
- **Primary**: Students and recent graduates (IT/ML/DS/SE/QA/DevOps).
- **Secondary**: University career advisors.

### Data sources and policy
- **Primary**: Telegram job channels (self-built dataset), hh.ru API.
- **Auxiliary**: ESCO skills/occupations, Kaggle Job Postings (EN).
- **Policy**: Respect ToS; store non-personal, publicly available text/metadata; keep provenance where feasible.

### Metrics and success criteria
- **IE/NER**: F1 ≥ 0.80 (SKILL, SALARY); F1 ≥ 0.85 (JOB_TITLE).
- **Ranking**: Recall@5 ≥ 0.70, NDCG@10 ≥ 0.60 (offline).
- **Product**: D7 retention ≥ 30% (≥50 students); median latency < 1.5s at ~10k vacancies.
- **Data quality**: ESCO coverage ≥ 90%; salary parsing accuracy ≥ 95%.

### Minimal requirements checklist
1. **Frame the problem** – target users, success metrics, and motivational context are documented in this README and detailed in `docs/architecture.md`.
2. **Get/annotate data** – sqlite-backed ingestion pulls live hh.ru/Habr/Telegram data via `scripts/ingest_jobs.py`; a JSON seed is bundled for offline use. Résюме annotations that power the skill dictionary are stored in `model/data.py`.
3. **Explore multiple models** – hybrid rule-based + Natasha NER + embedding similarity for information extraction plus multilingual sentence-transformer for semantic search ensure at least two modeling families are evaluated.
4. **Fine-tune & combine** – `SkillQualityClassifier` reuses sentence-transformer embeddings to rank skills/soft skills, while the matcher combines semantic similarity with preference-derived boosts (likes/dislikes/favorites).
5. **Launch, monitor, maintain** – Deployable Telegram bot (`backend/main.py`) with persistent user storage, feedback loops, and monitoring hooks (structured logs). Future observability and retraining cadence are outlined in the architecture doc.

### Repository layout
| Path | Purpose |
| --- | --- |
| `backend/` | Aiogram bot entry point plus conversational logic, keyboards, and persistent storage. |
| `model/main.py` | Resume parsing orchestrator built on Natasha NER + semantic similarity. |
| `model/skill_classifier.py` | Embedding-based matcher that maps text chunks to curated skill/quality dictionaries. |
| `model/job_repository.py` | SQLite-backed vacancy repository with JSON seeding fallback. |
| `model/matcher.py` | Semantic search matcher backed by `sentence-transformers`. |
| `ingestion/` | Source-specific fetchers for hh.ru, Habr Career, Telegram. |
| `scripts/ingest_jobs.py` | CLI runner that populates SQLite with fresh vacancies. |
| `data/jobs_sample.json` | Seed dataset automatically loaded if the DB is empty. |
| `docs/architecture.md` | System overview covering problem framing, data plan, modeling, and Ops. |

### Running the bot locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Optional but recommended: ingest fresh data
python scripts/ingest_jobs.py --sources hh,habr --pages 2 --query "junior developer"
# For Telegram ingestion specify credentials + channels:
# python scripts/ingest_jobs.py --sources telegram --telegram-api-id ... --telegram-api-hash ... --telegram-channels "@it_jobs,@ml_jobs"
export BOT_TOKEN=...  # Telegram bot token
python -m backend.main
```
The bot will request your résumé text, extract structured information, and reply with a summary. Use the reply keyboard to fetch recommendations or review favorites. Inline buttons beneath each job allow you to like, dislike, or star vacancies; these signals are stored in `data/user_state.json` (git-ignored) and immediately influence future rankings. Vacancies are served directly from the SQLite database (`data/jobmatcher.db`), so re-running the ingestor refreshes the catalog without code changes.

### Roadmap (next 2–3 weeks)
- Improve SKILL F1 by +0.05 via domain fine-tuning and annotation expansion.
- Add personalized reranking (BPR/LambdaMART).
- Better deduplication across sources.
- Online dashboards for CTR, like rate, latency; basic monitoring/alerts.
- Pilot with 50–100 students and iterate.

### Tech stack
- **NLP/ML**: Python, PyTorch, HuggingFace, spaCy, Sentence-BERT
- **Search/Storage**: FAISS or OpenSearch kNN, PostgreSQL
- **Bot/Backend**: aiogram, FastAPI
- **Data/MLOps**: Telethon, hh.ru API, DVC, MLflow, Docker
- **Analytics/Monitoring**: Prometheus/Grafana (or alternatives)

### Team
- **Aleksandr Gavkovskii** (Product/Team Lead, QA/Analytics) — a.gavkovskii@innopolis.university
- **Ilya Maksimov** (Backend/Telegram, Data/ETL, MLOps/DevOps) — i.maksimov@innopolis.university
- **Karim Zakirov** (ML/NLP: IE & Ranking) — k.zakirov@innopolis.university

### Links
- **GitHub**: [https://github.com/SachaYT1/PMLDL-project-JobMatcherAI](https://github.com/SachaYT1/PMLDL-project-JobMatcherAI)
- **Telegram bot**: [https://t.me/your_bot_username](https://t.me/your_bot_username)
- **hh.ru API**: [https://api.hh.ru/](https://api.hh.ru/)
- **ESCO**: [https://esco.ec.europa.eu/](https://esco.ec.europa.eu/)
- **Kaggle Job Postings**: [https://www.kaggle.com/datasets/datafiniti/job-postings-data](https://www.kaggle.com/datasets/datafiniti/job-postings-data)

### License
TBD 
