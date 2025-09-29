from typing import Literal, Optional

from langgraph.store.base import BaseStore

from email_assistant.consts import MARK_EMAIL_AS_READ_NODE, TOOL_HANDLER_NODE
from email_assistant.logger import logger
from email_assistant.schemas import EmailAgentState
from email_assistant.tools import get_tools, get_tools_by_name

# Get tools
tools = get_tools()
tools_by_name = get_tools_by_name(tools)


# Conditional edge function
def should_call_tool(state: EmailAgentState, store: Optional[BaseStore] = None) -> Literal["Action", "mark_as_read_node"]:
    """Route to Action, or end if Done tool called"""
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            if tool_call["name"] == "Done":
                # TODO: Here, we could update the background memory with the email-response for follow up actions.
                return MARK_EMAIL_AS_READ_NODE
            else:
                return "Action"  # could be interrupt_handler (hitl) or tool_handler (no hitl)


async def tool_handler_node(state: EmailAgentState):
    """Performs the tool call"""

    result = []
    # Iterate over the tool calls in the last message
    logger.info(f"***{TOOL_HANDLER_NODE}***")
    for tool_call in state["messages"][-1].tool_calls:
        tool = tools_by_name[tool_call["name"]]
        observation = await tool.ainvoke(tool_call["args"])
        result.append({"role": "tool", "content": observation, "tool_call_id": tool_call["id"]})
        logger.info(f"***{TOOL_HANDLER_NODE} result {observation}***")
    return {"messages": result}
