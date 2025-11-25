import re
from typing import List, Dict, Any, Tuple

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

# ============================================================
# 1. ИМПОРТ ДАТАСЕТА
# ============================================================
# Ожидается, что в model/data.py есть переменная:
# data = [
#   {
#       "text": "...",
#       "job_role": "разработчик" / "аналитик" / ... (может быть None),
#       "skills": ["python", "django", ...] (может быть пусто),
#       "experience_level": "junior/middle/senior/lead" (может быть None),
#       "work_format": "офис/удалёнка/гибрид/..." (может быть None),
#       "salary_min": 180000 (может быть None),
#       "company_field": "it/финансы/..." (может быть None),
#   },
#   ...
# ]
from model.data import data


# ============================================================
# 2. СЛОВАРИ СИНОНИМОВ / ПОДСКАЗКИ
# ============================================================

# — должности для эвристик (кроме ML)
JOB_TITLE_HEADER_PATTERNS = [
    r"вакансия[:\- ]+(.*)",
    r"позиция[:\- ]+(.*)",
    r"ищем[:\- ]+(.*)",
    r"требуется[:\- ]+(.*)",
    r"we are looking for[:\- ]+(.*)",
    r"we’re hiring[:\- ]+(.*)",
]

JOB_ROLE_KEYWORDS = {
    "Backend Developer": [
        "backend", "back-end", "бэкенд", "server-side",
        "python developer", "backend developer", "backend engineer"
    ],
    "Frontend Developer": [
        "frontend", "front-end", "фронтенд", "react developer",
        "javascript developer", "ui developer"
    ],
    "Fullstack Developer": [
        "fullstack", "full-stack", "full stack", "фуллстек"
    ],
    "DevOps Engineer": [
        "devops", "dev ops", "sre", "site reliability"
    ],
    "Data Scientist": [
        "data scientist", "data science", "ml engineer", "machine learning engineer"
    ],
    "Data Analyst": [
        "data analyst", "аналитик данных", "product analyst", "bi analyst"
    ],
    "QA Engineer": [
        "qa", "qa engineer", "test engineer", "тестировщик"
    ],
    "UI/UX Designer": [
        "designer", "ui/ux", "ux designer", "product designer", "дизайнер"
    ],
    "Product Manager": [
        "product manager", "продакт менеджер", "product owner"
    ],
    "Project Manager": [
        "project manager", "руководитель проекта", "pm"
    ],
}

# — подсказки по уровню
EXPERIENCE_HINTS = {
    "junior": ["junior", "джуниор", "начинающий", "стажер", "интернатура"],
    "middle": ["middle", "мидл", "middle+", "middle-"],
    "senior": ["senior", "сеньор", "старший"],
    "lead": ["lead", "team lead", "tech lead", "ведущий", "руководитель"],
}

# — подсказки по формату работы
REMOTE_WORDS = [
    "удаленно", "удалённо", "remote", "работа из дома", "home office",
    "полностью удал", "full remote"
]
OFFICE_WORDS = [
    "офис", "в офисе", "офис в", "office"
]
HYBRID_WORDS = [
    "гибрид", "hybrid", "частично удаленно", "частично удалённо",
    "несколько дней в офисе", "3 дня офис", "офис/удаленно", "офис + удаленно",
]

# — синонимы навыков (добавляются к ML)
SKILL_SYNONYMS = {
    # Backend
    "python": ["python", "py", "python3", "python 3"],
    "fastapi": ["fastapi", "fast api", "fast-api"],
    "django": ["django"],
    "flask": ["flask"],
    "celery": ["celery"],
    "aiohttp": ["aiohttp", "aio http"],
    "postgresql": ["postgresql", "postgres", "pgsql"],
    "mysql": ["mysql"],
    "redis": ["redis"],
    "rabbitmq": ["rabbitmq", "rabbit mq"],
    "mongodb": ["mongodb", "mongo"],

    # Frontend
    "react": ["react", "reactjs", "react.js"],
    "typescript": ["typescript", "ts"],
    "javascript": ["javascript", "js"],
    "redux": ["redux"],
    "mobx": ["mobx"],
    "next.js": ["next.js", "next js", "nextjs"],
    "node.js": ["node.js", "nodejs", "node js"],
    "css": ["css", "css3"],
    "html": ["html", "html5"],
    "webpack": ["webpack"],
    "vite": ["vite"],
    "spa": ["spa", "single page application"],

    # DevOps
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "terraform": ["terraform"],
    "ansible": ["ansible"],
    "jenkins": ["jenkins"],
    "gitlab ci": ["gitlab ci", "gitlab-ci", "gitlabci"],
    "grafana": ["grafana"],
    "prometheus": ["prometheus"],
    "elk": ["elk", "elk stack"],

    # Data / ML
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "tensorflow": ["tensorflow", "tf"],
    "pytorch": ["pytorch"],
    "xgboost": ["xgboost"],
    "machine learning": ["machine learning", "ml"],
    "sql": ["sql"],

    # Tools
    "git": ["git"],
    "jira": ["jira"],
    "confluence": ["confluence"],
    "linux": ["linux"],
}


