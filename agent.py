import asyncio
import sys
from config import create_mcp_server, create_agent
from agents import Runner


async def main():
    # Fix Windows console encoding
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    mcp_server = await create_mcp_server()

    async with mcp_server:
        agent = await create_agent(mcp_server)
        print("[OK] Агент готов\n")

        user_input = "Собери продукты для борща на 4 порции"
        print(f"Пользователь: {user_input}\n")

        result = await Runner.run(agent, input=user_input)

        print("\n=== ХОД РАБОТЫ АГЕНТА ===")
        for item in result.new_items:
            item_type = getattr(item, "type", "?")
            if item_type == "tool_call_item":
                print(f"\n[>] Вызов инструмента:")
                print(f"  name: {getattr(item, 'name', '?')}")
                args = getattr(item, "arguments", None)
                if args:
                    print(f"  args: {args[:500]}")
            elif item_type == "tool_call_output_item":
                output = getattr(item, "output", "")
                print(f"  [<] Результат (первые 800 символов):")
                print(f"  {str(output)[:800]}")
            elif item_type == "message_output_item":
                content = getattr(item, "content", "")
                print(f"\n[*] Сообщение модели: {str(content)[:500]}")

        print("\n=== ФИНАЛЬНЫЙ ОТВЕТ ===")
        print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())