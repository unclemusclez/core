"""Constants for the OpenWebUI Conversation integration."""

import logging

DOMAIN = "openwebui_conversation"
LOGGER = logging.getLogger(__package__)

# Configuration keys
CONF_OPENWEBUI_API = "openwebui_api"  # Now used for API key
CONF_OPENWEBUI_HOST = "openwebui_host"  # Now used for API URL
CONF_OPENWEBUI_SSL_VERIFY = "openwebui_ssl_verify"
CONF_OPENWEBUI_MODEL = "openwebui_model"
CONF_OPENWEBUI_TOKEN = "openwebui_token"
CONF_OPENWEBUI_MAX_TOKENS = "openwebui_max_tokens"
CONF_OPENWEBUI_TEMPERATURE = "openwebui_temperature"
CONF_OPENWEBUI_TOP_P = "openwebui_top_p"

# Default values
DEFAULT_OPENWEBUI_HOST = "http://localhost:3000/api/chat/completions"  # Renamed from DEFAULT_OPENWEBUI_API
DEFAULT_OPENWEBUI_MODEL = "llama3.1"
DEFAULT_OPENWEBUI_MAX_TOKENS = 1000
DEFAULT_OPENWEBUI_TEMPERATURE = 0.7
DEFAULT_OPENWEBUI_TOP_P = 0.9