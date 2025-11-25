import json
from typing import Dict, List, Tuple


# ------------------------------------------
# Алгоритм сопоставления кандидат-вакансия
# ------------------------------------------

def calculate_skills_match(candidate_skills: List[str], required_skills: List[str], preferred_skills: List[str]) -> \
Tuple[float, List[str], List[str]]:
    """Сравнение навыков кандидата и требований вакансии"""
    positives = []
    negatives = []

    # Обязательные навыки
    required_match = set(candidate_skills) & set(required_skills)
    required_match_rate = len(required_match) / len(required_skills) if required_skills else 1.0

    if required_match:
        positives.append(f"Совпадают обязательные навыки: {', '.join(required_match)}")

    missing_required = set(required_skills) - set(candidate_skills)
    if missing_required:
        negatives.append(f"Отсутствуют обязательные навыки: {', '.join(missing_required)}")

    # Предпочтительные навыки
    preferred_match = set(candidate_skills) & set(preferred_skills)
    preferred_match_rate = len(preferred_match) / len(preferred_skills) if preferred_skills else 1.0

    if preferred_match:
        positives.append(f"Совпадают желательные навыки: {', '.join(preferred_match)}")

    # Общий score (70% обязательные, 30% предпочтительные)
    skills_score = (required_match_rate * 0.7 + preferred_match_rate * 0.3) * 100

    return round(skills_score, 2), positives, negatives


def calculate_experience_match(candidate_exp: Dict, vacancy_requirements: Dict) -> Tuple[float, List[str], List[str]]:
    """Сравнение опыта кандидата и требований вакансии"""
    positives = []
    negatives = []
    score = 0

    candidate_years = candidate_exp.get("total_years", 0)
    required_years = vacancy_requirements.get("experience_years", 0)

    # Сравнение стажа
    if candidate_years >= required_years:
        exp_match = min(100, (candidate_years / max(required_years, 1)) * 100)
        score += exp_match * 0.6
        positives.append(f"Опыт работы: {candidate_years} лет (требуется: {required_years})")
    else:
        exp_match = max(0, (candidate_years / required_years) * 100)
        score += exp_match * 0.6
        negatives.append(f"Недостаточный опыт: {candidate_years} лет (требуется: {required_years})")

    # Сравнение уровня
    levels = {"Junior": 1, "Middle": 2, "Senior": 3, "Lead": 4}
    candidate_level = levels.get(candidate_exp.get("level", ""), 0)
    required_level = levels.get(vacancy_requirements.get("level", ""), 0)

    if candidate_level >= required_level:
        score += 40
        positives.append(f"Уровень подходит: {candidate_exp.get('level')}")
    else:
        level_match = max(0, (candidate_level / max(required_level, 1)) * 40)
        score += level_match
        negatives.append(
            f"Уровень ниже требуемого: {candidate_exp.get('level')} vs {vacancy_requirements.get('level')}")

    return round(score, 2), positives, negatives


def calculate_education_match(candidate_edu: Dict, vacancy_requirements: Dict) -> Tuple[float, List[str], List[str]]:
    """Сравнение образования"""
    positives = []
    negatives = []
    score = 0

    # Уровень образования
    degree_levels = {"Среднее": 1, "Бакалавр": 2, "Магистр": 3, "Кандидат наук": 4, "Доктор наук": 5}
    candidate_degree = degree_levels.get(candidate_edu.get("degree", ""), 0)
    required_degree = degree_levels.get(vacancy_requirements.get("education_level", ""), 0)

    if candidate_degree >= required_degree:
        score += 60
        positives.append(f"Уровень образования подходит: {candidate_edu.get('degree')}")
    else:
        degree_match = max(0, (candidate_degree / max(required_degree, 1)) * 60)
        score += degree_match
        negatives.append(f"Уровень образования ниже требуемого")

    # Специализация
    candidate_spec = candidate_edu.get("specialization", "")
    required_specs = vacancy_requirements.get("specializations", [])

    if required_specs and candidate_spec in required_specs:
        score += 40
        positives.append(f"Специализация подходит: {candidate_spec}")
    elif required_specs:
        negatives.append(f"Специализация не совпадает с требуемыми: {', '.join(required_specs)}")
    else:
        score += 40  # Если специализация не указана как требование

    return round(score, 2), positives, negatives


