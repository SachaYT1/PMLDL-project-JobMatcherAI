import asyncio
import logging

from aiogram import Bot, Dispatcher, types
from .config import settings
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from .chat import register_handlers as chat
from .chat import Form
from aiogram.fsm.context import FSMContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)





@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_for_message)
    await message.answer("Отправьте ваше резюме")


def register_handlers(dp: Dispatcher):
    chat(dp)


async def main():


    await bot.set_my_commands([
        BotCommand(command="start", description="Запуск бота")
    ])

    register_handlers(dp)

    logger.info("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
    