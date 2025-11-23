from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
import json
import os

router = Router()

class ResumeForm(StatesGroup):
    waiting_for_full_name = State()
    waiting_for_age = State()
    waiting_for_location = State()
    waiting_for_education = State()
    waiting_for_specialization = State()
    waiting_for_experience = State()
    waiting_for_skills = State()
    waiting_for_interests = State()
    waiting_for_salary = State()
    waiting_for_work_format = State()
    waiting_for_career_goals = State()

# Главное меню
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Отправить резюме", callback_data="create_resume")],
        [InlineKeyboardButton(text="🔍 Найти вакансии", callback_data="find_vacancies")],
        [InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")]
    ])

# Клавиатуры для выбора
def get_education_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Среднее", callback_data="education_Среднее")],
        [InlineKeyboardButton(text="Бакалавр", callback_data="education_Бакалавр")],
        [InlineKeyboardButton(text="Магистр", callback_data="education_Магистр")],
        [InlineKeyboardButton(text="Кандидат наук", callback_data="education_Кандидат наук")],
        [InlineKeyboardButton(text="Доктор наук", callback_data="education_Доктор наук")]
    ])

def get_work_format_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Офис", callback_data="format_офис")],
        [InlineKeyboardButton(text="Удалёнка", callback_data="format_удалёнка")],
        [InlineKeyboardButton(text="Гибрид", callback_data="format_гибрид")]
    ])

def get_experience_level_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Junior (0-2 года)", callback_data="level_Junior")],
        [InlineKeyboardButton(text="Middle (2-5 лет)", callback_data="level_Middle")],
        [InlineKeyboardButton(text="Senior (5+ лет)", callback_data="level_Senior")],
        [InlineKeyboardButton(text="Lead", callback_data="level_Lead")]
    ])

# Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "👋 Добро пожаловать в JobMatcher!\n\n"
        "Я помогу вам найти подходящие вакансии на основе вашего резюме.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )

# Обработчик текста "старт"
@router.message(F.text.lower() == "старт")
async def text_start(message: Message):
    await cmd_start(message)

# Обработчик кнопки "Отправить резюме" из меню
@router.callback_query(F.data == "create_resume")
async def process_create_resume(callback: CallbackQuery, state: FSMContext):
    await start_resume_form(callback.message, state)

# Начало заполнения резюме
@router.message(F.text == "Отправить резюме")
async def start_resume_form(message: Message, state: FSMContext):
    await state.set_state(ResumeForm.waiting_for_full_name)
    await message.answer("Давайте заполним ваше резюме! Это займет несколько минут.\n\nКак вас зовут? (ФИО)")

