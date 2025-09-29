from typing import Literal, Optional

from langgraph.graph import END
from langgraph.store.base import BaseStore
from langgraph.types import Command

from email_assistant.chains.triage_chain import llm_router
from email_assistant.consts import (
    EMAIL_AGENT,
    RESPONSE_AGENT,
    TRIAGE_INTERRUPT_HANDLER_NODE,
    TRIAGE_ROUTER_HITL_NODE,
    TRIAGE_ROUTER_NODE,
)
from email_assistant.logger import logger
from email_assistant.persistence.long_term_memory import get_memory
from email_assistant.prompts import (
    default_background,
    default_triage_instructions,
    triage_system_prompt,
    triage_user_prompt,
)
from email_assistant.schemas import EmailAgentState
from email_assistant.utils import format_for_display  # noqa F401
from email_assistant.utils import (
    format_email_markdown,
    format_gmail_markdown,
    parse_email,
    parse_gmail,
)


async def triage_router_node(state: EmailAgentState) -> Command[Literal["email_agent", "__end__"]]:
    """Analyze email content to decide if we should respond, notify, or ignore."""
    logger.info(f"***{TRIAGE_ROUTER_NODE}***")
    author, to, subject, email_thread = parse_email(state["email_input"])
    system_prompt = triage_system_prompt.format(background=default_background, triage_instructions=default_triage_instructions)

    user_prompt = triage_user_prompt.format(author=author, to=to, subject=subject, email_thread=email_thread)

    result = await llm_router.ainvoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    if result.classification == "respond":
        logger.info(f"{TRIAGE_ROUTER_NODE} Classification: RESPOND - This email requires a response")
        goto = EMAIL_AGENT
        update = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Respond to the email: \n\n{format_email_markdown(subject, author, to, email_thread)}",
                }
            ],
            "classification_decision": result.classification,
        }

    elif result.classification == "ignore":
        logger.info(f"{TRIAGE_ROUTER_NODE} Classification: IGNORE - This email can be safely ignored")
        goto = END
        update = {
            "classification_decision": result.classification,
        }

    elif result.classification == "notify":
        logger.info(f"{TRIAGE_ROUTER_NODE} Classification: NOTIFY - This email contains important information")
        # For now, we go to END. But we will add to this later!
        goto = END
        update = {
            "classification_decision": result.classification,
        }

    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    logger.info(f"***{TRIAGE_ROUTER_NODE} ended***")
    return Command(goto=goto, update=update)


async def triage_router_hitl_node(
    state: EmailAgentState, use_gmail_tools: bool, store: Optional[BaseStore] = None
) -> Command[Literal["triage_interrupt_handler", "response_agent", "__end__"]]:
    """Analyze email content to decide if we should respond, notify, or ignore."""
    logger.info(f"***{TRIAGE_ROUTER_HITL_NODE}***")
    if use_gmail_tools:
        author, to, subject, email_thread, email_id = parse_gmail(state["email_input"])
        # Create email markdown for Agent Inbox in case of notification
        email_markdown = format_gmail_markdown(subject, author, to, email_thread, email_id)
    else:
        author, to, subject, email_thread = parse_email(state["email_input"])
        # Create email markdown for Agent Inbox in case of notification
        email_markdown = format_email_markdown(subject, author, to, email_thread)

    if store:
        # Search for existing triage_preferences memory
        triage_instructions = await get_memory(
            store=store, namespace=("email_assistant", "triage_preferences"), default_content=default_triage_instructions
        )
        logger.info(f"***{TRIAGE_ROUTER_HITL_NODE} fetch long-term memory for triage_instructions***")
    else:
        # No long-term memory - use default
        triage_instructions = default_triage_instructions

    system_prompt = triage_system_prompt.format(background=default_background, triage_instructions=triage_instructions)

    user_prompt = triage_user_prompt.format(author=author, to=to, subject=subject, email_thread=email_thread)

    result = await llm_router.ainvoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    if result.classification == "respond":
        logger.info(f"{TRIAGE_ROUTER_HITL_NODE} Classification: RESPOND - This email requires a response")
        goto = RESPONSE_AGENT
        update = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Respond to the email: \n\n{email_markdown}",
                }
            ],
            "classification_decision": result.classification,
        }

    elif result.classification == "ignore":
        logger.info(f"{TRIAGE_ROUTER_HITL_NODE} Classification: IGNORE - This email can be safely ignored")
        goto = END
        update = {
            "classification_decision": result.classification,
        }

    elif result.classification == "notify":
        print("🔔 Classification: NOTIFY - This email contains important information")
        goto = TRIAGE_INTERRUPT_HANDLER_NODE
        update = {
            "classification_decision": result.classification,
        }

    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    logger.info(f"***{TRIAGE_ROUTER_HITL_NODE} ended***")
    return Command(goto=goto, update=update)
