"""Tests for config module."""
import os
import sys
from unittest.mock import patch, AsyncMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest


def test_config_loads_env_variables():
    """Test that config loads environment variables correctly."""
    with patch.dict(os.environ, {
        "OPENROUTER_API_KEY": "test-key",
        "OPENROUTER_MODEL": "test-model",
        "MAX_TURNS": "15",
    }):
        # Reload config module
        import importlib
        import config
        importlib.reload(config)
        
        assert config.OPENROUTER_API_KEY == "test-key"
        assert config.MODEL_NAME == "test-model"
        assert config.MAX_TURNS == 15


def test_config_default_values():
    """Test default values when env vars are not set."""
    with patch.dict(os.environ, {"OPENROUTER_MODEL": "openrouter/free", "MAX_TURNS": "20"}, clear=True):
        import importlib
        import config
        importlib.reload(config)
        
        assert config.MODEL_NAME == "openrouter/free"
        assert config.MAX_TURNS == 20
        assert config.MCP_URL == "https://mcp001.vkusvill.ru/mcp"


def test_agent_instructions_not_empty():
    """Test that agent instructions are defined."""
    from config import AGENT_INSTRUCTIONS
    
    assert isinstance(AGENT_INSTRUCTIONS, str)
    assert len(AGENT_INSTRUCTIONS) > 100
    assert "vkusvill_recipes" in AGENT_INSTRUCTIONS
    assert "vkusvill_products_search" in AGENT_INSTRUCTIONS
    assert "vkusvill_cart_link_create" in AGENT_INSTRUCTIONS


@pytest.mark.asyncio
async def test_create_mcp_server():
    """Test MCP server creation."""
    from config import create_mcp_server
    
    server = await create_mcp_server()
    assert server is not None
    assert server.name == "VkusVill MCP Server"
    
    # Clean up
    await server.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_create_agent():
    """Test agent creation."""
    from config import create_mcp_server, create_agent, AGENT_INSTRUCTIONS
    
    mcp_server = await create_mcp_server()
    async with mcp_server:
        agent = await create_agent(mcp_server)
        assert agent is not None
        assert agent.name == "Повар-помощник"
        assert agent.instructions == AGENT_INSTRUCTIONS