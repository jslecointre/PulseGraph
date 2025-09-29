from typing import Literal

from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from src.email_assistant.chains import wx_credentials


class RouterSchema(BaseModel):
    """Analyze the unread email and route it according to its content."""

    reasoning: str = Field(description="Step-by-step reasoning behind the classification.")
    classification: Literal["ignore", "respond", "notify"] = Field(
        description="The classification of an email: 'ignore' for irrelevant emails, "
        "'notify' for important information that doesn't need a response, "
        "'respond' for emails that need a reply",
    )


model_name = "openai:gpt-4.1"
# model_name = "ibm:meta-llama/llama-3-3-70b-instruct"
# model_name = "ibm:ibm/granite-3-3-8b-instruct"
# model_name = "ollama:granite3.3:8b"
# model_name = "ollama:gpt-oss:20b"

# Initialize the LLM for use with router / structured output
if model_name.startswith("ibm:"):
    from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

    params = TextChatParameters(max_tokens=100, temperature=0.0, seed=122)
    llm = init_chat_model(model=model_name, params=params, **wx_credentials)
elif model_name.startswith("openai:"):
    llm = init_chat_model(model=model_name, temperature=0.0)
elif model_name.startswith("ollama:"):
    llm = init_chat_model(model=model_name, temperature=0.0, seed=122, num_predict=100)
else:
    raise ValueError(f"Unknown model: {model_name}")


llm_router = llm.with_config({"tags": ["triage_decision"]}).with_structured_output(RouterSchema)
