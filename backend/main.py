import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM для резюме
class ResumeStates(StatesGroup):
    waiting_for_resume = State()

# Постоянная кнопка "Отправить резюме"
keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Отправить резюме")]],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    # Приветственное сообщение отправляется один раз
    await message.answer(
        "Добро пожаловать! Используйте кнопку 'Отправить резюме', чтобы отправить текст резюме.",
        reply_markup=keyboard  # Клавиатура остаётся
    )

# Нажатие кнопки "Отправить резюме"
@dp.message(lambda message: message.text == "Отправить резюме")
async def start_resume(message: Message, state: FSMContext):
    await message.answer("Отправьте ваше резюме в виде текста.")
    await state.set_state(ResumeStates.waiting_for_resume)

# Получение текста резюме
@dp.message(ResumeStates.waiting_for_resume)
async def receive_resume(message: Message, state: FSMContext):
    # Здесь можно добавить обработку резюме
    await message.answer("Ваше резюме в обработке.")
    await state.clear()  # Сбрасываем состояние

# Любые другие сообщения
@dp.message()
async def other_messages(message: Message):
    await message.answer("Спасибо за сообщение.", reply_markup=keyboard)  # Кнопка остаётся

async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота")
    ])
    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
