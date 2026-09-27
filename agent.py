import os
import asyncio
from dotenv import load_dotenv

# Импортируем компоненты для создания агента
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStreamableHttp  # <-- Используем Streamable HTTP

# Импортируем клиент для MCP
import httpx2 # <-- Используем httpx2, как в вашей ошибке

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# URL MCP-сервера ВкусВилла
MCP_URL = "https://mcp001.vkusvill.ru/mcp" # <-- Используем официальный URL

# Создаем MCP-сервер для агента.
async def create_mcp_server():
    # Создаем http_client с необходимыми заголовками
    # Важно: используем httpx2, так как он используется в вашем окружении
    http_client = httpx2.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/event-stream",
        },
        timeout=60.0,
    )
    return MCPServerStreamableHttp(
        name="VkusVill MCP Server",
        params={
            "url": MCP_URL,
            "http_client": http_client,
        }
    )

# Создаем и запускаем агента
async def main():
    mcp_server = await create_mcp_server()
    
    async with mcp_server:
        # Настраиваем клиент OpenRouter через AsyncOpenAI
        client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        
        # Создаем модель
        model = OpenAIChatCompletionsModel(
            model="stealth/space-bunny-alpha",
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

        # Пример запроса к агенту (для теста)
        user_input = "Собери продукты для борща на 4 порции"
        print(f"Пользователь: {user_input}")

        # Запускаем агента
        result = await Runner.run(agent, input=user_input)
        
        print("\nАгент:")
        if result.final_output:
            print(result.final_output)
        else:
            for item in result.new_items:
                if item.type == "tool_call":
                    print(f"  [Вызов инструмента: {item.tool_name}]")
                elif item.type == "message":
                    print(f"  {item.content}")


if __name__ == "__main__":
    asyncio.run(main())