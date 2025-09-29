from typing import Optional

from langgraph.store.base import BaseStore

from email_assistant.chains.tools_chain import llm_with_tools
from email_assistant.consts import LLM_CALL_NODE, LLM_CALL_NODE_HITL
from email_assistant.logger import logger
from email_assistant.persistence.long_term_memory import get_memory
from email_assistant.prompts import (
    agent_system_prompt,
    default_background,
    default_cal_preferences,
    default_response_preferences,
)
from email_assistant.schemas import EmailAgentState
from email_assistant.tools import get_tools
from email_assistant.tools.default.prompt_templates import (  # noqa F401
    AGENT_TOOLS_PROMPT,
    HITL_TOOLS_PROMPT,
    build_agent_tools_prompt,
)
from email_assistant.tools.gmail.prompt_templates import (  # noqa F401
    COMBINED_TOOLS_PROMPT,
    GMAIL_TOOLS_PROMPT,
)

tools = get_tools()

AGENT_TOOLS_DYNAMIC_PROMPT = build_agent_tools_prompt(tools)


async def llm_call_node(state: EmailAgentState, use_gmail_tools: bool, store: Optional[BaseStore] = None):
    """LLM decides whether to call a tool or not"""
    logger.info(f"***{LLM_CALL_NODE}***")
    SELECTED_AGENT_TOOLS_PROMPT = GMAIL_TOOLS_PROMPT if use_gmail_tools else AGENT_TOOLS_DYNAMIC_PROMPT
    messages = [
        {
            "role": "system",
            "content": agent_system_prompt.format(
                tools_prompt=SELECTED_AGENT_TOOLS_PROMPT,
                background=default_background,
                response_preferences=default_response_preferences,
                cal_preferences=default_cal_preferences,
            ),
        },
    ] + state["messages"]

    res = await llm_with_tools.ainvoke(messages)
    return {"messages": [res]}


async def llm_call_hitl_node(state: EmailAgentState, use_gmail_tools: bool, store: Optional[BaseStore] = None):
    """LLM decides whether to call a tool or not"""
    logger.info(f"***{LLM_CALL_NODE_HITL}***")
    if store:
        # Search for existing cal_preferences memory
        cal_preferences = await get_memory(store, ("email_assistant", "cal_preferences"), default_cal_preferences)

        # Search for existing response_preferences memory
        response_preferences = await get_memory(store, ("email_assistant", "response_preferences"), default_response_preferences)
    else:
        cal_preferences = default_cal_preferences
        response_preferences = default_response_preferences

    SELECTED_HITL_TOOLS_PROMPT = GMAIL_TOOLS_PROMPT if use_gmail_tools else HITL_TOOLS_PROMPT
    messages = [
        {
            "role": "system",
            "content": agent_system_prompt.format(
                tools_prompt=SELECTED_HITL_TOOLS_PROMPT,
                background=default_background,
                response_preferences=response_preferences,
                cal_preferences=cal_preferences,
            ),
        },
    ] + state["messages"]

    res = await llm_with_tools.ainvoke(messages)
    return {"messages": [res]}
