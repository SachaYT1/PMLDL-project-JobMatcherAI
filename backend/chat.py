from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from model.main import ResumeProfile, extract_resume_info
from model.matcher import JobMatcher
from model.preferences import PreferenceVector
from model.job_repository import JobRepository
from .keyboards import job_feedback_keyboard, main_menu
from .storage import UserStorage

router = Router()
storage = UserStorage()
job_repository = JobRepository()
matcher = JobMatcher(job_repository)


class Form(StatesGroup):
    waiting_for_resume = State()

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


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    profile = storage.get_profile(message.from_user.id)
    if profile:
        await message.answer(
            "У нас уже есть ваше резюме. Используйте меню, чтобы обновить резюме или получить рекомендации.",
            reply_markup=main_menu,
        )
    else:
        await state.set_state(Form.waiting_for_resume)
        await message.answer(
            "Привет! Отправьте текст вашего резюме в свободной форме. Мы извлечем навыки, зарплатные ожидания и подготовим подборку вакансий.",
            reply_markup=main_menu,
        )


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
async def ask_resume(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_for_resume)
    await message.answer("Пожалуйста, вставьте текст вашего резюме сообщением:")


@router.callback_query(F.data.startswith("level_"), ResumeForm.waiting_for_experience)
async def process_experience_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.replace("level_", "")
    await state.update_data(experience_level=level)
    await callback.message.edit_text(f"Уровень опыта: {level}")
    
    # Спросим общий стаж
    await state.set_state(ResumeForm.waiting_for_skills)
    await callback.message.answer("Перечислите ваши ключевые навыки через запятую:\n(например: Python, SQL, Анализ данных, Маркетинг)")


@router.message(Form.waiting_for_resume)
async def process_resume(message: Message, state: FSMContext):
    profile = extract_resume_info(message.text)
    storage.save_profile(message.from_user.id, profile)
    await state.clear()
    await message.answer(
        "Резюме сохранено ✅\n\n" + profile.to_message(),
        reply_markup=main_menu,
    )


@router.message(F.text == "Получить рекомендации")
@router.message(Command("recommend"))
async def recommend(message: Message):
    await send_recommendations(message)


async def send_recommendations(message: Message):
    user_id = message.from_user.id
    profile = storage.get_profile(user_id)
    if not profile:
        await message.answer("Сначала отправьте резюме, чтобы мы узнали ваши навыки.", reply_markup=main_menu)
        return

    preferences = storage.get_preferences(user_id)
    matches = matcher.recommend(profile, preferences, limit=10)

    if not matches:
        await message.answer("Пока нет вакансий, удовлетворяющих фильтрам. Попробуйте позже.")
        return

    await message.answer("Вот топ-10 вакансий, подходящих под ваше резюме и предпочтения:")
    for vacancy, score in matches:
        formatted_score = f"\n⚖️ Рейтинг соответствия: {score:.2f}"
        await message.answer(
            vacancy.to_message() + formatted_score,
            reply_markup=job_feedback_keyboard(vacancy.id),
        )


@router.message(F.text == "Избранное")
@router.message(Command("favorites"))
async def favorites(message: Message):
    user_id = message.from_user.id
    preferences = storage.get_preferences(user_id)
    favorites_ids = list(preferences.favorite_vacancies)
    if not favorites_ids:
        await message.answer("У вас пока нет избранных вакансий.", reply_markup=main_menu)
        return
    for vacancy_id in favorites_ids:
        vacancy = job_repository.get(vacancy_id)
        if vacancy:
            await message.answer(vacancy.to_message())


@router.callback_query(F.data.startswith("jm_"))
async def feedback_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    action, vacancy_id = callback.data.split(":")
    vacancy = job_repository.get(vacancy_id)
    if not vacancy:
        await callback.answer("Вакансия не найдена", show_alert=True)
        return

    preferences = storage.get_preferences(user_id)
    if action == "jm_like":
        preferences.update_from_vacancy(vacancy, "like")
        response = "Отмечено как понравившееся."
    elif action == "jm_dislike":
        preferences.update_from_vacancy(vacancy, "dislike")
        response = "Больше не будем показывать похожие вакансии."
    elif action == "jm_favorite":
        if vacancy_id in preferences.favorite_vacancies:
            preferences.remove_favorite(vacancy_id)
            response = "Удалено из избранного."
        else:
            preferences.update_from_vacancy(vacancy, "favorite")
            response = "Добавлено в избранное."
    else:
        response = "Неизвестное действие"

    storage.save_preferences(user_id, preferences)
    await callback.answer(response, show_alert=False)


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