# ============================================================
# 3. ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def _normalize_list_field(series, default_empty=True) -> pd.Series:
    """Гарантирует, что колонка — список (для skills)."""
    cleaned = []
    for v in series:
        if isinstance(v, list):
            cleaned.append(v)
        elif pd.isna(v):
            cleaned.append([] if default_empty else [None])
        else:
            cleaned.append([v])
    return pd.Series(cleaned)


def _extract_header_job_title(text: str) -> str | None:
    """Пытаемся вытащить должность из заголовка 'Вакансия: ...', 'Ищем ...' и т.п."""
    for pattern in JOB_TITLE_HEADER_PATTERNS:
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            role = m.group(1).strip()
            role = role.split("\n")[0].strip()
            role = re.sub(r"\(.*?\)", "", role).strip()
            return role if len(role) > 2 else None
    return None


def _extract_job_role_smart(text: str) -> str | None:
    """
    Извлекает должность из текста максимально точно.
    Работает по шаблонам, ключевым словам и сокращает длинные фразы.
    """

    t = text.lower()

    # --- 1) Попытка найти строку вида:
    # "Ищем Frontend разработчика", "Требуется Senior Backend Developer"
    header_patterns = [
        r"(?:вакансия[:\- ]+)(.+)",
        r"(?:ищем[:\- ]+)(.+)",
        r"(?:требуется[:\- ]+)(.+)",
        r"(?:мы ищем[:\- ]+)(.+)",
        r"(?:we are looking for[:\- ]+)(.+)",
        r"(?:we’re hiring[:\- ]+)(.+)"
    ]

    for pat in header_patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            role = m.group(1).strip()
            # убираем всё после первого дефиса/точки
            role = re.split(r"[.,;!]| для | чтобы ", role)[0].strip()
            if 3 <= len(role) <= 60:
                return role

    # --- 2) Прямые шаблоны должностей
    ROLE_PATTERNS = [
        r"(senior\s+[a-zа-я0-9\- ]+developer)",
        r"(middle\s+[a-zа-я0-9\- ]+developer)",
        r"(junior\s+[a-zа-я0-9\- ]+developer)",
        r"([a-zа-я0-9\- ]+developer)",
        r"([a-zа-я ]+разработчик)",
        r"(team lead [a-zа-я ]+)",
        r"(tech lead [a-zа-я ]+)",
        r"([a-zа-я ]+analyst)",
        r"([a-zа-я ]+инженер)",
    ]

    for pat in ROLE_PATTERNS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            role = m.group(1).strip()
            role = re.split(r"[.,;!]| для | чтобы ", role)[0].strip()
            # Капитализация
            return role.capitalize()

    return None


def _heuristic_experience(text: str, ml_pred: List[str]) -> str:
    """Комбинируем ML-предсказание и эвристику по словам/годам."""
    if ml_pred:
        return ml_pred[0]

    t = text.lower()

    # ключевые слова
    for lvl, kws in EXPERIENCE_HINTS.items():
        if any(kw in t for kw in kws):
            return lvl

    # по годам опыта
    m = re.search(r"опыт.*?(\d+)\s*год", t)
    if m:
        years = int(m.group(1))
        if years <= 1:
            return "junior"
        elif 2 <= years <= 3:
            return "middle"
        elif 4 <= years <= 5:
            return "senior"
        else:
            return "lead"

    return "не указан"


def _heuristic_work_format(text: str, ml_pred: List[str]) -> str:
    """Определяем формат работы, с приоритетом 'гибрид', если явно и офис, и удалёнка."""
    t = text.lower()

    has_remote = any(w in t for w in REMOTE_WORDS)
    has_office = any(w in t for w in OFFICE_WORDS)
    has_hybrid_word = any(w in t for w in HYBRID_WORDS)

    # 1. Явный гибрид по словам
    if has_hybrid_word or (has_remote and has_office):
        return "гибрид"

    # 2. Если ML что-то нашёл — используем
    if ml_pred:
        return ml_pred[0]

    # 3. fallback по ключам
    if has_remote and not has_office:
        return "удалёнка"
    if has_office and not has_remote:
        return "офис"

    return "не указан"


