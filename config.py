import os
import httpx2
from dotenv import load_dotenv

from agents import Agent, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStreamableHttp

load_dotenv()

# --- Настройки (меняй здесь) ---
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_NAME = os.getenv("OPENROUTER_MODEL", "openrouter/free")
MCP_URL = "https://mcp001.vkusvill.ru/mcp"

AGENT_INSTRUCTIONS = (
    "Ты — ассистент, который помогает пользователю собрать корзину продуктов во ВкусВилле. "
    "\n\n"
    "ПОРЯДОК ДЕЙСТВИЙ:\n"
    "1. Определи блюдо из запроса пользователя. Если пользователь спрашивает "
    "   «что приготовить из X и Y» — выбери ОДИН подходящий рецепт через "
    "   vkusvill_recipes и работай с ним. Не перебирай десятки вариантов.\n"
    "2. Получи список ингредиентов этого рецепта.\n"
    "3. Для КАЖДОГО ингредиента вызови vkusvill_products_search ОДИН раз. "
    "   Если поиск не дал результата — пропусти ингредиент, не повторяй запрос.\n"
    "4. Собери корзину через vkusvill_cart_link_create.\n"
    "5. Верни пользователю ссылку и краткое описание.\n"
    "\n"
    "ПРАВИЛА:\n"
    "- Не вызывай один и тот же инструмент с одинаковыми аргументами дважды.\n"
    "- Если рецепт не найден после 2 попыток — предложи пользователю уточнить запрос.\n"
    "- Максимум 15 вызовов инструментов на один запрос пользователя.\n"
    "- Будь кратким. Не пиши длинных рассуждений.\n"
    "- Если запрос неоднозначный — задай уточняющий вопрос."
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