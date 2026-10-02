import os
os.environ["OPENAI_AGENTS_DISABLE_TRACING"] = "1"

import asyncio
import json
import re
import time
from pathlib import Path
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from config import create_mcp_server, create_agent, MODEL_NAME, MAX_TURNS
from agents import Runner
from agents.exceptions import MaxTurnsExceeded
from agents.stream_events import RunItemStreamEvent

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

ALLOWED_USERS_FILE = Path(__file__).parent / "allowed_users.txt"


def get_allowed_users() -> set[int]:
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
    mapping = {
        "vkusvill_recipes": "🔍 Ищу рецепт",
        "vkusvill_products_search": "🛒 Ищу товар",
        "vkusvill_product_details": "📋 Уточняю детали",
        "vkusvill_product_barcode": "📊 По штрихкоду",
        "vkusvill_product_analogs": "🔄 Ищу аналоги",
        "vkusvill_products_discount": "🏷 Ищу акции",
        "vkusvill_cart_link_create": "🛍 Собираю корзину",
        "vkusvill_shops": "📍 Ищу магазины",
    }
    return mapping.get(tool_name, f"🔧 {tool_name}")


def describe_args(tool_name: str, args: dict) -> str:
    if tool_name in ("vkusvill_products_search", "vkusvill_recipes"):
        q = args.get("q") or args.get("query")
        if q:
            return f"«{q}»"
    if tool_name == "vkusvill_product_details" and "id" in args:
        return f"id={args['id']}"
    if tool_name == "vkusvill_cart_link_create":
        items = args.get("products", [])
        return f"({len(items)} товаров)"
    return ""


def _extract_text_payload(raw_output: str) -> str:
    """
    Достаёт полезную нагрузку из MCP-обёртки вида:
    {'type': 'text', 'text': '{\n  "ok": true, ...}'}
    Возвращает строку — то, что можно распарсить как JSON.
    """
    raw = raw_output.strip()

    # Случай 1: питоновский dict со str-представлением
    if raw.startswith("{'type'") or raw.startswith('{"type"'):
        # Вытаскиваем содержимое поля 'text' регуляркой
        m = re.search(
            r"['\"]text['\"]\s*:\s*['\"]((?:[^'\"\\]|\\.)*)['\"]",
            raw,
            re.DOTALL,
        )
        if m:
            extracted = m.group(1)
            try:
                # Раскодируем escape-последовательности (\n, \", \\ и т.д.)
                extracted = bytes(extracted, "utf-8").decode("unicode_escape")
            except Exception:
                pass
            return extracted

    # Случай 2: уже чистый JSON или что-то другое
    return raw


def format_tool_output(tool_name: str, raw_output: str) -> str:
    """Превращает сырой ответ MCP в читаемую строку."""
    payload_str = _extract_text_payload(raw_output)

    try:
        data = json.loads(payload_str)
    except json.JSONDecodeError:
        preview = payload_str[:400].replace("<", "&lt;").replace(">", "&gt;")
        return f"<code>{preview}</code>"

    # --- Поиск товаров ---
    if tool_name == "vkusvill_products_search":
        items = data.get("data", {}).get("items", [])
        meta = data.get("data", {}).get("meta", {})
        if not items:
            return "❌ Ничего не найдено"

        lines = [f"Найдено {meta.get('total', '?')} товаров. Первые:"]
        for item in items[:3]:
            name = item.get("name", "?")
            price = item.get("price", {}).get("current", "?")
            unit = item.get("unit", "шт")
            if len(name) > 50:
                name = name[:50] + "…"
            lines.append(f"  • {name} — {price} ₽/{unit}")
        return "\n".join(lines)

    # --- Рецепты ---
    if tool_name == "vkusvill_recipes":
        recipes = data.get("data", {}).get("items", [])
        if not recipes:
            return "❌ Рецепты не найдены"
        first = recipes[0]
        name = first.get("name", "?")
        lines = [f"📖 {name}"]
        ingredients = first.get("ingredients", []) or first.get("properties", [])
        if ingredients:
            ings = []
            for ing in ingredients[:6]:
                if isinstance(ing, dict):
                    ings.append(ing.get("name", "?"))
                else:
                    ings.append(str(ing))
            lines.append(f"  Ингредиенты: {', '.join(ings)}…")
        return "\n".join(lines)

    # --- Создание корзины ---
    if tool_name == "vkusvill_cart_link_create":
        link = data.get("data", {}).get("link", "")
        return f"🔗 Корзина создана: <a href=\"{link}\">открыть</a>"

    # --- Детали товара ---
    if tool_name == "vkusvill_product_details":
        item = data.get("data", {})
        name = item.get("name", "?")
        price = item.get("price", {}).get("current", "?")
        return f"📋 {name} — {price} ₽"

    # --- Fallback ---
    preview = payload_str[:300].replace("<", "&lt;").replace(">", "&gt;")
    return f"<code>{preview}</code>"


