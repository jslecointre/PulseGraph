from langchain.chat_models import init_chat_model

from email_assistant.config import USE_GMAIL
from email_assistant.tools import get_tools
from src.email_assistant.chains import wx_credentials

# Get tools
if USE_GMAIL:
    tools = get_tools(["send_email_tool", "schedule_meeting_tool", "check_calendar_tool", "Question", "Done"], include_gmail=True)
else:
    tools = get_tools()

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
    tool_choice = "required" if USE_GMAIL else "any"
elif model_name.startswith("ollama:"):
    llm = init_chat_model(model=model_name, temperature=0.0, seed=122, num_predict=1000)
    tool_choice = "auto"
else:
    raise ValueError(f"Unknown model: {model_name}")


llm_with_tools = llm.bind_tools(tools, tool_choice=tool_choice)
