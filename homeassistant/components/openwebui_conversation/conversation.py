"""The Open WebUI Conversation integration."""

from __future__ import annotations

import json
import aiohttp
import voluptuous as vol

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import ulid

from .const import (
    DOMAIN,
    LOGGER,
    CONF_OPENWEBUI_API,
    CONF_OPENWEBUI_HOST,
    CONF_OPENWEBUI_SSL_VERIFY,
    CONF_OPENWEBUI_MODEL,
    CONF_OPENWEBUI_TOKEN,
    CONF_OPENWEBUI_MAX_TOKENS,
    CONF_OPENWEBUI_TEMPERATURE,
    CONF_OPENWEBUI_TOP_P,
    DEFAULT_OPENWEBUI_HOST,
    DEFAULT_OPENWEBUI_MODEL,
    DEFAULT_OPENWEBUI_MAX_TOKENS,
    DEFAULT_OPENWEBUI_TEMPERATURE,
    DEFAULT_OPENWEBUI_TOP_P,
)

PLATFORMS = (Platform.CONVERSATION,)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OpenWebUIConfigEntry = ConfigEntry[aiohttp.ClientSession]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: OpenWebUIConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up conversation entities."""
    agent = OpenWebUIConversationEntity(config_entry)
    async_add_entities([agent])


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up OpenWebUI Conversation."""
    # No additional service setup needed since conversation entity handles it
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenWebUI."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


class OpenWebUIConversationEntity(conversation.ConversationEntity):
    """OpenWebUI conversation agent."""

    _attr_has_entity_name = True
    _attr_name = "OpenWebUI Chat"

    def __init__(self, entry: OpenWebUIConfigEntry) -> None:
        """Initialize the agent."""
        self.entry = entry
        self.history: dict[str, list[dict]] = {}
        self._attr_unique_id = entry.entry_id
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "OpenWebUI",
            "model": "Chat",
            "entry_type": "service",
        }

    @property
    def supported_languages(self) -> list[str] | str:
        """Return a list of supported languages."""
        return MATCH_ALL

    async def async_added_to_hass(self) -> None:
        """When entity is added to Home Assistant."""
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)
        self.entry.async_on_unload(
            self.entry.add_update_listener(self._async_entry_update_listener)
        )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from Home Assistant."""
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def async_setup_entry(self) -> bool:
        """Set up OpenWebUI Conversation from a config entry."""
        api_key = self.entry.data[CONF_OPENWEBUI_API]
        api_url = self.entry.data.get(CONF_OPENWEBUI_HOST) or DEFAULT_OPENWEBUI_HOST
        ssl_verify = self.entry.data.get(CONF_OPENWEBUI_SSL_VERIFY, True)
        token = self.entry.data.get(CONF_OPENWEBUI_TOKEN)

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if token:
            headers["Token"] = token

        session = aiohttp.ClientSession(
            headers=headers,
            connector=aiohttp.TCPConnector(verify_ssl=ssl_verify),
        )

        try:
            async with session.get(api_url) as response:
                if response.status == 401:
                    LOGGER.error("Invalid API key or token")
                    await session.close()
                    return False
                if response.status != 200:
                    raise ConfigEntryNotReady(f"Failed to connect: {response.status}")
        except aiohttp.ClientError as err:
            await session.close()
            raise ConfigEntryNotReady(err) from err

        self.entry.runtime_data = session
        return True

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        """Process a sentence."""
        api_key = self.entry.data[CONF_OPENWEBUI_API]
        api_url = self.entry.data.get(CONF_OPENWEBUI_HOST, DEFAULT_OPENWEBUI_HOST)
        default_model = self.entry.data.get(CONF_OPENWEBUI_MODEL, DEFAULT_OPENWEBUI_MODEL)
        token = self.entry.data.get(CONF_OPENWEBUI_TOKEN)
        max_tokens = self.entry.data.get(CONF_OPENWEBUI_MAX_TOKENS, DEFAULT_OPENWEBUI_MAX_TOKENS)
        temperature = self.entry.data.get(CONF_OPENWEBUI_TEMPERATURE, DEFAULT_OPENWEBUI_TEMPERATURE)
        top_p = self.entry.data.get(CONF_OPENWEBUI_TOP_P, DEFAULT_OPENWEBUI_TOP_P)

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if token:
            headers["Token"] = token

        if user_input.conversation_id in self.history:
            conversation_id = user_input.conversation_id
            messages = self.history[conversation_id]
        else:
            conversation_id = ulid.ulid_now()
            messages = []

        messages.append({"role": "user", "content": user_input.text})

        payload = {
            "model": default_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        session = self.entry.runtime_data

        try:
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    raise HomeAssistantError(f"API request failed with status: {response.status}")
                result = await response.json()
                response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        except aiohttp.ClientError as err:
            LOGGER.error("Error communicating with OpenWebUI: %s", err)
            intent_response = conversation.intent.IntentResponse(language=user_input.language)
            intent_response.async_set_error(
                conversation.intent.IntentResponseErrorCode.UNKNOWN,
                "Sorry, I had a problem talking to OpenWebUI",
            )
            return conversation.ConversationResult(
                response=intent_response, conversation_id=conversation_id
            )

        messages.append({"role": "assistant", "content": response_text})
        self.history[conversation_id] = messages

        intent_response = conversation.intent.IntentResponse(language=user_input.language)
        intent_response.async_set_speech(response_text)
        return conversation.ConversationResult(
            response=intent_response, conversation_id=conversation_id
        )

    async def _async_entry_update_listener(
        self, hass: HomeAssistant, entry: ConfigEntry
    ) -> None:
        """Handle options update."""
        await hass.config_entries.async_reload(entry.entry_id)