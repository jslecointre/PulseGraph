from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from src.email_assistant.chains import wx_credentials


class UserPreferences(BaseModel):
    """Updated user preferences based on user's feedback."""

    chain_of_thought: str = Field(description="Reasoning about which user preferences need to add / update if required")
    user_preferences: str = Field(description="Updated user preferences")


model_name = "openai:gpt-4.1"
# model_name = "ibm:meta-llama/llama-3-3-70b-instruct"
# model_name = "ibm:ibm/granite-3-3-8b-instruct"
# model_name = "ollama:granite3.3:8b"
# model_name = "ollama:gpt-oss:20b"

if model_name.startswith("ibm:"):
    # from langchain_ibm import ChatWatsonx
    from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

    params = TextChatParameters(max_tokens=500, temperature=0.0, seed=122)
    llm = init_chat_model(model=model_name, params=params, **wx_credentials)
    tool_choice = "auto"
elif model_name.startswith("openai:"):
    llm = init_chat_model(model=model_name, temperature=0.0)
    tool_choice = "any"
elif model_name.startswith("ollama:"):
    llm = init_chat_model(model=model_name, temperature=0.0, seed=122, num_predict=1000)
    tool_choice = "auto"
else:
    raise ValueError(f"Unknown model: {model_name}")


llm_long_term_memory = llm.with_config({"tags": ["long_term_memory_update"]}).with_structured_output(UserPreferences)
