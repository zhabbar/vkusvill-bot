import asyncio
import json
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "https://mcp.vkusvill.ru/mcp"


def print_result(title, result):
    print(f"\n=== {title} ===")
    for item in result.content:
        if item.type == "text":
            try:
                data = json.loads(item.text)
                print(json.dumps(data, ensure_ascii=False, indent=2)[:4000])
            except json.JSONDecodeError:
                print(item.text[:4000])
        else:
            print(f"[{item.type}]")


async def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/event-stream",
    }
    async with httpx.AsyncClient(headers=headers, timeout=60.0) as http_client:
        async with streamable_http_client(MCP_URL, http_client=http_client) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("✅ Сессия инициализирована")

                # 1. Поиск товаров — параметр q, не query
                result = await session.call_tool(
                    "vkusvill_products_search",
                    {"q": "молоко", "mode": "short"}
                )
                print_result("1. Поиск: молоко", result)

                # 2. Рецепты — все параметры обязательные
                result = await session.call_tool(
                    "vkusvill_recipes",
                    {
                        "q": "борщ",
                        "sort": "popularity",
                        "page": 1,
                        "id_feature_filter": 0,
                        "id_cooking_time_filter": 0,
                        "id_cooking_method_filter": 0,
                        "id_complexity_filter": 0,
                        "id_category_filter": 0,
                        "id_exclude_allergens_filter": [],
                    }
                )
                print_result("2. Рецепты: борщ", result)


if __name__ == "__main__":
    asyncio.run(main())