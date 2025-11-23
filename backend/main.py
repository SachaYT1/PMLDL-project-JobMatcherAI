import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

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
    
    await message.answer("Добро пожаловать")



async def main():
    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота")
    ])

    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
