from email_assistant.config import USE_GMAIL
from email_assistant.tools.base import get_tools, get_tools_by_name
from email_assistant.tools.default.calendar_tools import (
    check_calendar_availability,
    schedule_meeting,
)
from email_assistant.tools.default.email_tools import (
    Done,
    Question,
    triage_email,
    write_email,
)
from email_assistant.tools.gmail.gmail_tools import (
    check_calendar_tool,
    fetch_emails_tool,
    schedule_meeting_tool,
    send_email_tool,
)

print(f"Use GMAIL ENVAR {USE_GMAIL}")

__all__ = [
    "get_tools",
    "get_tools_by_name",
    "write_email",
    "triage_email",
    "Done",
    "Question",
    "schedule_meeting",
    "check_calendar_availability",
    "send_email_tool",  # GMAIL
    "check_calendar_tool",  # GMAIL
    "schedule_meeting_tool",  # GMAIL
    "fetch_emails_tool",  # GMAIL
]
