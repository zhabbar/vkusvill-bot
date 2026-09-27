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
                tools = await session.list_tools()

                for tool in tools.tools:
                    print("=" * 70)
                    print(f"ИНСТРУМЕНТ: {tool.name}")
                    print("=" * 70)
                    # В SDK 2.x поле называется input_schema
                    schema = tool.input_schema or {}
                    props = schema.get("properties", {})
                    required = schema.get("required", [])
                    for name, meta in props.items():
                        req = " (обязательный)" if name in required else ""
                        typ = meta.get("type", "?")
                        desc = meta.get("description", "")
                        default = meta.get("default", "")
                        enum = meta.get("enum")
                        line = f"  - {name}: {typ}{req}"
                        if enum:
                            line += f"  варианты: {enum}"
                        if default != "":
                            line += f"  по умолчанию: {default}"
                        print(line)
                        if desc:
                            print(f"      {desc[:200]}")
                    print()


if __name__ == "__main__":
    asyncio.run(main())