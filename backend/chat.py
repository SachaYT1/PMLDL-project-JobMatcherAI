from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from model.main import  extract_resume_info
from .keyboards import menu

router = Router()
class Form(StatesGroup):
    waiting_for_message = State()



@router.message(F.text == "Отправить резюме")
async def ask_resume(message: Message, state: FSMContext):
    await state.set_state(Form.waiting_for_message)
    await message.answer("Пожалуйста, введите текст вашего резюме:")


@router.message(Form.waiting_for_message)
async def process_message(message: Message, state: FSMContext):
    text = message.text
    result = extract_resume_info(text)
    await message.answer(result, reply_markup=menu)
    await state.clear()

def register_handlers(dp):
    dp.include_router(router)