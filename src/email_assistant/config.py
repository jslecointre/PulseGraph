"""Centralized configuration loader for the email assistant."""

from email_assistant.configuration import Configuration

config = Configuration.from_env()

USE_GMAIL = config.use_gmail

__all__ = ["config", "USE_GMAIL"]
