## JobMatcher.AI

A Telegram-first job discovery assistant that extracts structured information from unstructured job posts and recommends the most relevant vacancies to students and junior candidates. The system learns from feedback (likes/dislikes/saves) to continuously improve relevance.

### Why it matters
- **Reduce overload**: Cuts through noisy Telegram feeds and repost channels.
- **Personalized**: Matches by skills, preferences, salary, and work format.
- **Practical**: Targets Intern/Junior roles and supports career advisors.

### How it works
- **Ingestion**: Collects posts from Telegram channels (and optionally hh.ru, Habr Career).
- **Information extraction**: Transformer-based NER (mBERT/XLM-R) + rules for salary parsing; skill normalization via ESCO.
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
