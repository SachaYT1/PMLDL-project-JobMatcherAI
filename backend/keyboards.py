from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


menu = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Отправить резюме")],
], resize_keyboard=True)