def calculate_work_conditions_match(candidate_prefs: Dict, vacancy_conditions: Dict) -> Tuple[
    float, List[str], List[str]]:
    """Сравнение условий работы"""
    positives = []
    negatives = []
    matches = 0
    total = 0

    # Формат работы
    work_format_match = candidate_prefs.get("work_format") == vacancy_conditions.get("work_format")
    total += 1
    if work_format_match:
        matches += 1
        positives.append(f"Формат работы: {vacancy_conditions.get('work_format')}")
    else:
        negatives.append(
            f"Формат работы не совпадает: предпочитается {candidate_prefs.get('work_format')}, предлагается {vacancy_conditions.get('work_format')}")

    # График работы
    schedule_match = candidate_prefs.get("schedule") == vacancy_conditions.get("schedule")
    total += 1
    if schedule_match:
        matches += 1
        positives.append(f"График работы: {vacancy_conditions.get('schedule')}")

    # Размер команды
    team_size_match = candidate_prefs.get("team_size") == vacancy_conditions.get("team_size")
    total += 1
    if team_size_match:
        matches += 1
        positives.append(f"Размер команды: {vacancy_conditions.get('team_size')}")

    # Стиль управления
    management_match = candidate_prefs.get("management_style") == vacancy_conditions.get("management_style")
    total += 1
    if management_match:
        matches += 1
        positives.append(f"Стиль управления: {vacancy_conditions.get('management_style')}")

    score = (matches / total) * 100 if total > 0 else 100
    return round(score, 2), positives, negatives


def calculate_salary_match(candidate_salary: Dict, vacancy_salary: Dict) -> Tuple[float, List[str], List[str]]:
    """Сравнение зарплатных ожиданий"""
    positives = []
    negatives = []

    candidate_desired = candidate_salary.get("desired", 0)
    candidate_min = candidate_salary.get("min", 0)
    vacancy_min = vacancy_salary.get("min", 0)
    vacancy_max = vacancy_salary.get("max", 0)

    if candidate_min <= vacancy_max and candidate_desired <= vacancy_max:
        if candidate_desired >= vacancy_min:
            score = 100
            positives.append(
                f"Зарплатные ожидания в пределах вилки: {candidate_desired} (вилка: {vacancy_min}-{vacancy_max})")
        else:
            score = 80
            positives.append(
                f"Зарплатные ожидания ниже вилки: {candidate_desired} (вилка: {vacancy_min}-{vacancy_max})")
    elif candidate_min <= vacancy_max:
        score = 60
        negatives.append(f"Желаемая зарплата выше вилки: {candidate_desired} (вилка: {vacancy_min}-{vacancy_max})")
    else:
        score = max(0, (vacancy_max / candidate_min) * 100)
        negatives.append(
            f"Минимальные ожидания выше максимальной вилки: {candidate_min} (вилка: {vacancy_min}-{vacancy_max})")

    return round(score, 2), positives, negatives


def calculate_culture_match(candidate: Dict, vacancy: Dict) -> Tuple[float, List[str], List[str]]:
    """Сравнение ценностей и культуры"""
    positives = []
    negatives = []

    # Ценности
    candidate_values = set(candidate.get("values", []))
    company_values = set(vacancy.get("company_culture", {}).get("values", []))
    values_match = len(candidate_values & company_values) / len(company_values) if company_values else 1.0

    if values_match > 0:
        common_values = candidate_values & company_values
        if common_values:
            positives.append(f"Совпадают ценности: {', '.join(common_values)}")

    # Интересы
    candidate_interests = set(candidate.get("interests", []))
    company_interests = set(vacancy.get("company_culture", {}).get("interests", []))
    interests_match = len(candidate_interests & company_interests) / len(
        company_interests) if company_interests else 1.0

    if interests_match > 0:
        common_interests = candidate_interests & company_interests
        if common_interests:
            positives.append(f"Совпадают интересы: {', '.join(common_interests)}")

    # Карьерные цели
    candidate_goals = set(candidate.get("career_goals", []))
    company_opportunities = set(vacancy.get("company_culture", {}).get("career_opportunities", []))
    goals_match = len(candidate_goals & company_opportunities) / len(candidate_goals) if candidate_goals else 1.0

    if goals_match > 0:
        common_goals = candidate_goals & company_opportunities
        if common_goals:
            positives.append(f"Есть возможности для карьерного роста: {', '.join(common_goals)}")

    # Общий score (40% ценности, 30% интересы, 30% карьера)
    culture_score = (values_match * 40 + interests_match * 30 + goals_match * 30)

    return round(culture_score, 2), positives, negatives


