from email_assistant.consts import MARK_EMAIL_AS_READ_NODE
from email_assistant.logger import logger
from email_assistant.schemas import EmailAgentState
from email_assistant.tools.gmail.gmail_tools import mark_as_read
from email_assistant.utils import parse_gmail


def mark_as_read_node(state: EmailAgentState, use_gmail_tools: bool):
    logger.info(f"***{MARK_EMAIL_AS_READ_NODE}***")
    result = []
    if use_gmail_tools:
        email_input = state["email_input"]
        author, to, subject, email_thread, email_id = parse_gmail(email_input)
        mark_as_read(email_id)
        result.append({"role": "user", "content": f"Gmail email [{email_id}] was marked as read"})

    return {"messages": result}
