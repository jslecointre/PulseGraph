from typing import Literal, Optional

from langgraph.graph import END
from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt

from email_assistant.chains.long_term_memory_chain import llm_long_term_memory
from email_assistant.consts import RESPONSE_AGENT, TRIAGE_INTERRUPT_HANDLER_NODE
from email_assistant.logger import logger
from email_assistant.persistence.long_term_memory import update_memory
from email_assistant.schemas import EmailAgentState
from email_assistant.utils import (  # noqa F401
    format_email_markdown,
    format_for_display,
    format_gmail_markdown,
    parse_email,
    parse_gmail,
)


async def triage_interrupt_handler_node(
    state: EmailAgentState, use_gmail_tools: bool, store: Optional[BaseStore] = None
) -> Command[Literal["response_agent", "__end__"]]:
    """Handles interrupts from the triage step"""

    if use_gmail_tools:
        logger.info(f"***{TRIAGE_INTERRUPT_HANDLER_NODE} WITH GMAIL TOOLS***")
        # Parse the gmail email input
        author, to, subject, email_thread, email_id = parse_gmail(state["email_input"])
        # Create gmail email markdown for Agent Inbox in case of notification
        email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)
    else:
        logger.info(f"***{TRIAGE_INTERRUPT_HANDLER_NODE} MOCKED TOOLS***")
        # Parse the email input
        author, to, subject, email_thread = parse_email(state["email_input"])
        # Create email markdown for Agent Inbox in case of notification
        email_markdown = format_email_markdown(subject, author, to, email_thread)

    # Create messages
    messages = [{"role": "user", "content": f"Email to notify user about: {email_markdown}"}]

    # Create interrupt for Agent Inbox
    request = {
        "action_request": {"action": f"Email Assistant: {state['classification_decision']}", "args": {}},
        "config": {
            "allow_ignore": True,
            "allow_respond": True,
            "allow_edit": False,
            "allow_accept": False,
        },
        # Email to show in Agent Inbox
        "description": email_markdown,
    }

    # Agent Inbox responds with a list
    response = interrupt([request])[0]

    # If user provides feedback, go to response agent and use feedback to respond to email
    if response["type"] == "response":
        # Add feedback to messages
        user_input = response["args"]
        # Used by the response agent
        messages.append(
            {"role": "user", "content": f"User wants to reply to the email. Use this feedback to respond: {user_input}"}
        )
        if store:
            logger.info(f"***{TRIAGE_INTERRUPT_HANDLER_NODE} UPDATE LONG-TERM MEMORY for triage_preferences***")
            await update_memory(
                store,
                llm_long_term_memory,
                ("email_assistant", "triage_preferences"),
                [
                    {
                        "role": "user",
                        "content": "The user decided to respond to the email, so update the triage preferences to capture this.",  # noqa E501
                    }
                ]
                + messages,
            )

        # Go to response agent
        goto = RESPONSE_AGENT

    # If user ignores email, go to END
    elif response["type"] == "ignore":
        if store:
            logger.info(f"***{TRIAGE_INTERRUPT_HANDLER_NODE} UPDATE LONG-TERM MEMORY for triage_preferences***")
            # Make note of the user's decision to ignore the email
            messages.append(
                {
                    "role": "user",
                    "content": "The user decided to ignore the email even though it was classified as notify. Update triage preferences to capture this.",  # noqa E501
                }
            )
            # This is new: triage_preferences with feedback
            await update_memory(store, llm_long_term_memory, ("email_assistant", "triage_preferences"), messages)

        goto = END

    # Catch all other responses
    else:
        raise ValueError(f"Invalid response: {response}")

    # Update the state
    update = {
        "messages": messages,
    }

    return Command(goto=goto, update=update)
