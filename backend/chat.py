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


@router.message(F.text == "Отправить резюме")
async def ask_resume(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_for_resume)
    await message.answer("Пожалуйста, вставьте текст вашего резюме сообщением:")


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


def register_handlers(dp):
    dp.include_router(router)