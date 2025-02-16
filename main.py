import logging
from config import BOT_COMMANDS, BOT_TOKEN
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Логування
logging.basicConfig(level=logging.INFO)

# Ініціалізація бота і диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# Визначення станів
class EncodeDecodeStates(StatesGroup):
    choosing_mode = State()
    choosing_emoji = State()
    encoding_text = State()


# Емодзі для кодування
EMOJIS = [
    "😀", "😂", "🥰", "😎", "🤔", "👍", "👎", "👏", "😅", "🤝",
    "🎉", "🎂", "🍕", "🌈", "🌞", "🌙", "🔥", "💯", "🚀", "👀", "💀", "🥹"
]

VARIATION_SELECTOR_START = 0xFE00
VARIATION_SELECTOR_END = 0xFE0F
VARIATION_SELECTOR_SUPPLEMENT_START = 0xE0100
VARIATION_SELECTOR_SUPPLEMENT_END = 0xE01EF


# Функції для кодування та декодування
def to_variation_selector(byte: int) -> str | None:
    if 0 <= byte < 16:
        return chr(VARIATION_SELECTOR_START + byte)
    elif 16 <= byte < 256:
        return chr(VARIATION_SELECTOR_SUPPLEMENT_START + byte - 16)
    return None


def from_variation_selector(code_point: int) -> int | None:
    if VARIATION_SELECTOR_START <= code_point <= VARIATION_SELECTOR_END:
        return code_point - VARIATION_SELECTOR_START
    elif VARIATION_SELECTOR_SUPPLEMENT_START <= code_point <= VARIATION_SELECTOR_SUPPLEMENT_END:
        return code_point - VARIATION_SELECTOR_SUPPLEMENT_START + 16
    return None


def encode(emoji: str, text: str) -> str:
    bytes_data = text.encode("utf-8")
    encoded = emoji + "".join(filter(None, (to_variation_selector(b) for b in bytes_data)))
    return encoded


def decode(text: str) -> str:
    decoded_bytes = []
    for char in text:
        byte = from_variation_selector(ord(char))
        if byte is None and decoded_bytes:
            break
        elif byte is not None:
            decoded_bytes.append(byte)
    return bytes(decoded_bytes).decode("utf-8")


# Обробник команди /start
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Hello! This bot can Hide and decode message in an emoji!\n"
        "Send me any message to begin."
    )


# Обробка отриманого повідомлення та вибір режиму
@dp.message()
async def ask_mode(message: Message, state: FSMContext):
    if len(message.text) > 3000:
        await message.answer("❌ Your message is too long. Please send a shorter one.")
        return

    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Encode 🔒", callback_data="encode")
    keyboard.button(text="Decode 🔓", callback_data="decode")
    keyboard.adjust(2)

    sent_message = await message.answer("What do you want to do?", reply_markup=keyboard.as_markup())

    await state.update_data(text=message.text, message_id=sent_message.message_id)
    await state.set_state(EncodeDecodeStates.choosing_mode)


# Вибір режиму (Encode)
@dp.callback_query(F.data == "encode")
async def choose_emoji(callback: CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardBuilder()
    for emoji in EMOJIS:
        keyboard.button(text=emoji, callback_data=f"emoji_{emoji}")
    keyboard.adjust(5)

    await callback.message.edit_text("Choose an emoji for encoding:", reply_markup=keyboard.as_markup())
    await state.set_state(EncodeDecodeStates.choosing_emoji)


# Вибір емодзі та одразу кодування
@dp.callback_query(F.data.startswith("emoji_"))
async def encode_and_send(callback: CallbackQuery, state: FSMContext):
    chosen_emoji = callback.data.split("_")[1]
    user_data = await state.get_data()
    text = user_data.get("text", "")

    if not text:
        await callback.message.edit_text("❌ No text found. Please send your message first.")
        return

    encoded_text = encode(chosen_emoji, text)

    await callback.message.edit_text(encoded_text)

    await state.clear()


# Вибір режиму (Decode)
@dp.callback_query(F.data == "decode")
async def decode_message(callback: CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    text = user_data.get("text", "")

    if not text:
        await callback.message.edit_text("❌ No text found. Please send your message first.")
        return

    decoded_text = decode(text)

    if len(decoded_text) > 3000:
        await callback.message.edit_text("❌ Decoded message is too long. Please use a shorter one.")
        return

    await callback.message.edit_text(
        f"<b>Decoded text:</b>\n<code>{decoded_text}</code>",
        parse_mode=ParseMode.HTML
    )

    await state.clear()


# Запуск бота
async def main():
    import middlewares

    for middleware in middlewares.__all__:
        dp.message.outer_middleware(middleware())
        dp.callback_query.outer_middleware(middleware())
        dp.inline_query.outer_middleware(middleware())

        await bot.delete_webhook(drop_pending_updates=True)

        await bot.set_my_commands(commands=BOT_COMMANDS)

        await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
