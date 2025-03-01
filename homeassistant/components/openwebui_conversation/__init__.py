"""The Open WebUI Conversation integration."""

from __future__ import annotations

import os
import voluptuous as vol
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import (
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv, selector
from homeassistant.helpers.typing import ConfigType

from .const import (
    DOMAIN,
    LOGGER,
    CONF_OPENWEBUI_API,  # Now API key
    CONF_OPENWEBUI_HOST,  # Now API URL
    CONF_OPENWEBUI_SSL_VERIFY,
    CONF_OPENWEBUI_MODEL,
    CONF_OPENWEBUI_TOKEN,
    CONF_OPENWEBUI_MAX_TOKENS,
    CONF_OPENWEBUI_TEMPERATURE,
    CONF_OPENWEBUI_TOP_P,
    DEFAULT_OPENWEBUI_HOST,  # Updated
    DEFAULT_OPENWEBUI_MODEL,
    DEFAULT_OPENWEBUI_MAX_TOKENS,
    DEFAULT_OPENWEBUI_TEMPERATURE,
    DEFAULT_OPENWEBUI_TOP_P,
)

SERVICE_CHAT_COMPLETION = "chat_completion"
PLATFORMS = (Platform.CONVERSATION,)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type OpenWebUIConfigEntry = ConfigEntry[aiohttp.ClientSession]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up OpenWebUI Conversation."""

    async def handle_chat_completion(call: ServiceCall) -> ServiceResponse:
        """Handle chat completion request."""
        entry_id = call.data["config_entry"]
        entry = hass.config_entries.async_get_entry(entry_id)

        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="invalid_config_entry",
                translation_placeholders={"config_entry": entry_id},
            )

        session: aiohttp.ClientSession = entry.runtime_data
        api_key = entry.data[CONF_OPENWEBUI_API]  # Now API key
        api_url = entry.data.get(CONF_OPENWEBUI_HOST, DEFAULT_OPENWEBUI_HOST)  # Now API URL
        default_model = entry.data.get(CONF_OPENWEBUI_MODEL, DEFAULT_OPENWEBUI_MODEL)
        token = entry.data.get(CONF_OPENWEBUI_TOKEN)
        max_tokens = entry.data.get(CONF_OPENWEBUI_MAX_TOKENS, DEFAULT_OPENWEBUI_MAX_TOKENS)
        temperature = entry.data.get(CONF_OPENWEBUI_TEMPERATURE, DEFAULT_OPENWEBUI_TEMPERATURE)
        top_p = entry.data.get(CONF_OPENWEBUI_TOP_P, DEFAULT_OPENWEBUI_TOP_P)

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        if token:
            headers["Token"] = token

        payload = {
            "model": call.data.get("model", default_model),
            "messages": [{"role": "user", "content": call.data["prompt"]}],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
        }

        try:
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    raise HomeAssistantError(f"API request failed with status: {response.status}")
                result = await response.json()
                return {"response": result}
        except aiohttp.ClientError as err:
            raise HomeAssistantError(f"Error communicating with OpenWebUI: {err}") from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_CHAT_COMPLETION,
        handle_chat_completion,
        schema=vol.Schema(
            {
                vol.Required("config_entry"): selector.ConfigEntrySelector(
                    {"integration": DOMAIN}
                ),
                vol.Required("prompt"): cv.string,
                vol.Optional("model"): cv.string,
            }
        ),
        supports_response=SupportsResponse.ONLY,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OpenWebUIConfigEntry) -> bool:
    """Set up OpenWebUI Conversation from a config entry."""
    api_key = entry.data[CONF_OPENWEBUI_API]  # Now API key
    api_url = entry.data.get(CONF_OPENWEBUI_HOST) or os.getenv("OPENWEBUI_API_URL") or DEFAULT_OPENWEBUI_HOST  # Now API URL
    ssl_verify = entry.data.get(CONF_OPENWEBUI_SSL_VERIFY, True)
    token = entry.data.get(CONF_OPENWEBUI_TOKEN)

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

    entry.runtime_data = session
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload OpenWebUI."""
    session: aiohttp.ClientSession = entry.runtime_data
    await session.close()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)