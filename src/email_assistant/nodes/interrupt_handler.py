from typing import Literal, Optional

from langgraph.graph import END
from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt

from email_assistant.chains.long_term_memory_chain import llm_long_term_memory
from email_assistant.consts import INTERRUPT_HANDLER_NODE, LLM_CALL_NODE_HITL
from email_assistant.logger import logger
from email_assistant.persistence.long_term_memory import update_memory
from email_assistant.prompts import MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT
from email_assistant.schemas import EmailAgentState
from email_assistant.tools import check_calendar_tool  # GMAIL
from email_assistant.tools import fetch_emails_tool  # GMAIL
from email_assistant.tools import schedule_meeting_tool  # GMAIL
from email_assistant.tools import send_email_tool  # GMAIL
from email_assistant.tools import triage_email  # GMAIL
from email_assistant.tools import (
    Done,
    Question,
    check_calendar_availability,
    schedule_meeting,
    write_email,
)
from email_assistant.utils import (
    format_email_markdown,
    format_for_display,
    format_gmail_markdown,
    parse_email,
    parse_gmail,
)


async def interrupt_handler_node(
    state: EmailAgentState, use_gmail_tools: bool, store: Optional[BaseStore] = None
) -> Command[Literal["llm_call_hitl", "__end__"]]:
    """Creates an interrupt for human review of tool calls"""
    logger.info(f"***{INTERRUPT_HANDLER_NODE}***")
    # Store messages
    result = []
    if use_gmail_tools:
        tools = [fetch_emails_tool, send_email_tool, check_calendar_tool, schedule_meeting_tool, triage_email, Done]
        hitl_tools = ["send_email_tool", "schedule_meeting_tool", "Question"]
    else:
        tools = [write_email, schedule_meeting, check_calendar_availability, Question, Done]
        hitl_tools = ["write_email", "schedule_meeting", "Question"]

    tools_by_name = {tool.name: tool for tool in tools}
    # Go to the LLM call node next
    goto = LLM_CALL_NODE_HITL
    logger.info(f"***{INTERRUPT_HANDLER_NODE} MESSAGE LENGTH {len(state['messages'])}***")
    # Iterate over the tool calls in the last message
    for tool_call in state["messages"][-1].tool_calls:
        # Allowed tools for HITL

        # If tool is not in our HITL list, execute it directly without interruption
        if tool_call["name"] not in hitl_tools:
            # Execute tool without interruption
            tool = tools_by_name[tool_call["name"]]
            observation = await tool.ainvoke(tool_call["args"])
            result.append({"role": "tool", "content": observation, "tool_call_id": tool_call["id"]})
            continue

        # Get original email from email_input in state
        email_input = state["email_input"]
        if use_gmail_tools:
            author, to, subject, email_thread, email_id = parse_gmail(email_input)
            original_email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)
        else:
            author, to, subject, email_thread = parse_email(email_input)
            original_email_markdown = format_email_markdown(subject, author, to, email_thread)

        # Format tool call for display and prepend the original email
        tool_display = format_for_display(tool_call)
        description = original_email_markdown + tool_display

        # Configure what actions are allowed in Agent Inbox
        if tool_call["name"] in ["write_email", "send_email_tool"]:
            config = {
                "allow_ignore": True,
                "allow_respond": True,
                "allow_edit": True,
                "allow_accept": True,
            }
        elif tool_call["name"] in ["schedule_meeting", "schedule_meeting_tool"]:
            config = {
                "allow_ignore": True,
                "allow_respond": True,
                "allow_edit": True,
                "allow_accept": True,
            }
        elif tool_call["name"] == "Question":
            config = {
                "allow_ignore": True,
                "allow_respond": True,
                "allow_edit": False,
                "allow_accept": False,
            }
        else:
            raise ValueError(f"Invalid tool call: {tool_call['name']}")

        # Create the interrupt request
        request = {
            "action_request": {"action": tool_call["name"], "args": tool_call["args"]},
            "config": config,
            "description": description,
        }

        # Send to Agent Inbox and wait for response
        response = interrupt([request])[0]

        # Handle the responses
        if response["type"] == "accept":
            # Execute the tool with original args
            tool = tools_by_name[tool_call["name"]]
            observation = await tool.ainvoke(tool_call["args"])
            result.append({"role": "tool", "content": observation, "tool_call_id": tool_call["id"]})

        elif response["type"] == "edit":
            # Tool selection
            tool = tools_by_name[tool_call["name"]]
            initial_tool_call = tool_call["args"]
            # Get edited args from Agent Inbox
            edited_args = response["args"]["args"]

            # Update the AI message's tool call with edited content (reference to the message in the state)
            ai_message = state["messages"][-1]  # Get the most recent message from the state
            current_id = tool_call["id"]  # Store the ID of the tool call being edited

            # Create a new list of tool calls by filtering out the one being edited and adding the updated version
            # This avoids modifying the original list directly (immutable approach)
            updated_tool_calls = [tc for tc in ai_message.tool_calls if tc["id"] != current_id] + [
                {"type": "tool_call", "name": tool_call["name"], "args": edited_args, "id": current_id}
            ]

            # Create a new copy of the message with updated tool calls rather than modifying the original
            # This ensures state immutability and prevents side effects in other parts of the code
            # When we update the messages state key ("messages": result), the add_messages reducer will
            # overwrite existing messages by id and we take advantage of this here to update the tool calls.
            result.append(ai_message.model_copy(update={"tool_calls": updated_tool_calls}))

            # Update the write_email tool call with the edited content from Agent Inbox
            if tool_call["name"] in ["write_email", "send_email_tool"]:
                # Execute the tool with edited args
                observation = tool.invoke(edited_args)

                # Add only the tool response message
                result.append({"role": "tool", "content": observation, "tool_call_id": current_id})

                if store:
                    # This is new: update the memory
                    logger.info(f"***{INTERRUPT_HANDLER_NODE} update long-term memory for edit to write_email ***")
                    await update_memory(
                        store,
                        llm_long_term_memory,
                        ("email_assistant", "response_preferences"),
                        [
                            {
                                "role": "user",
                                "content": f"User edited the email response. Here is the initial email generated by the assistant: {initial_tool_call}. Here is the edited email: {edited_args}. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}.",  # noqa E501
                            }
                        ],
                    )

            # Update the schedule_meeting tool call with the edited content from Agent Inbox
            elif tool_call["name"] in ["schedule_meeting", "schedule_meeting_tool"]:
                # Execute the tool with edited args
                observation = await tool.ainvoke(edited_args)

                # Add only the tool response message
                result.append({"role": "tool", "content": observation, "tool_call_id": current_id})

                if store:
                    logger.info(f"***{INTERRUPT_HANDLER_NODE} update long-term memory for edit to schedule_meeting ***")
                    await update_memory(
                        store,
                        llm_long_term_memory,
                        ("email_assistant", "cal_preferences"),
                        [
                            {
                                "role": "user",
                                "content": f"User edited the calendar invitation. Here is the initial calendar invitation generated by the assistant: {initial_tool_call}. Here is the edited calendar invitation: {edited_args}. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}.",  # noqa E501
                            }
                        ],
                    )

            # Catch all other tool calls
            else:
                raise ValueError(f"Invalid tool call: {tool_call['name']}")

        elif response["type"] == "ignore":
            if tool_call["name"] in ["write_email", "send_email_tool"]:
                # Don't execute the tool, and tell the agent how to proceed
                result.append(
                    {
                        "role": "tool",
                        "content": "User ignored this email draft. Ignore this email and end the workflow.",
                        "tool_call_id": tool_call["id"],
                    }
                )
                # Go to END
                goto = END

                if store:
                    logger.info(f"***{INTERRUPT_HANDLER_NODE} update long-term memory for ignore to write_email ***")
                    await update_memory(
                        store,
                        llm_long_term_memory,
                        ("email_assistant", "triage_preferences"),
                        state["messages"]
                        + result
                        + [
                            {
                                "role": "user",
                                "content": f"The user ignored the email draft. That means they did not want to respond to the email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}.",  # noqa E501
                            }
                        ],
                    )

            elif tool_call["name"] in ["schedule_meeting", "schedule_meeting_tool"]:
                # Don't execute the tool, and tell the agent how to proceed
                result.append(
                    {
                        "role": "tool",
                        "content": "User ignored this calendar meeting draft. Ignore this email and end the workflow.",
                        "tool_call_id": tool_call["id"],
                    }
                )
                # Go to END
                goto = END

                if store:
                    logger.info(f"***{INTERRUPT_HANDLER_NODE} update long-term memory for ignore to schedule_meeting ***")
                    await update_memory(
                        store,
                        llm_long_term_memory,
                        ("email_assistant", "triage_preferences"),
                        state["messages"]
                        + result
                        + [
                            {
                                "role": "user",
                                "content": f"The user ignored the calendar meeting draft. That means they did not want to schedule a meeting for this email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}.",  # noqa E501
                            }
                        ],
                    )

            elif tool_call["name"] == "Question":
                # Don't execute the tool, and tell the agent how to proceed
                result.append(
                    {
                        "role": "tool",
                        "content": "User ignored this question. Ignore this email and end the workflow.",
                        "tool_call_id": tool_call["id"],
                    }
                )
                # Go to END
                goto = END
                if store:
                    logger.info(f"***{INTERRUPT_HANDLER_NODE} update long-term memory for ignore Question ***")
                    await update_memory(
                        store,
                        llm_long_term_memory,
                        ("email_assistant", "triage_preferences"),
                        state["messages"]
                        + result
                        + [
                            {
                                "role": "user",
                                "content": f"The user ignored the Question. That means they did not want to answer the question or deal with this email. Update the triage preferences to ensure emails of this type are not classified as respond. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}.",  # noqa E501
                            }
                        ],
                    )

            else:
                raise ValueError(f"Invalid tool call: {tool_call['name']}")

        elif response["type"] == "response":
            # User provided feedback
            user_feedback = response["args"]
            if tool_call["name"] in ["write_email", "send_email_tool"]:
                # Don't execute the tool, and add a message with the user feedback to incorporate into the email
                result.append(
                    {
                        "role": "tool",
                        "content": f"User gave feedback, which can we incorporate into the email. Feedback: {user_feedback}",
                        "tool_call_id": tool_call["id"],
                    }
                )

                if store:
                    logger.info(f"***{INTERRUPT_HANDLER_NODE} update long-term memory for response to write_email ***")
                    await update_memory(
                        store,
                        llm_long_term_memory,
                        ("email_assistant", "response_preferences"),
                        state["messages"]
                        + result
                        + [
                            {
                                "role": "user",
                                "content": f"User gave feedback, which we can use to update the response preferences. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}.",  # noqa E501
                            }
                        ],
                    )

            elif tool_call["name"] in ["schedule_meeting", "schedule_meeting_tool"]:
                # Don't execute the tool, and add a message with the user feedback to incorporate into the email
                result.append(
                    {
                        "role": "tool",
                        "content": f"User gave feedback, which can we incorporate into the meeting request. Feedback: {user_feedback}",  # noqa E501
                        "tool_call_id": tool_call["id"],
                    }
                )

                if store:
                    logger.info(f"***{INTERRUPT_HANDLER_NODE} update long-term memory for response to schedule_meeting ***")
                    await update_memory(
                        store,
                        llm_long_term_memory,
                        ("email_assistant", "cal_preferences"),
                        state["messages"]
                        + result
                        + [
                            {
                                "role": "user",
                                "content": f"User gave feedback, which we can use to update the calendar preferences. Follow all instructions above, and remember: {MEMORY_UPDATE_INSTRUCTIONS_REINFORCEMENT}.",  # noqa E501
                            }
                        ],
                    )

            elif tool_call["name"] == "Question":
                # Don't execute the tool, and add a message with the user feedback to incorporate into the email
                result.append(
                    {
                        "role": "tool",
                        "content": f"User answered the question, which can we can use for any follow up actions. Feedback: {user_feedback}",  # noqa E501
                        "tool_call_id": tool_call["id"],
                    }
                )
            else:
                raise ValueError(f"Invalid tool call: {tool_call['name']}")

        # Catch all other responses
        else:
            raise ValueError(f"Invalid response: {response}")

    # Update the state
    update = {
        "messages": result,
    }

    return Command(goto=goto, update=update)
