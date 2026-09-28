import os
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import create_mcp_server, create_agent
from agents import Runner
from agents.exceptions import MaxTurnsExceeded

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

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
    await message.answer(
        "Привет! Напиши, что хочешь приготовить, и я соберу корзину продуктов "
        "во ВкусВилле.\n"
        "Например: «Собери продукты для борща на 4 порции»."
    )


@dp.message()
async def handle_message(message: types.Message):
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
                # Если HTML сломан — отправляем как обычный текст
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