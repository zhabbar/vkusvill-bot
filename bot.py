import os
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

import asyncio
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import create_mcp_server, create_agent
from agents import Runner
from agents.exceptions import MaxTurnsExceeded

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Путь к файлу со списком разрешённых пользователей
ALLOWED_USERS_FILE = Path(__file__).parent / "allowed_users.txt"


def get_allowed_users() -> set[int]:
    """Читает список разрешённых user_id из файла.
    Формат: один ID на строку, комментарии через #."""
    ids: set[int] = set()
    try:
        with open(ALLOWED_USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                try:
                    ids.add(int(line))
                except ValueError:
                    print(f"Некорректный ID в allowed_users.txt: {line!r}")
    except FileNotFoundError:
        print(f"Файл {ALLOWED_USERS_FILE} не найден — доступ запрещён всем")
    return ids


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

mcp_server = None
agent = None


async def init_agent():
    global mcp_server, agent
    mcp_server = await create_mcp_server()
    await mcp_server.__aenter__()
    agent = await create_agent(mcp_server)
    print("Агент инициализирован.")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in get_allowed_users():
        await message.answer(
            "🔒 Извините, бот работает только для избранных пользователей."
        )
        return
    await message.answer(
        "Привет! Напиши, что хочешь приготовить, и я соберу корзину продуктов "
        "во ВкусВилле.\n"
        "Например: «Собери продукты для борща на 4 порции»."
    )


@dp.message()
async def handle_message(message: types.Message):
    if message.from_user.id not in get_allowed_users():
        await message.answer(
            "🔒 Извините, бот работает только для избранных пользователей."
        )
        return

    if agent is None:
        await message.answer("Агент ещё не готов, попробуйте через минуту.")
        return

    await message.answer("Думаю… Это может занять до минуты.")
    try:
        result = await Runner.run(
            agent,
            input=message.text,
            max_turns=20,
        )
        if result.final_output:
            try:
                await message.answer(
                    result.final_output,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception as send_error:
                print(f"HTML parse failed, sending as plain text: {send_error}")
                await message.answer(
                    result.final_output,
                    disable_web_page_preview=False,
                )
        else:
            await message.answer("Готово, но не могу сформулировать ответ.")
    except MaxTurnsExceeded:
        await message.answer(
            "Не получилось собрать ответ за разумное время. "
            "Попробуйте уточнить запрос — например, назовите конкретное блюдо."
        )
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
        print(f"Ошибка: {e}")


async def main():
    await init_agent()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())