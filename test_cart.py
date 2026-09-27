import asyncio
import json
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

MCP_URL = "https://mcp.vkusvill.ru/mcp"


async def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/event-stream",
    }
    async with httpx.AsyncClient(headers=headers, timeout=60.0) as http_client:
        async with streamable_http_client(MCP_URL, http_client=http_client) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Создаём корзину: молоко (xml_id 36296) x1 и молоко 3.2% (xml_id 173) x2
                result = await session.call_tool(
                    "vkusvill_cart_link_create",
                    {
                        "products": [
                            {"xml_id": 36296, "q": 1},
                            {"xml_id": 173, "q": 2},
                        ]
                    }
                )

                print("=== Результат ===")
                for item in result.content:
                    if item.type == "text":
                        try:
                            data = json.loads(item.text)
                            print(json.dumps(data, ensure_ascii=False, indent=2))
                        except json.JSONDecodeError:
                            print(item.text)


if __name__ == "__main__":
    asyncio.run(main())