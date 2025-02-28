"""Config flow for OpenWebUI Conversation integration."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant

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

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_OPENWEBUI_API): str,  # Now API key
        vol.Optional(CONF_OPENWEBUI_HOST, default=DEFAULT_OPENWEBUI_HOST): str,  # Now API URL
        vol.Optional(CONF_OPENWEBUI_SSL_VERIFY, default=True): bool,
        vol.Optional(CONF_OPENWEBUI_MODEL, default=DEFAULT_OPENWEBUI_MODEL): str,
        vol.Optional(CONF_OPENWEBUI_TOKEN): str,
        vol.Optional(CONF_OPENWEBUI_MAX_TOKENS, default=DEFAULT_OPENWEBUI_MAX_TOKENS): int,
        vol.Optional(CONF_OPENWEBUI_TEMPERATURE, default=DEFAULT_OPENWEBUI_TEMPERATURE): float,
        vol.Optional(CONF_OPENWEBUI_TOP_P, default=DEFAULT_OPENWEBUI_TOP_P): float,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate the user input allows us to connect."""
    api_url = data[CONF_OPENWEBUI_HOST]  # Now API URL
    api_key = data[CONF_OPENWEBUI_API]  # Now API key
    token = data.get(CONF_OPENWEBUI_TOKEN)
    ssl_verify = data[CONF_OPENWEBUI_SSL_VERIFY]

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if token:
        headers["Token"] = token

    async with aiohttp.ClientSession(
        headers=headers,
        connector=aiohttp.TCPConnector(verify_ssl=ssl_verify),
    ) as session:
        try:
            async with session.get(api_url) as response:
                if response.status == 401:
                    raise ValueError("Invalid API key or token")
                if response.status != 200:
                    raise ValueError(f"Failed to connect: {response.status}")
        except aiohttp.ClientError as err:
            raise ValueError(f"Connection error: {err}") from err


class OpenWebUIConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenWebUI Conversation."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        try:
            await validate_input(self.hass, user_input)
        except ValueError as err:
            errors["base"] = str(err)
        except Exception:
            LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(
                title="OpenWebUI",
                data=user_input,
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Create the options flow."""
        return OpenWebUIOptionsFlow(config_entry)


class OpenWebUIOptionsFlow(OptionsFlow):
    """OpenWebUI config flow options handler."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.data | self.config_entry.options
        schema = openwebui_config_option_schema(options)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema),
        )


def openwebui_config_option_schema(
    options: dict[str, Any] | MappingProxyType[str, Any],
) -> dict:
    """Return a schema for OpenWebUI options."""
    return {
        vol.Required(
            CONF_OPENWEBUI_API,  # Now API key
            default=options.get(CONF_OPENWEBUI_API),
        ): str,
        vol.Optional(
            CONF_OPENWEBUI_HOST,  # Now API URL
            default=options.get(CONF_OPENWEBUI_HOST, DEFAULT_OPENWEBUI_HOST),
        ): str,
        vol.Optional(
            CONF_OPENWEBUI_SSL_VERIFY,
            default=options.get(CONF_OPENWEBUI_SSL_VERIFY, True),
        ): bool,
        vol.Optional(
            CONF_OPENWEBUI_MODEL,
            default=options.get(CONF_OPENWEBUI_MODEL, DEFAULT_OPENWEBUI_MODEL),
        ): str,
        vol.Optional(
            CONF_OPENWEBUI_TOKEN,
            default=options.get(CONF_OPENWEBUI_TOKEN, ""),
        ): str,
        vol.Optional(
            CONF_OPENWEBUI_MAX_TOKENS,
            default=options.get(CONF_OPENWEBUI_MAX_TOKENS, DEFAULT_OPENWEBUI_MAX_TOKENS),
        ): int,
        vol.Optional(
            CONF_OPENWEBUI_TEMPERATURE,
            default=options.get(CONF_OPENWEBUI_TEMPERATURE, DEFAULT_OPENWEBUI_TEMPERATURE),
        ): vol.All(vol.Coerce(float), vol.Range(min=0, max=2)),
        vol.Optional(
            CONF_OPENWEBUI_TOP_P,
            default=options.get(CONF_OPENWEBUI_TOP_P, DEFAULT_OPENWEBUI_TOP_P),
        ): vol.All(vol.Coerce(float), vol.Range(min=0, max=1)),
    }