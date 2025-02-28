"""Test the OpenWebUI Conversation config flow."""

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from homeassistant import config_entries
from homeassistant.components.openwebui_conversation.const import (
    DOMAIN,
    CONF_OPENWEBUI_API,
    CONF_OPENWEBUI_HOST,
    DEFAULT_OPENWEBUI_HOST,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_form(hass: HomeAssistant) -> None:
    """Test we get the form."""
    # Pretend we already set up a config entry.
    hass.config.components.add("openwebui_conversation")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] is None

    with (
        patch(
            "aiohttp.ClientSession.get",
            return_value=AsyncMock(status=200),
        ),
        patch(
            "homeassistant.components.openwebui_conversation.async_setup_entry",
            return_value=True,
        ) as mock_setup_entry,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "openwebui_api": "test-key",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"] == {
        "openwebui_api": "test-key",
        "openwebui_host": DEFAULT_OPENWEBUI_HOST,
        "openwebui_ssl_verify": True,
        "openwebui_model": "llama3.1",
        "openwebui_max_tokens": 1000,
        "openwebui_temperature": 0.7,
        "openwebui_top_p": 0.9,
    }
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    ("side_effect", "error"),
    [
        (aiohttp.ClientConnectionError(), "cannot_connect"),
        (aiohttp.ClientResponseError(status=401, request_info=None, history=()), "invalid_auth"),
        (aiohttp.ClientResponseError(status=400, request_info=None, history=()), "unknown"),
    ],
)
async def test_form_errors(hass: HomeAssistant, side_effect, error) -> None:
    """Test we handle connection/auth errors."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    with patch(
        "aiohttp.ClientSession.get",
        side_effect=side_effect,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "openwebui_api": "test-key",
            },
        )

    assert result2["type"] is FlowResultType.FORM
    assert result2["errors"] == {"base": error}