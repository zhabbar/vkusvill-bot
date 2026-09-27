import asyncio
import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

async def main():
    url = "https://mcp.vkusvill.ru/mcp"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/event-stream",
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as http_client:
        try:
            # ИСПРАВЛЕНИЕ: распаковываем 2 значения, а не 3
            async with streamable_http_client(url, http_client=http_client) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    print("✅ Сессия успешно инициализирована!")
                    
                    tools = await session.list_tools()
                    print("\n📋 Доступные инструменты:")
                    for tool in tools.tools:
                        print(f"  - {tool.name}: {tool.description}")
                        
        except BaseException as e:
            print(f"❌ Ошибка: {type(e).__name__}: {e}")
            if hasattr(e, 'exceptions'):
                for sub in e.exceptions:
                    print(f"   ↳ Под-ошибка: {type(sub).__name__}: {sub}")
                    if hasattr(sub, 'exceptions'):
                        for sub2 in sub.exceptions:
                            print(f"      ↳ Вложенная: {type(sub2).__name__}: {sub2}")

if __name__ == "__main__":
    asyncio.run(main())