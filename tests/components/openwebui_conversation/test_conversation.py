"""Tests for the OpenWebUI Conversation integration."""

from unittest.mock import AsyncMock, patch

import aiohttp
from syrupy.assertion import SnapshotAssertion
import pytest

from homeassistant.components import conversation
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import intent

from tests.common import MockConfigEntry


async def test_entity(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_init_component,
) -> None:
    """Test entity properties."""
    state = hass.states.get("conversation.openwebui_chat")
    assert state
    assert state.attributes["supported_features"] == 0  # No CONTROL feature without tools


async def test_error_handling(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry, mock_init_component
) -> None:
    """Test error handling in conversation."""
    with patch(
        "aiohttp.ClientSession.post",
        side_effect=aiohttp.ClientError,
    ):
        result = await conversation.async_converse(
            hass, "hello", None, Context(), agent_id=mock_config_entry.entry_id
        )

    assert result.response.response_type == intent.IntentResponseType.ERROR
    assert result.response.error_code == "unknown"


async def test_conversation(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_init_component,
) -> None:
    """Test basic conversation."""
    with patch(
        "aiohttp.ClientSession.post",
        return_value=AsyncMock(
            status=200,
            json=AsyncMock(
                return_value={
                    "choices": [{"message": {"content": "Hello back!"}}]
                }
            ),
        ),
    ) as mock_post:
        result = await conversation.async_converse(
            hass, "hello", None, Context(), agent_id=mock_config_entry.entry_id
        )

    assert result.response.response_type == intent.IntentResponseType.ACTION_DONE
    assert result.response.speech["plain"]["speech"] == "Hello back!"
    assert mock_post.called
    assert mock_post.call_args[1]["json"]["messages"][-1] == {
        "role": "user",
        "content": "hello",
    }


async def test_conversation_id(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_init_component,
) -> None:
    """Test conversation ID persistence."""
    with patch(
        "aiohttp.ClientSession.post",
        return_value=AsyncMock(
            status=200,
            json=AsyncMock(
                return_value={
                    "choices": [{"message": {"content": "First response"}}]
                }
            ),
        ),
    ):
        result = await conversation.async_converse(
            hass, "hello", None, None, agent_id=mock_config_entry.entry_id
        )
        conv_id = result.conversation_id

    with patch(
        "aiohttp.ClientSession.post",
        return_value=AsyncMock(
            status=200,
            json=AsyncMock(
                return_value={
                    "choices": [{"message": {"content": "Second response"}}]
                }
            ),
        ),
    ):
        result = await conversation.async_converse(
            hass, "hi again", conv_id, None, agent_id=mock_config_entry.entry_id
        )

    assert result.conversation_id == conv_id
    assert result.response.speech["plain"]["speech"] == "Second response"