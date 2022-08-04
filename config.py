#!/usr/bin/env python3

import os
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
secret_client = SecretClient(vault_url="https://chatbot-vault.vault.azure.net/", credential=credential)


class DefaultConfig:
    """ Bot Configuration """

    APP_ID = secret_client.get_secret("MicrosoftAppId", "")
    APP_PASSWORD = os.environ.get("MicrosoftAppPassword", "")
    LUIS_APP_ID = secret_client.get_secret('LuisAppId').value
    LUIS_API_KEY = secret_client.get_secret('LuisAPIKey').value
    LUIS_API_HOST_NAME = secret_client.get_secret('LuisAPIHostName').value
    APPINSIGHTS_INSTRUMENTATIONKEY = secret_client.get_secret('InstrumentationKey').value