def _extract_skills_by_synonyms(text: str) -> List[str]:
    """Достаём навыки по словарю синонимов."""
    t = text.lower()
    found = []
    for canonical, synonyms in SKILL_SYNONYMS.items():
        if any(s in t for s in synonyms):
            found.append(canonical)
    return sorted(set(found))


def _extract_salary(text: str) -> Tuple[int | None, int | None]:
    """
    Аккуратно достаём зарплату:
    - диапазон: 180000–220000, 180 000 - 220 000, от 180000 до 220000
    - от X
    """
    t = text.lower()

    # Уберём пробелы внутри чисел, но не вокруг "лет"
    def _clean_num(s: str) -> int:
        return int(s.replace(" ", "").replace("\u00a0", ""))

    # 1) Диапазон: от 180 000 до 240 000 / 180000–240000 / 180000-240000
    range_patterns = [
        r"от\s*(\d[\d\s]{3,7})\s*до\s*(\d[\d\s]{3,7})",
        r"(\d[\d\s]{3,7})\s*[–—-]\s*(\d[\d\s]{3,7})\s*(?:руб|р|рублей)?",
    ]
    for pat in range_patterns:
        m = re.search(pat, t)
        if m:
            n1, n2 = _clean_num(m.group(1)), _clean_num(m.group(2))
            # фильтр против "1–2 лет"
            if n1 < 10000 and n2 < 10000:
                continue
            return min(n1, n2), max(n1, n2)

    # 2) "зарплата от 180000", "от 200 000 руб."
    m = re.search(r"от\s*(\d[\d\s]{3,7})\s*(?:руб|р|рублей)?", t)
    if m:
        n = _clean_num(m.group(1))
        if n >= 10000:
            return n, None

    # 3) Одиночное число, похожее на зарплату
    m = re.search(r"(\d[\d\s]{4,7})\s*(?:руб|р|рублей)?", t)
    if m:
        n = _clean_num(m.group(1))
        if n >= 40000:
            return n, None

    return None, None


# ============================================================
# 4. КЛАСС МОДЕЛИ
# ============================================================