@router.message(ResumeForm.waiting_for_full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(ResumeForm.waiting_for_age)
    await message.answer("Сколько вам лет?")

@router.message(ResumeForm.waiting_for_age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        if age < 14 or age > 80:
            await message.answer("Пожалуйста, введите реальный возраст (14-80 лет):")
            return
        await state.update_data(age=age)
        await state.set_state(ResumeForm.waiting_for_location)
        await message.answer("В каком городе вы находитесь?")
    except ValueError:
        await message.answer("Пожалуйста, введите возраст числом:")

@router.message(ResumeForm.waiting_for_location)
async def process_location(message: Message, state: FSMContext):
    await state.update_data(location=message.text)
    await state.set_state(ResumeForm.waiting_for_education)
    await message.answer("Какое у вас образование?", reply_markup=get_education_keyboard())

@router.callback_query(F.data.startswith("education_"), ResumeForm.waiting_for_education)
async def process_education(callback: CallbackQuery, state: FSMContext):
    education = callback.data.replace("education_", "")
    await state.update_data(education=education)
    await state.set_state(ResumeForm.waiting_for_specialization)
    await callback.message.edit_text(f"Образование: {education}")
    await callback.message.answer("Какая у вас специализация/профессия?\n(например: Компьютерные науки, Маркетинг, Медицина)")

@router.message(ResumeForm.waiting_for_specialization)
async def process_specialization(message: Message, state: FSMContext):
    await state.update_data(specialization=message.text)
    await state.set_state(ResumeForm.waiting_for_experience)
    await message.answer("Какой у вас уровень опыта?", reply_markup=get_experience_level_keyboard())

@router.callback_query(F.data.startswith("level_"), ResumeForm.waiting_for_experience)
async def process_experience_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.replace("level_", "")
    await state.update_data(experience_level=level)
    await callback.message.edit_text(f"Уровень опыта: {level}")
    
    # Спросим общий стаж
    await state.set_state(ResumeForm.waiting_for_skills)
    await callback.message.answer("Перечислите ваши ключевые навыки через запятую:\n(например: Python, SQL, Анализ данных, Маркетинг)")

@router.message(ResumeForm.waiting_for_skills)
async def process_skills(message: Message, state: FSMContext):
    skills = [skill.strip() for skill in message.text.split(",")]
    await state.update_data(skills=skills)
    await state.set_state(ResumeForm.waiting_for_interests)
    await message.answer("Какие профессиональные сферы вам интересны? (через запятую)\n(например: IT, Маркетинг, Дизайн, Финансы)")

@router.message(ResumeForm.waiting_for_interests)
async def process_interests(message: Message, state: FSMContext):
    interests = [interest.strip() for interest in message.text.split(",")]
    await state.update_data(interests=interests)
    await state.set_state(ResumeForm.waiting_for_salary)
    await message.answer("Какие у вас зарплатные ожидания? (в рублях)\n(например: 80000)")

@router.message(ResumeForm.waiting_for_salary)
async def process_salary(message: Message, state: FSMContext):
    try:
        salary = int(message.text)
        await state.update_data(salary_expectations=salary)
        await state.set_state(ResumeForm.waiting_for_work_format)
        await message.answer("Какой формат работы предпочитаете?", reply_markup=get_work_format_keyboard())
    except ValueError:
        await message.answer("Пожалуйста, введите зарплату числом:")

@router.callback_query(F.data.startswith("format_"), ResumeForm.waiting_for_work_format)
async def process_work_format(callback: CallbackQuery, state: FSMContext):
    work_format = callback.data.replace("format_", "")
    await state.update_data(work_format=work_format)
    await state.set_state(ResumeForm.waiting_for_career_goals)
    await callback.message.edit_text(f"Формат работы: {work_format}")
    await callback.message.answer("Какие у вас карьерные цели? (через запятую)\n(например: профессиональный рост, управление командой, международный опыт)")

@router.message(ResumeForm.waiting_for_career_goals)
async def process_career_goals(message: Message, state: FSMContext):
    career_goals = [goal.strip() for goal in message.text.split(",")]
    
    # Получаем все данные
    data = await state.get_data()
    
    # Формируем структурированное резюме
    resume_data = {
        "candidate_id": str(message.from_user.id),
        "personal_info": {
            "name": data.get("full_name"),
            "age": data.get("age"),
            "location": data.get("location")
        },
        "education": {
            "degree": data.get("education"),
            "specialization": data.get("specialization")
        },
        "experience": {
            "level": data.get("experience_level"),
            "total_years": estimate_experience_years(data.get("experience_level"))
        },
        "hard_skills": data.get("skills", []),
        "interests": data.get("interests", []),
        "work_preferences": {
            "work_format": data.get("work_format")
        },
        "salary_expectations": {
            "desired": data.get("salary_expectations")
        },
        "career_goals": career_goals
    }
    
    # Сохраняем резюме (здесь можно добавить сохранение в БД)
    await save_resume(resume_data)
    
    # Формируем красивый ответ
    resume_text = format_resume_text(resume_data)
    
    await message.answer("✅ Ваше резюме успешно сохранено!\n\n" + resume_text, reply_markup=get_main_menu())
    await state.clear()

# Обработчик кнопки "Найти вакансии"
@router.callback_query(F.data == "find_vacancies")
async def process_find_vacancies(callback: CallbackQuery):
    await callback.message.answer("🔍 Функция поиска вакансий скоро будет доступна!")

# Обработчик кнопки "Помощь"
@router.callback_query(F.data == "help")
async def process_help(callback: CallbackQuery):
    await callback.message.answer(
        "ℹ️ Помощь по боту:\n\n"
        "• 📝 Отправить резюме - заполнить информацию о себе\n"
        "• 🔍 Найти вакансии - подбор подходящих вакансий\n\n"
        "Просто нажмите на нужную кнопку в меню!"
    )

# Обработчик любых текстовых сообщений (fallback)
@router.message(F.text)
async def handle_other_messages(message: Message):
    await message.answer(
        "Я не понял ваше сообщение 😊\n\n"
        "Используйте кнопки меню или команду /start",
        reply_markup=get_main_menu()
    )

def estimate_experience_years(level):
    """Оцениваем стаж по уровню"""
    experience_map = {
        "Junior": 1,
        "Middle": 3,
        "Senior": 6,
        "Lead": 8
    }
    return experience_map.get(level, 1)

async def save_resume(resume_data):
    """Функция для сохранения резюме (можно подключить БД)"""
    # TODO: Реализовать сохранение в базу данных
    print("Сохранено резюме:", resume_data)
    
    # Создаем папку data если её нет
    os.makedirs("data", exist_ok=True)
    
    # Сохраняем в файл
    with open("data/resumes.json", "a", encoding="utf-8") as f:
        json.dump(resume_data, f, ensure_ascii=False)
        f.write("\n")

def format_resume_text(resume_data):
    """Форматируем резюме в красивый текст"""
    personal = resume_data["personal_info"]
    education = resume_data["education"]
    experience = resume_data["experience"]
    
    text = f"👤 {personal['name']}\n"
    text += f"🎂 Возраст: {personal['age']}\n"
    text += f"📍 Локация: {personal['location']}\n"
    text += f"🎓 Образование: {education['degree']} ({education['specialization']})\n"
    text += f"💼 Опыт: {experience['level']} (~{experience['total_years']} лет)\n"
    text += f"🛠 Навыки: {', '.join(resume_data['hard_skills'])}\n"
    text += f"🎯 Интересы: {', '.join(resume_data['interests'])}\n"
    text += f"💼 Формат работы: {resume_data['work_preferences']['work_format']}\n"
    text += f"💰 Зарплатные ожидания: {resume_data['salary_expectations']['desired']} руб.\n"
    text += f"🚀 Цели: {', '.join(resume_data['career_goals'])}"
    
    return text

def register_handlers(dp):
    dp.include_router(router)