def calculate_location_match(candidate: Dict, vacancy: Dict) -> Tuple[float, List[str], List[str]]:
    """Сравнение локации"""
    positives = []
    negatives = []

    candidate_location = candidate.get("personal_info", {}).get("location", "")
    vacancy_location = vacancy.get("location", "")
    relocation_ready = candidate.get("personal_info", {}).get("relocation_ready", False)
    remote_possible = vacancy.get("remote_possible", False)

    if candidate_location.lower() == vacancy_location.lower():
        score = 100
        positives.append(f"Локация совпадает: {vacancy_location}")
    elif remote_possible:
        score = 90
        positives.append(f"Возможна удалённая работа из {candidate_location}")
    elif relocation_ready:
        score = 70
        positives.append(f"Готов к переезду в {vacancy_location}")
    else:
        score = 0
        negatives.append(f"Локация не совпадает: кандидат в {candidate_location}, вакансия в {vacancy_location}")

    return round(score, 2), positives, negatives


# ------------------------------------------
# Основная функция сопоставления
# ------------------------------------------

def match_candidate_vacancy(candidate: Dict, vacancy: Dict) -> Dict:
    """Основная функция сопоставления кандидата и вакансии"""

    all_positives = []
    all_negatives = []
    total_score = 0

    # 1. Навыки (30%)
    skills_score, skills_pos, skills_neg = calculate_skills_match(
        candidate.get("hard_skills", []) + candidate.get("education", {}).get("skills", []),
        vacancy.get("requirements", {}).get("required_skills", []),
        vacancy.get("requirements", {}).get("preferred_skills", [])
    )
    total_score += skills_score * 0.30
    all_positives.extend(skills_pos)
    all_negatives.extend(skills_neg)

    # 2. Опыт (20%)
    exp_score, exp_pos, exp_neg = calculate_experience_match(
        candidate.get("experience", {}),
        vacancy.get("requirements", {})
    )
    total_score += exp_score * 0.20
    all_positives.extend(exp_pos)
    all_negatives.extend(exp_neg)

    # 3. Локация/формат (15%)
    location_score, location_pos, location_neg = calculate_location_match(candidate, vacancy)
    total_score += location_score * 0.15
    all_positives.extend(location_pos)
    all_negatives.extend(location_neg)

    # 4. Образование (10%)
    edu_score, edu_pos, edu_neg = calculate_education_match(
        candidate.get("education", {}),
        vacancy.get("requirements", {})
    )
    total_score += edu_score * 0.10
    all_positives.extend(edu_pos)
    all_negatives.extend(edu_neg)

    # 5. Условия работы (10%)
    conditions_score, conditions_pos, conditions_neg = calculate_work_conditions_match(
        candidate.get("work_preferences", {}),
        vacancy.get("work_conditions", {})
    )
    total_score += conditions_score * 0.10
    all_positives.extend(conditions_pos)
    all_negatives.extend(conditions_neg)

    # 6. Зарплата (10%)
    salary_score, salary_pos, salary_neg = calculate_salary_match(
        candidate.get("salary_expectations", {}),
        vacancy.get("salary_range", {})
    )
    total_score += salary_score * 0.10
    all_positives.extend(salary_pos)
    all_negatives.extend(salary_neg)

    # 7. Культура/ценности (5%)
    culture_score, culture_pos, culture_neg = calculate_culture_match(candidate, vacancy)
    total_score += culture_score * 0.05
    all_positives.extend(culture_pos)
    all_negatives.extend(culture_neg)

    # Итоговый результат
    final_score = round(total_score, 2)

    # Определение уровня совместимости
    if final_score >= 85:
        compatibility_level = "Высокая совместимость"
    elif final_score >= 70:
        compatibility_level = "Средняя совместимость"
    elif final_score >= 50:
        compatibility_level = "Низкая совместимость"
    else:
        compatibility_level = "Несовместимы"

    return {
        "vacancy_id": vacancy.get("vacancy_id"),
        "job_title": vacancy.get("job_title"),
        "company": vacancy.get("company"),
        "match_score": final_score,
        "compatibility_level": compatibility_level,
        "detailed_scores": {
            "skills": skills_score,
            "experience": exp_score,
            "location": location_score,
            "education": edu_score,
            "work_conditions": conditions_score,
            "salary": salary_score,
            "culture": culture_score
        },
        "positives": all_positives,
        "negatives": all_negatives
    }


