# noqa E501
import ast
import re
from datetime import datetime
from typing import Union

from langchain_core.tools import tool


@tool
def schedule_meeting(
    attendees: Union[list[str], str], subject: str, duration_minutes: int, preferred_day: datetime, start_time: int
) -> str:
    """Schedule a calendar meeting."""
    # Placeholder response - in real app would check calendar and schedule
    if isinstance(attendees, str):
        if re.fullmatch(r"\[.*\]", attendees):
            attendees = ast.literal_eval(attendees)
        else:
            email_pattern = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
            attendees = re.findall(email_pattern, attendees)
    date_str = preferred_day.strftime("%A, %B %d, %Y")
    return f"Meeting '{subject}' scheduled on {date_str} at {start_time} for {duration_minutes} minutes with {len(attendees)} attendees"  # noqa E501


@tool
def check_calendar_availability(day: str) -> str:
    """Check calendar availability for a given day."""
    # Placeholder response - in real app would check actual calendar
    return f"Available times on {day}: 9:00 AM, 2:00 PM, 4:00 PM"
