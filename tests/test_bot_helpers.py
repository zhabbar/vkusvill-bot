"""Tests for bot helper functions."""
import os
import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_human_tool_name():
    """Test human-readable tool names mapping."""
    from bot import human_tool_name
    
    assert human_tool_name("vkusvill_recipes") == "🔍 Ищу рецепт"
    assert human_tool_name("vkusvill_products_search") == "🛒 Ищу товар"
    assert human_tool_name("vkusvill_cart_link_create") == "🛍 Собираю корзину"
    assert human_tool_name("unknown_tool") == "🔧 unknown_tool"


def test_describe_args():
    """Test argument description formatting."""
    from bot import describe_args
    
    # Products search
    assert describe_args("vkusvill_products_search", {"q": "молоко"}) == "«молоко»"
    assert describe_args("vkusvill_products_search", {"query": "хлеб"}) == "«хлеб»"
    assert describe_args("vkusvill_products_search", {}) == ""
    
    # Recipes
    assert describe_args("vkusvill_recipes", {"q": "борщ"}) == "«борщ»"
    
    # Cart
    assert describe_args("vkusvill_cart_link_create", {"products": [{"xml_id": 1}, {"xml_id": 2}]}) == "(2 товаров)"
    assert describe_args("vkusvill_cart_link_create", {"products": []}) == "(0 товаров)"
    
    # Product details
    assert describe_args("vkusvill_product_details", {"id": 123}) == "id=123"
    
    # Unknown tool
    assert describe_args("unknown", {}) == ""


def test_format_tool_output_products_search():
    """Test formatting of products search output."""
    from bot import format_tool_output
    
    # Mock MCP output with content list
    class MockContent:
        def __init__(self, text):
            self.text = text
            self.type = "text"
    
    class MockOutput:
        def __init__(self, data):
            self.content = [MockContent(json.dumps(data))]
    
    # Test with results
    data = {
        "data": {
            "items": [
                {"name": "Молоко 3.2%", "price": {"current": 85}, "unit": "л"},
                {"name": "Хлеб батон", "price": {"current": 45}, "unit": "шт"},
            ],
            "meta": {"total": 10}
        }
    }
    output = MockOutput(data)
    result = format_tool_output("vkusvill_products_search", output)
    assert "Найдено 10 товаров" in result
    assert "Молоко 3.2%" in result
    assert "85 ₽/л" in result
    
    # Test empty results
    data_empty = {"data": {"items": [], "meta": {"total": 0}}}
    output_empty = MockOutput(data_empty)
    result_empty = format_tool_output("vkusvill_products_search", output_empty)
    assert "Ничего не найдено" in result_empty


def test_format_tool_output_recipes():
    """Test formatting of recipes output."""
    from bot import format_tool_output
    
    class MockContent:
        def __init__(self, text):
            self.text = text
            self.type = "text"
    
    class MockOutput:
        def __init__(self, data):
            self.content = [MockContent(json.dumps(data))]
    
    data = {
        "data": {
            "items": [
                {"name": "Борщ классический", "id": 123}
            ]
        }
    }
    output = MockOutput(data)
    result = format_tool_output("vkusvill_recipes", output)
    assert "Борщ классический" in result


def test_format_tool_output_cart():
    """Test formatting of cart creation output."""
    from bot import format_tool_output
    
    class MockContent:
        def __init__(self, text):
            self.text = text
            self.type = "text"
    
    class MockOutput:
        def __init__(self, data):
            self.content = [MockContent(json.dumps(data))]
    
    data = {"data": {"link": "https://vkusvill.ru/?share_basket=abc123"}}
    output = MockOutput(data)
    result = format_tool_output("vkusvill_cart_link_create", output)
    assert "Корзина создана" in result
    assert "abc123" in result


def test_clean_broken_html():
    """Test cleaning broken HTML."""
    from bot import clean_broken_html
    
    # Test link conversion
    text = '<a href="https://example.com">Ссылка</a>'
    result = clean_broken_html(text)
    assert "Ссылка (https://example.com)" in result
    
    # Test tag removal
    text = "<b>Жирный</b> и <i>курсив</i>"
    result = clean_broken_html(text)
    assert "Жирный" in result
    assert "курсив" in result
    assert "<b>" not in result
    assert "<i>" not in result
    
    # Test entity decoding - incomplete tags are also removed
    text = "<script>"
    result = clean_broken_html(text)
    assert result == ""  # incomplete tag is removed
    
    # Test that unknown tags are removed
    text = "<unknown>text</unknown>"
    result = clean_broken_html(text)
    assert "text" in result
    assert "<unknown>" not in result


def test_truncate():
    """Test text truncation."""
    from bot import truncate
    
    short = "Короткий текст"
    assert truncate(short, 100) == short
    
    long = "А" * 2000
    result = truncate(long, 100)
    # 100 chars + newline + "…<обрезано>" (10 chars) = ~111
    assert len(result) <= 115
    assert result.endswith("…<обрезано>")


def test_get_allowed_users(tmp_path):
    """Test loading allowed users from file."""
    from bot import get_allowed_users, ALLOWED_USERS_FILE
    
    # Create temp file
    test_file = tmp_path / "allowed_users.txt"
    test_file.write_text("12345 # User1\n67890 # User2\n# Comment\n\n99999 # User3")
    
    with patch("bot.ALLOWED_USERS_FILE", test_file):
        users = get_allowed_users()
        assert users == {12345, 67890, 99999}


def test_get_allowed_users_file_not_found():
    """Test behavior when allowed_users.txt doesn't exist."""
    from bot import get_allowed_users
    
    with patch("bot.ALLOWED_USERS_FILE", Path("/nonexistent/path/allowed_users.txt")):
        users = get_allowed_users()
        assert users == set()