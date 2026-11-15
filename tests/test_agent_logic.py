"""Tests for agent instruction logic validation."""
import os
import sys
import re
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_agent_instructions_structure():
    """Test that agent instructions contain all required sections."""
    from config import AGENT_INSTRUCTIONS
    
    # Check main sections
    assert "ПОРЯДОК ДЕЙСТВИЙ" in AGENT_INSTRUCTIONS
    assert "ЖЁСТКИЕ ПРАВИЛА" in AGENT_INSTRUCTIONS
    assert "ФОРМАТ ОТВЕТА" in AGENT_INSTRUCTIONS
    assert "ПРИМЕР ХОРОШЕГО ОТВЕТА" in AGENT_INSTRUCTIONS


def test_agent_instructions_key_rules():
    """Test that key rules are present in instructions."""
    from config import AGENT_INSTRUCTIONS
    
    # Rule: don't repeat tool calls
    assert "НИКОГДА не вызывай один и тот же инструмент с одинаковыми аргументами дважды" in AGENT_INSTRUCTIONS
    
    # Rule: max product searches
    assert "Максимум 10 вызовов vkusvill_products_search" in AGENT_INSTRUCTIONS
    
    # Rule: max total tool calls
    assert "Не делай больше 15 вызовов инструментов всего за один запрос" in AGENT_INSTRUCTIONS
    
    # Rule: eggs packaging
    assert "ВАЖНО ПРО ЯЙЦА" in AGENT_INSTRUCTIONS
    assert "упаковка 10 штук (десяток)" in AGENT_INSTRUCTIONS
    
    # Rule: skip common ingredients
    assert "НЕ ИЩИ следующие категории товаров" in AGENT_INSTRUCTIONS
    assert "соль, сахар, перец" in AGENT_INSTRUCTIONS


def test_agent_instructions_html_format():
    """Test that HTML format requirements are specified."""
    from config import AGENT_INSTRUCTIONS
    
    assert "<b>жирный</b>" in AGENT_INSTRUCTIONS
    assert "<i>курсив</i>" in AGENT_INSTRUCTIONS
    assert "<code>моноширинный</code>" in AGENT_INSTRUCTIONS
    assert "<a href=" in AGENT_INSTRUCTIONS
    assert "Telegram НЕ понимает Markdown" in AGENT_INSTRUCTIONS


def test_agent_instructions_emoji_markers():
    """Test that emoji markers for lists are specified."""
    from config import AGENT_INSTRUCTIONS
    
    assert "эмодзи-маркеры" in AGENT_INSTRUCTIONS
    assert "🥛" in AGENT_INSTRUCTIONS or "🥚" in AGENT_INSTRUCTIONS or "🧈" in AGENT_INSTRUCTIONS


def test_agent_instructions_russian_only():
    """Test that instructions emphasize Russian-only text."""
    from config import AGENT_INSTRUCTIONS
    
    assert "Пиши слова ЦЕЛИКОМ на русском языке" in AGENT_INSTRUCTIONS
    assert "без смешивания алфавитов" in AGENT_INSTRUCTIONS


def test_agent_example_response_format():
    """Test that example response has correct format."""
    from config import AGENT_INSTRUCTIONS
    
    # Extract example
    example_start = AGENT_INSTRUCTIONS.find("ПРИМЕР ХОРОШЕГО ОТВЕТА:")
    example = AGENT_INSTRUCTIONS[example_start:]
    
    assert "🔗 <a href=" in example
    assert "Открыть корзину</a>" in example
    assert "<b>Ингредиенты:</b>" in example
    # Check emoji markers in example
    assert any(emoji in example for emoji in ["🥩", "🫒", "🥬", "🥔"])


def test_model_name_from_env():
    """Test model name configuration."""
    import os
    import importlib
    import config
    
    # Test default from code (not from .env)
    # We need to patch before load_dotenv is called, so we mock the default
    with patch.dict(os.environ, {"OPENROUTER_MODEL": "openrouter/free"}, clear=True):
        importlib.reload(config)
        assert config.MODEL_NAME == "openrouter/free"
    
    # Test custom
    with patch.dict(os.environ, {"OPENROUTER_MODEL": "custom/model"}):
        importlib.reload(config)
        assert config.MODEL_NAME == "custom/model"


def test_mcp_url_format():
    """Test MCP URL is correct."""
    from config import MCP_URL
    
    assert MCP_URL == "https://mcp001.vkusvill.ru/mcp"
    assert MCP_URL.startswith("https://")
    assert "vkusvill.ru" in MCP_URL


def test_model_name_from_env():
    """Test model name configuration."""
    import os
    import importlib
    import config
    
    # Test default from code (not from .env)
    # We need to patch before load_dotenv is called, so we mock the default
    with patch.dict(os.environ, {"OPENROUTER_MODEL": "openrouter/free"}, clear=True):
        importlib.reload(config)
        assert config.MODEL_NAME == "openrouter/free"
    
    # Test custom
    with patch.dict(os.environ, {"OPENROUTER_MODEL": "custom/model"}):
        importlib.reload(config)
        assert config.MODEL_NAME == "custom/model"