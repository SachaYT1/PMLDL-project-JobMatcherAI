import re
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.multioutput import MultiOutputClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from .data import data, quality_classes, skill_classes
import numpy as np

class ResumeExtractor:
    _model = None
    _vectorizer = None
    _skill_classes = skill_classes
    _quality_classes = quality_classes

    @classmethod
    def get_model(cls):
        if cls._model is None:
            # Расширенный синтетический датасет с добавлением новых примеров из веб-поиска
            

            # Подготовка DataFrame
            df = pd.DataFrame(data)

            # Создание бинарных меток для навыков и качеств (multi-label)
            skill_labels = pd.DataFrame(0, index=df.index, columns=cls._skill_classes)
            for i, skills in enumerate(df['skills']):
                for skill in skills:
                    if skill in cls._skill_classes:
                        skill_labels.at[i, skill] = 1

            quality_labels = pd.DataFrame(0, index=df.index, columns=cls._quality_classes)
            for i, qualities in enumerate(df['qualities']):
                for quality in qualities:
                    if quality in cls._quality_classes:
                        quality_labels.at[i, quality] = 1

            # Объединение меток в один массив
            y = pd.concat([skill_labels, quality_labels], axis=1)

            # Обработка all-0 columns
            active_mask = (y.sum(axis=0) > 0)
            cls._active_indices = np.where(active_mask)[0]
            y_active = y.loc[:, active_mask]

            # Обучение модели
            pipeline = Pipeline([
                ('vect', CountVectorizer(ngram_range=(1, 2), min_df=1)),
                ('clf', MultiOutputClassifier(LogisticRegression(max_iter=2000, class_weight='balanced')))
            ])
            cls._model = pipeline.fit(df['text'], y_active)

        return cls._model

def extract_resume_info(text):
    model = ResumeExtractor.get_model()

    # Предсказание навыков и качеств
    prediction_active = model.predict([text])[0]
    all_classes_len = len(ResumeExtractor._skill_classes) + len(ResumeExtractor._quality_classes)
    prediction = np.zeros(all_classes_len)
    prediction[ResumeExtractor._active_indices] = prediction_active

    num_skills = len(ResumeExtractor._skill_classes)
    predicted_skills = [ResumeExtractor._skill_classes[i] for i in range(num_skills) if prediction[i] == 1]
    predicted_qualities = [ResumeExtractor._quality_classes[i] for i in range(len(ResumeExtractor._quality_classes)) if prediction[i + num_skills] == 1]

    # Извлечение базовых полей с помощью regex (расширенные паттерны для лучшего обобщения)
    result = {
        "name": re.search(r'(?:Я —|Меня зовут|Имя:|Зовут меня|ФИО:)\s*([А-ЯЁ][а-яё]+ [А-ЯЁ][а-яё]+(?: [А-ЯЁ][а-яё]+)?)', text, re.IGNORECASE) or "",
        "age": re.search(r'(\d{1,2})\s*(лет|год|года|годов|возраст)', text, re.IGNORECASE) or "",
        "city": re.search(r'(?:живу в|город|проживаю в|Место проживания:)\s*([А-ЯЁ][а-яё]+)', text, re.IGNORECASE) or "",
        "education": re.search(r'(?:Образование:|Высшее образование в|Учебное заведение:|Факультет:|Специальность:|Год окончания:|Курсы:|ПГНИУ|МГУ|СПбГУ|УрФУ|НГУ|КФУ|ДВФУ|ЮФУ|ЧелГУ|ОмГУ|МГТУ им. Баумана|РТУ МИРЭА|Омский государственный университет)\s*([А-ЯЁa-z0-9, .]+)', text, re.IGNORECASE) or "Не указано",
        "skills": predicted_skills,
        "qualities": predicted_qualities
    }

    # Обработка матчей regex
    name = result["name"].group(1) if result["name"] else "Не указано"
    age = result["age"].group(1) if result["age"] else "Не указано"
    city = result["city"].group(1) if result["city"] else "Не указано"
    education_match = result["education"]
    education = education_match.group(2) if isinstance(education_match, re.Match) and education_match.group(2) else education_match if education_match != "" else "Не указано"

    # Форматирование результата
    formatted_result = (
        f"Имя: {name}\n"
        f"Возраст: {age}\n"
        f"Город проживания: {city}\n"
        f"Образование: {education}\n"
        f"Профессиональные навыки: {', '.join(predicted_skills) or 'Не указано'}\n"
        f"Личные качества: {', '.join(predicted_qualities) or 'Не указано'}"
    )

    return formatted_result