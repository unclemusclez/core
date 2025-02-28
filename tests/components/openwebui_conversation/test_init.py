"""Tests for the OpenWebUI Conversation integration."""

from unittest.mock import patch

import aiohttp
import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


async def test_init_success(hass: HomeAssistant, mock_config_entry: MockConfigEntry) -> None:
    """Test successful initialization."""
    with patch(
        "aiohttp.ClientSession.get",
        return_value=AsyncMock(status=200),
    ):
        assert await async_setup_component(hass, "openwebui_conversation", {})
        await hass.async_block_till_done()


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (aiohttp.ClientConnectionError(), "Connection error"),
        (aiohttp.ClientResponseError(status=401, request_info=None, history=()), "Invalid API key"),
        (aiohttp.ClientResponseError(status=400, request_info=None, history=()), "Failed to connect"),
    ],
)
async def test_init_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    caplog: pytest.LogCaptureFixture,
    side_effect,
    error,
) -> None:
    """Test initialization errors."""
    with patch(
        "aiohttp.ClientSession.get",
        side_effect=side_effect,
    ):
        assert not await async_setup_component(hass, "openwebui_conversation", {})
        await hass.async_block_till_done()
        assert error in caplog.text