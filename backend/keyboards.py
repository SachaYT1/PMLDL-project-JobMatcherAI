from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Отправить резюме")],
        [KeyboardButton(text="Получить рекомендации")],
        [KeyboardButton(text="Избранное")],
    ],
    resize_keyboard=True,
)


def job_feedback_keyboard(vacancy_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👍 Подходит", callback_data=f"jm_like:{vacancy_id}"
                ),
                InlineKeyboardButton(
                    text="👎 Не подходит", callback_data=f"jm_dislike:{vacancy_id}"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⭐ В избранное", callback_data=f"jm_favorite:{vacancy_id}"
                ),
            ],
        ]
    )