def truncate(text: str, limit: int = 1500) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "\n…<обрезано>"


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

mcp_server = None
agent = None


async def init_agent():
    global mcp_server, agent
    mcp_server = await create_mcp_server()
    await mcp_server.__aenter__()
    agent = await create_agent(mcp_server)
    print(f"✅ Агент инициализирован. Модель: {MODEL_NAME}. MAX_TURNS: {MAX_TURNS}")


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

    await message.answer(
        f"🤔 Начинаю работу…\n<i>Модель: {short_model}, лимит шагов: {MAX_TURNS}</i>",
        parse_mode="HTML",
    )

    try:
        result = Runner.run_streamed(
            agent,
            input=message.text,
            max_turns=MAX_TURNS,
        )

        tools_used = {}
        step = 0
        last_tool_name = None

        async for event in result.stream_events():
            if isinstance(event, RunItemStreamEvent):
                item_type = getattr(event.item, "type", None)

                if item_type == "tool_call_item":
                    step += 1
                    tool_name = getattr(event.item.raw_item, "name", "инструмент")
                    last_tool_name = tool_name
                    tools_used[tool_name] = tools_used.get(tool_name, 0) + 1

                    args_display = ""
                    try:
                        raw_args = getattr(event.item.raw_item, "arguments", "{}")
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                        args_display = describe_args(tool_name, args)
                    except Exception:
                        pass

                    elapsed = int(time.time() - start_time)
                    text = (
                        f"<b>Шаг {step}/{MAX_TURNS}</b> · {elapsed} сек\n"
                        f"{human_tool_name(tool_name)} {args_display}".strip()
                    )
                    await message.answer(text, parse_mode="HTML")

                elif item_type == "tool_call_output_item":
                    raw_output = str(getattr(event.item, "output", ""))
                    formatted = format_tool_output(last_tool_name or "", raw_output)
                    await message.answer(
                        f"📥 <b>Ответ:</b>\n{formatted}",
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )

        elapsed = int(time.time() - start_time)
        final_output = result.final_output

        await message.answer(
            f"✅ <b>Готово за {elapsed} сек. Шагов: {step}/{MAX_TURNS}</b>",
            parse_mode="HTML",
        )

        if final_output:
            try:
                await message.answer(
                    truncate(final_output),
                    parse_mode="HTML",
                    disable_web_page_preview=False,
                )
            except Exception as send_error:
                print(f"HTML parse failed, sending as plain text: {send_error}")
                await message.answer(
                    truncate(final_output),
                    disable_web_page_preview=False,
                )
        else:
            await message.answer(
                "⚠️ Финальный ответ пустой. Возможно, модель ушла в цикл "
                "или превысила лимит шагов."
            )

    except MaxTurnsExceeded:
        elapsed = int(time.time() - start_time)
        await message.answer(
            f"⏱ <b>Превышен лимит шагов ({elapsed} сек).</b>\n"
            f"Лимит: {MAX_TURNS}. Модель зациклилась. Попробуйте назвать "
            f"конкретное блюдо или увеличьте MAX_TURNS в .env.",
            parse_mode="HTML",
        )
    except Exception as e:
        elapsed = int(time.time() - start_time)
        await message.answer(
            f"❌ <b>Ошибка через {elapsed} сек:</b>\n<code>{e}</code>",
            parse_mode="HTML",
        )
        print(f"Ошибка: {e}")


async def main():
    await init_agent()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())