import os
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

import asyncio
import os as _os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Импортируем агента
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStreamableHttp
import httpx2

load_dotenv()
BOT_TOKEN = _os.getenv("BOT_TOKEN")
OPENROUTER_API_KEY = _os.getenv("OPENROUTER_API_KEY")
MCP_URL = "https://mcp001.vkusvill.ru/mcp"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

mcp_server = None
agent = None


async def init_agent():
    global mcp_server, agent

    http_client = httpx2.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/event-stream",
        },
        timeout=60.0,
    )
    mcp_server = MCPServerStreamableHttp(
        name="VkusVill MCP Server",
        params={"url": MCP_URL, "http_client": http_client},
    )
    await mcp_server.__aenter__()

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    model = OpenAIChatCompletionsModel(
        model="z-ai/glm-4.5-air:free",
        openai_client=client,
    )

    agent = Agent(
        name="Повар-помощник",
        instructions=(
            "Ты — полезный ассистент, который помогает пользователю собрать корзину продуктов во ВкусВилле. "
            "Твоя задача — понять, что хочет приготовить пользователь, найти рецепт, "
            "подобрать ингредиенты в магазине и создать ссылку на корзину. "
            "Используй предоставленные инструменты для поиска рецептов и товаров. "
            "Всегда возвращай пользователю ссылку на готовую корзину. "
            "Будь вежливым и кратко объясняй свои действия."
        ),
        mcp_servers=[mcp_server],
        model=model,
    )
    print("Агент инициализирован.")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Напиши, что хочешь приготовить, и я соберу корзину продуктов во ВкусВилле.\n"
        "Например: «Собери продукты для борща на 4 порции»."
    )


@dp.message()
async def handle_message(message: types.Message):
    if agent is None:
        await message.answer("Агент ещё не готов, попробуйте через минуту.")
        return

    await message.answer("Думаю… Это может занять до минуты.")
    try:
        result = await Runner.run(agent, input=message.text)
        if result.final_output:
            await message.answer(result.final_output, disable_web_page_preview=False)
        else:
            await message.answer("Готово, но не могу сформулировать ответ. Проверьте логи.")
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
        print(f"Ошибка: {e}")


async def main():
    await init_agent()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())