class VacancyModel:
    """
    Гибридная модель:
    - ML (TF-IDF + LogisticRegression + MultiOutputClassifier) по:
        * experience_level
        * work_format
        * company_field
        * skills
    - rule-based по:
        * job_role
        * salary
        * доуточнение work_format/experience
    """

    _pipeline: Pipeline | None = None
    _label_columns: List[str] | None = None

    _exp_labels: List[str] = []
    _fmt_labels: List[str] = []
    _field_labels: List[str] = []
    _skill_labels: List[str] = []

    @classmethod
    def _train_if_needed(cls):
        if cls._pipeline is not None:
            return

        df = pd.DataFrame(data)

        if "text" not in df:
            raise ValueError("В датасете нет поля 'text'")

        df["text"] = df["text"].astype(str)

        # ----- experience_level -----
        if "experience_level" in df:
            df["experience_level"] = df["experience_level"].fillna("").astype(str).str.strip()
            exp_y = pd.get_dummies(df["experience_level"], prefix="exp")
            cls._exp_labels = sorted(
                [c.split("exp_")[1] for c in exp_y.columns if c != "exp_"]
            )
        else:
            exp_y = pd.DataFrame(index=df.index)
            cls._exp_labels = []

        # ----- work_format -----
        if "work_format" in df:
            df["work_format"] = df["work_format"].fillna("").astype(str).str.strip()
            fmt_y = pd.get_dummies(df["work_format"], prefix="fmt")
            cls._fmt_labels = sorted(
                [c.split("fmt_")[1] for c in fmt_y.columns if c != "fmt_"]
            )
        else:
            fmt_y = pd.DataFrame(index=df.index)
            cls._fmt_labels = []

        # ----- company_field -----
        if "company_field" in df:
            df["company_field"] = df["company_field"].fillna("").astype(str).str.strip()
            field_y = pd.get_dummies(df["company_field"], prefix="fld")
            cls._field_labels = sorted(
                [c.split("fld_")[1] for c in field_y.columns if c != "fld_"]
            )
        else:
            field_y = pd.DataFrame(index=df.index)
            cls._field_labels = []

        # ----- skills (multi-label) -----
        if "skills" in df:
            df["skills"] = _normalize_list_field(df["skills"])
        else:
            df["skills"] = [[] for _ in range(len(df))]

        all_skills = sorted({s for row in df["skills"] for s in row})
        if all_skills:
            mlb = MultiLabelBinarizer(classes=all_skills)
            skill_y_raw = mlb.fit_transform(df["skills"])
            skill_y = pd.DataFrame(
                skill_y_raw, columns=[f"sk_{s}" for s in mlb.classes_], index=df.index
            )
            cls._skill_labels = list(mlb.classes_)
        else:
            skill_y = pd.DataFrame(index=df.index)
            cls._skill_labels = []

        # ----- итоговая матрица Y -----
        y = pd.concat([exp_y, fmt_y, field_y, skill_y], axis=1)

        # убираем колонки, где везде 0
        y = y.loc[:, y.sum(axis=0) > 0]

        cls._label_columns = list(y.columns)

        # ----- обучаем пайплайн -----
        cls._pipeline = Pipeline([
            ("vect", TfidfVectorizer(ngram_range=(1, 3), max_features=8000)),
            ("clf", MultiOutputClassifier(
                LogisticRegression(max_iter=5000, class_weight="balanced")
            ))
        ])

        cls._pipeline.fit(df["text"], y)

    @classmethod
    def predict(cls, text: str) -> Dict[str, Any]:
        cls._train_if_needed()

        assert cls._pipeline is not None
        assert cls._label_columns is not None

        # ---- ML-предсказание ----
        ml_pred = cls._pipeline.predict([text])[0]
        result_map = {col: int(ml_pred[i]) for i, col in enumerate(cls._label_columns)}

        # ---- опыт ----
        exp_found = []
        for col in cls._label_columns:
            if col.startswith("exp_") and result_map.get(col):
                exp_found.append(col.split("exp_")[1])
        exp_res = _heuristic_experience(text, exp_found)

        # ---- формат ----
        fmt_found = []
        for col in cls._label_columns:
            if col.startswith("fmt_") and result_map.get(col):
                fmt_found.append(col.split("fmt_")[1])
        fmt_res = _heuristic_work_format(text, fmt_found)

        # ---- сфера ----
        field_found = []
        for col in cls._label_columns:
            if col.startswith("fld_") and result_map.get(col):
                field_found.append(col.split("fld_")[1])
        field_res = field_found[0] if field_found else "it"

        # ---- skills (по ML) ----
        ml_skills = []
        for col in cls._label_columns:
            if col.startswith("sk_") and result_map.get(col):
                ml_skills.append(col.split("sk_")[1])

        # ---- skills (по синонимам) ----
        syn_skills = _extract_skills_by_synonyms(text)
        skills_res = sorted(set(ml_skills) | set(syn_skills))

        # ---- job_role: header + эвристика ----
        job_smart = _extract_job_role_smart(text)
        if job_smart:
            job_role_res = job_smart
        else:
            job_role_res = _heuristic_job_role(text)

        # ---- salary ----
        salary_min, salary_max = _extract_salary(text)

        return {
            "job_role": job_role_res,
            "experience_level": exp_res,
            "work_format": fmt_res,
            "company_field": field_res,
            "skills": skills_res,
            "salary_min": salary_min,
            "salary_max": salary_max,
        }


# ============================================================
# 5. ВНЕШНИЙ ИНТЕРФЕЙС (для бота)
# ============================================================

def extract_vacancy_info(text: str) -> Dict[str, Any]:
    """Основная функция: на вход текст вакансии, на выход структурированные поля."""
    return VacancyModel.predict(text)


def format_vacancy_result(v: Dict[str, Any]) -> str:
    """Форматируем результат для отправки в Telegram."""
    text = "📄 *Анализ вакансии*\n\n"

    text += f"💼 Должность: {v.get('job_role', 'не определена')}\n"
    text += f"📊 Уровень: {v.get('experience_level', 'не указан')}\n"
    text += f"🏢 Формат: {v.get('work_format', 'не указан')}\n"
    text += f"🏭 Сфера: {v.get('company_field', 'не указана')}\n"

    skills = v.get("skills") or []
    if skills:
        text += f"🛠 Навыки: {', '.join(skills)}\n"
    else:
        text += "🛠 Навыки: не найдены\n"

    smin = v.get("salary_min")
    smax = v.get("salary_max")
    if smin:
        if smax and smax != smin:
            text += f"💰 Зарплата: {smin}–{smax} руб.\n"
        else:
            text += f"💰 Зарплата: от {smin} руб.\n"
    else:
        text += "💰 Зарплата: не указана\n"

    return text

