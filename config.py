import os
import httpx2
from dotenv import load_dotenv

from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStreamableHttp

load_dotenv()

# --- Настройки (меняй здесь) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "stealth/space-bunny-alpha")
MCP_URL = "https://mcp001.vkusvill.ru/mcp"

AGENT_INSTRUCTIONS = (
    "Ты — полезный ассистент, который помогает пользователю собрать корзину продуктов во ВкусВилле. "
    "Твоя задача — понять, что хочет приготовить пользователь, найти рецепт, "
    "подобрать ингредиенты в магазине и создать ссылку на корзину. "
    "Используй предоставленные инструменты для поиска рецептов и товаров. "
    "Всегда возвращай пользователю ссылку на готовую корзину. "
    "Будь вежливым и кратко объясняй свои действия."
)
# -------------------------------


async def create_mcp_server():
    http_client = httpx2.AsyncClient(
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/event-stream",
        },
        timeout=60.0,
    )
    return MCPServerStreamableHttp(
        name="VkusVill MCP Server",
        params={"url": MCP_URL, "http_client": http_client},
    )


async def create_agent(mcp_server):
    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )
    model = OpenAIChatCompletionsModel(
        model=MODEL_NAME,
        openai_client=client,
    )
    return Agent(
        name="Повар-помощник",
        instructions=AGENT_INSTRUCTIONS,
        mcp_servers=[mcp_server],
        model=model,
    )