from langchain.chat_models import init_chat_model
from pydantic import BaseModel, Field

from src.email_assistant.chains import wx_credentials


class CriteriaGrade(BaseModel):
    """Score the response against specific criteria."""

    justification: str = Field(
        description="The justification for the grade and score, including specific examples from the response."
    )
    grade: bool = Field(description="Does the response meet the provided criteria?")


model_name = "openai:gpt-4.1"
# model_name = "ibm:meta-llama/llama-3-3-70b-instruct"
# model_name = "ibm:ibm/granite-3-3-8b-instruct"
# model_name = "ollama:granite3.3:8b"
# model_name = "ollama:gpt-oss:20b"

criteria_eval_llm = init_chat_model("openai:gpt-4o")

if model_name.startswith("ibm:"):
    # from langchain_ibm import ChatWatsonx
    from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

    params = TextChatParameters(max_tokens=500, temperature=0.0, seed=122)
    criteria_eval_llm = init_chat_model(model=model_name, params=params, **wx_credentials)
elif model_name.startswith("openai:"):
    criteria_eval_llm = init_chat_model(model=model_name, temperature=0.0)
elif model_name.startswith("ollama:"):
    criteria_eval_llm = init_chat_model(model=model_name, temperature=0.0, seed=122, num_predict=1000)
else:
    raise ValueError(f"Unknown model: {model_name}")


criteria_eval_structured_llm = criteria_eval_llm.with_structured_output(CriteriaGrade)