# ------------------------------------------
# Массовое сопоставление
# ------------------------------------------

def find_best_vacancies_for_candidate(candidate: Dict, vacancies: List[Dict], top_n: int = 10) -> List[Dict]:
    """Найти лучшие вакансии для кандидата"""
    matches = []

    for vacancy in vacancies:
        match_result = match_candidate_vacancy(candidate, vacancy)
        matches.append(match_result)

    # Сортировка по убыванию релевантности
    matches.sort(key=lambda x: x["match_score"], reverse=True)

    return matches[:top_n]


def find_best_candidates_for_vacancy(vacancy: Dict, candidates: List[Dict], top_n: int = 10) -> List[Dict]:
    """Найти лучших кандидатов для вакансии"""
    matches = []

    for candidate in candidates:
        match_result = match_candidate_vacancy(candidate, vacancy)
        # Добавляем информацию о кандидате в результат
        match_result["candidate_info"] = {
            "candidate_id": candidate.get("candidate_id"),
            "name": candidate.get("personal_info", {}).get("name"),
            "experience": candidate.get("experience", {}).get("total_years", 0),
            "level": candidate.get("experience", {}).get("level", "")
        }
        matches.append(match_result)

    # Сортировка по убыванию релевантности
    matches.sort(key=lambda x: x["match_score"], reverse=True)

    return matches[:top_n]


# ------------------------------------------
# Тестовый пример
# ------------------------------------------

if __name__ == "__main__":
    # Пример кандидата
    candidate_example = {
        "candidate_id": "12345",
        "personal_info": {
            "name": "Иван Иванов",
            "age": 25,
            "location": "Москва",
            "relocation_ready": True
        },
        "education": {
            "degree": "Бакалавр",
            "specialization": "Компьютерные науки",
            "graduation_year": 2020,
            "skills": ["Python", "SQL", "Машинное обучение", "Анализ данных"]
        },
        "experience": {
            "total_years": 3,
            "level": "Middle",
            "previous_roles": ["Data Analyst", "Junior Data Scientist"]
        },
        "hard_skills": ["Python", "SQL", "Pandas", "Scikit-learn", "Tableau"],
        "soft_skills": ["аналитическое мышление", "коммуникация", "работа в команде"],
        "interests": ["аналитика", "исследования", "программирование", "математика"],
        "values": ["развитие", "стабильность", "инновации", "автономия"],
        "work_preferences": {
            "work_format": "гибрид",
            "schedule": "полный день",
            "team_size": "средняя",
            "management_style": "демократичный"
        },
        "salary_expectations": {
            "min": 80000,
            "desired": 100000
        },
        "career_goals": ["профессиональный рост", "управление командой", "международный опыт"]
    }

    # Пример вакансии
    vacancy_example = {
        "vacancy_id": "V001",
        "job_title": "Data Scientist",
        "company": "TechCorp",
        "location": "Москва",
        "remote_possible": True,

        "requirements": {
            "education_level": "Бакалавр",
            "specializations": ["Компьютерные науки", "Математика", "Статистика"],
            "experience_years": 2,
            "level": "Middle",
            "required_skills": ["Python", "SQL", "Машинное обучение", "Статистика"],
            "preferred_skills": ["Deep Learning", "Big Data", "Docker"]
        },

        "work_conditions": {
            "work_format": "гибрид",
            "schedule": "полный день",
            "team_size": "средняя",
            "management_style": "демократичный"
        },

        "salary_range": {
            "min": 70000,
            "max": 120000
        },

        "company_culture": {
            "values": ["инновации", "развитие", "коллаборация"],
            "interests": ["аналитика", "технологии", "исследования"],
            "career_opportunities": ["профессиональный рост", "обучение", "менеджмент"]
        }
    }

    # Тестирование
    result = match_candidate_vacancy(candidate_example, vacancy_example)
    print("Результат сопоставления:")
    print(json.dumps(result, ensure_ascii=False, indent=2))