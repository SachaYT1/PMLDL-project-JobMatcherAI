## JobMatcher.AI System Overview

### 1. Problem framing & users
- **Primary user**: Russian-speaking junior candidates who search for internships and entry-level IT jobs inside Telegram job channels and repost groups. Their pain is information overload and the lack of structured, personalized recommendations.
- **Secondary user**: University career center staff who need a light-weight assistant to help dozens of students at once.
- **Outcome metric**: Relevant top-10 job list within ≤1.5 s latency, D7 retention ≥30% for the student cohort, as outlined in the project README.

### 2. Data plan
| Stage | Source | Notes |
| --- | --- | --- |
| Ingestion | Telegram channels (Telethon), hh.ru API, Habr Career RSS/API | Fetch raw HTML/Markdown posts + metadata. Store in `data/raw/{source}/`. |
| Annotation | Semi-automatic: regex/rules for salary, geo, format; transformer NER (mBERT/XLM-R) for entities; manual review via lightweight annotation UI. | Produce `data/processed/jobs.parquet` with normalized schema. |
| Feedback | Bot interactions (likes/dislikes/saves, CTR). | Persist per-user feedback for implicit preference modeling. |

### 3. Modeling strategy
1. **Information extraction**: 
   - Resume parsing uses hybrid regex + `SkillQualityClassifier` trained on curated Russian résumés (`model/skill_classifier.py`).
   - Salary/location/work-format extracted with domain regex + city gazetteer.
2. **Semantic matching**:
   - Use multilingual `sentence-transformers` encoder (`paraphrase-multilingual-MiniLM-L12-v2`) to embed resumes and job posts.
   - `JobMatcher` filters by hard constraints (salary, format, location) then re-ranks with cosine similarity (`model/matcher.py`). Reference implementation follows Hugging Face semantic search patterns ([HuggingFace Sentence Transformers](https://github.com/huggingface/sentence-transformers) via Context7 docs).
3. **Personalized reranking**:
   - Store incremental user feedback features (liked skill n-grams, rejected companies).
   - Blend similarity score with preference score via weighted sum; ready for future BPR fine-tuning.

### 4. Deployment, monitoring, maintenance
- **Bot**: `aiogram`-based Telegram bot (`backend/main.py`) exposing `/start`, `/resume`, `/recommend`, `/favorites`.
- **Serving**: Stateless bot workers pull embeddings and metadata from local cache; job embeddings pre-built via `scripts/build_index.py`.
- **Monitoring**: Structured logs (JSON) for end-to-end latency, hit rate (recommendations served), and feedback counters. Future work: ship metrics to Prometheus/Grafana as noted in README.
- **Maintenance**: DVC/MLflow track datasets and models; nightly cron re-ingests vacancies, retrains matcher if drift>ε; manual QA on new data slices.

### 5. Minimal requirements coverage
1. **Framing** – covered in sections 1–2.
2. **Data acquisition & exploration** – ingestion plan + curated seed dataset in `data/jobs_sample.json`.
3. **Model exploration** – hybrid IE + neural semantic search; ready hooks for alternative encoders/BPR.
4. **Fine-tuning & combination** – `SkillQualityClassifier` fine-tunes logistic heads; matcher blends semantic + preference signals.
5. **Launch & monitoring** – Production-ready bot workflow, logging hooks, and persistence layer for continuous learning.

