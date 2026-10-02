import os
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

import asyncio
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import create_mcp_server, create_agent, MODEL_NAME
from agents import Runner
from agents.exceptions import MaxTurnsExceeded
from agents.stream_events import RunItemStreamEvent

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

ALLOWED_USERS_FILE = Path(__file__).parent / "allowed_users.txt"


def get_allowed_users() -> set[int]:
    """Читает список разрешённых user_id из файла.
    Формат: один ID на строку, комментарии через #."""
    ids: set[int] = set()
    try:
        with open(ALLOWED_USERS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
                try:
                    ids.add(int(line))
                except ValueError:
                    print(f"Некорректный ID в allowed_users.txt: {line!r}")
    except FileNotFoundError:
        print(f"Файл {ALLOWED_USERS_FILE} не найден — доступ запрещён всем")
    return ids


def human_tool_name(tool_name: str) -> str:
    """Переводит техническое имя инструмента в понятный текст."""
    mapping = {
        "vkusvill_recipes": "🔍 Ищу рецепт",
        "vkusvill_products_search": "🛒 Ищу товар",
        "vkusvill_product_details": "📋 Уточняю детали товара",
        "vkusvill_product_barcode": "📊 Ищу по штрихкоду",
        "vkusvill_product_analogs": "🔄 Ищу аналоги",
        "vkusvill_products_discount": "🏷 Ищу акции",
        "vkusvill_cart_link_create": "🛍 Собираю корзину",
        "vkusvill_shops": "📍 Ищу магазины",
    }
    return mapping.get(tool_name, f"🔧 {tool_name}")


def describe_args(tool_name: str, args: dict) -> str:
    """Кратко описывает аргументы вызова инструмента."""
    if tool_name == "vkusvill_products_search":
        q = args.get("q") or args.get("query")
        if q:
            return f"«{q}»"
    if tool_name == "vkusvill_recipes":
        q = args.get("q")
        if q:
            return f"«{q}»"
    if tool_name == "vkusvill_product_details" and "id" in args:
        return f"id={args['id']}"
    if tool_name == "vkusvill_cart_link_create":
        items = args.get("products", [])
        return f"({len(items)} товаров)"
    return ""


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

mcp_server = None
agent = None


async def init_agent():
    global mcp_server, agent
    mcp_server = await create_mcp_server()
    await mcp_server.__aenter__()
    agent = await create_agent(mcp_server)
    print(f"✅ Агент инициализирован. Модель: {MODEL_NAME}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    if message.from_user.id not in get_allowed_users():
        await message.answer("🔒 Извините, бот работает только для избранных пользователей.")
        return
    short_model = MODEL_NAME.split("/")[-1].replace(":free", "")
    await message.answer(
        f"Привет! Я помогу собрать корзину во ВкусВилле.\n\n"
        f"Напиши, что хочешь приготовить. Например:\n"
        f"«Собери продукты для борща на 4 порции»\n\n"
        f"<i>Модель: {short_model}</i>",
        parse_mode="HTML",
    )


@dp.message(Command("model"))
async def cmd_model(message: types.Message):
    if message.from_user.id not in get_allowed_users():
        await message.answer("🔒 Извините, бот работает только для избранных пользователей.")
        return
    await message.answer(f"🤖 Активная модель:\n<code>{MODEL_NAME}</code>", parse_mode="HTML")


@dp.message()
async def handle_message(message: types.Message):
    if message.from_user.id not in get_allowed_users():
        await message.answer("🔒 Извините, бот работает только для избранных пользователей.")
        return

    if agent is None:
        await message.answer("Агент ещё не готов, попробуйте через минуту.")
        return

    short_model = MODEL_NAME.split("/")[-1].replace(":free", "")
    start_time = time.time()

    status_msg = await message.answer(
        f"🤔 Начинаю работу…\n<i>Модель: {short_model}</i>",
        parse_mode="HTML",
    )

    # Троттлинг обновлений: не чаще раза в 2 секунды
    last_edit_time = [0.0]

    async def safe_edit(text: str):
        """Обновляет статусное сообщение, но не чаще раза в 2 секунды."""
        now = time.time()
        if now - last_edit_time[0] < 2.0:
            return
        last_edit_time[0] = now
        try:
            await status_msg.edit_text(text, parse_mode="HTML")
        except Exception:
            # Telegram может отказать (например, сообщение не изменилось)
            pass

    try:
        result = Runner.run_streamed(
            agent,
            input=message.text,
            max_turns=12,
        )

        tools_used = {}
        last_tool_display = ""

        async for event in result.stream_events():
            if isinstance(event, RunItemStreamEvent):
                if event.item.type == "tool_call_item":
                    tool_name = getattr(event.item.raw_item, "name", "инструмент")
                    tools_used[tool_name] = tools_used.get(tool_name, 0) + 1

                    # Кратко описываем аргументы
                    args_display = ""
                    try:
                        raw_args = getattr(event.item.raw_item, "arguments", "{}")
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        args_display = describe_args(tool_name, args)
                    except Exception:
                        pass

                    elapsed = int(time.time() - start_time)
                    last_tool_display = f"{human_tool_name(tool_name)} {args_display}".strip()

                    await safe_edit(
                        f"🔧 {last_tool_display}\n"
                        f"<i>Шаг {sum(tools_used.values())}, прошло {elapsed} сек</i>"
                    )

        # Поток завершён, собираем итог
        elapsed = int(time.time() - start_time)
        final_output = result.final_output

        if final_output:
            tools_summary = ""
            if tools_used:
                parts = [f"{n} ×{c}" if c > 1 else n for n, c in tools_used.items()]
                tools_summary = (
                    f"\n\n<i>⏱ {elapsed} сек · "
                    f"шагов: {sum(tools_used.values())} · "
                    f"{', '.join(parts)}</i>"
                )

            try:
                await status_msg.edit_text(
                    final_output + tools_summary,
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception as send_error:
                print(f"HTML parse failed, sending as plain text: {send_error}")
                await status_msg.delete()
                await message.answer(
                    final_output,
                    disable_web_page_preview=False,
                )
        else:
            await status_msg.edit_text(
                f"⚠️ Не получилось сформулировать ответ за {elapsed} сек. "
                f"Попробуйте уточнить запрос."
            )

    except MaxTurnsExceeded:
        elapsed = int(time.time() - start_time)
        await status_msg.edit_text(
            f"⏱ Превышен лимит шагов ({elapsed} сек). "
            f"Попробуйте назвать конкретное блюдо — «борщ», «паста», «запеканка»."
        )
    except Exception as e:
        elapsed = int(time.time() - start_time)
        await status_msg.edit_text(f"❌ Ошибка через {elapsed} сек: {e}")
        print(f"Ошибка: {e}")


async def main():
    await init_agent()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())