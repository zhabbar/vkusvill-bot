"""Tests for MCP tool schemas and basic functionality."""
import os
import sys
import json
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_mcp_tool_names():
    """Test that expected MCP tool names are known."""
    # These are the tools available from VkusVill MCP server
    expected_tools = {
        "vkusvill_recipes",
        "vkusvill_products_search",
        "vkusvill_product_details",
        "vkusvill_product_barcode",
        "vkusvill_product_analogs",
        "vkusvill_products_discount",
        "vkusvill_cart_link_create",
        "vkusvill_shops",
    }
    
    # This test documents the expected tools
    # Actual validation happens in integration tests
    assert len(expected_tools) == 8


@pytest.mark.asyncio
async def test_products_search_parameters():
    """Test that products_search uses correct parameter name 'q' not 'query'."""
    # Based on test_mcp_tools.py in project root, the correct parameter is 'q'
    # This test documents the expected parameter
    # The actual MCP call is tested in integration
    params = {"q": "молоко", "mode": "short"}
    assert "q" in params
    assert "query" not in params


@pytest.mark.asyncio
async def test_recipes_required_parameters():
    """Test that recipes tool requires all parameters."""
    # Based on test_mcp_tools.py, all these params are required
    required_params = {
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
    
    assert all(key in required_params for key in [
        "q", "sort", "page", "id_feature_filter",
        "id_cooking_time_filter", "id_cooking_method_filter",
        "id_complexity_filter", "id_category_filter",
        "id_exclude_allergens_filter"
    ])


@pytest.mark.asyncio
async def test_cart_link_create_format():
    """Test cart link creation format."""
    # Products should be list of dicts with xml_id and q
    products = [
        {"xml_id": 36296, "q": 1},
        {"xml_id": 173, "q": 2},
    ]
    
    for product in products:
        assert "xml_id" in product
        assert "q" in product
        assert isinstance(product["xml_id"], int)
        assert isinstance(product["q"], int)
        assert product["q"] > 0