"""Test helpers."""

from unittest.mock import AsyncMock, patch

import pytest

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from tests.common import MockConfigEntry


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Mock a config entry."""
    entry = MockConfigEntry(
        title="OpenWebUI",
        domain="openwebui_conversation",
        data={
            "openwebui_api": "test-key",
            "openwebui_host": "http://localhost:3000/api/chat/completions",
        },
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
async def mock_init_component(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Initialize integration."""
    with patch(
        "aiohttp.ClientSession.get",  # Mock the connection test in async_setup_entry
        return_value=AsyncMock(status=200),
    ):
        assert await async_setup_component(hass, "openwebui_conversation", {})
        await hass.async_block_till_done()


@pytest.fixture(autouse=True)
async def setup_ha(hass: HomeAssistant) -> None:
    """Set up Home Assistant."""
    assert await async_setup_component(hass, "homeassistant", {})