"""Define the configurable parameters for the agent."""

import os
from dataclasses import dataclass, fields
from typing import Any, Optional

from langchain_core.runnables import RunnableConfig

from email_assistant.utils import str_to_bool


@dataclass(kw_only=True)
class Configuration:
    """Configuration class for the email assistant agent."""

    use_gmail: bool = False
    """Whether to use Gmail tools instead of default email tools."""

    @classmethod
    def from_runnable_config(cls, config: Optional[RunnableConfig] = None) -> "Configuration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = config["configurable"] if config and "configurable" in config else {}

        use_gmail_env = os.environ.get("USE_GMAIL", "False")
        try:
            use_gmail = str_to_bool(use_gmail_env)
        except ValueError as e:
            print(f"Warning: Invalid USE_GMAIL value '{use_gmail_env}'. Using default False. Error: {e}")
            use_gmail = False

        values: dict[str, Any] = {
            "use_gmail": use_gmail,
        }

        for f in fields(cls):
            if f.init and f.name != "use_gmail":
                env_value = os.environ.get(f.name.upper())
                config_value = configurable.get(f.name)
                if env_value is not None:
                    values[f.name] = env_value
                elif config_value is not None:
                    values[f.name] = config_value

        return cls(**{k: v for k, v in values.items() if v is not None})

    @classmethod
    def from_env(cls) -> "Configuration":
        """Create a Configuration instance from environment variables only."""
        return cls.from_runnable_config(None)
