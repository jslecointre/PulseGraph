# flake8: noqa E501
"""Tool prompt templates for the email assistant."""

# Standard tool descriptions for insertion into prompts
STANDARD_TOOLS_PROMPT = """
1. triage_email(ignore, notify, respond) - Triage emails into one of three categories
2. write_email(to, subject, content) - Send emails to specified recipients
3. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
4. check_calendar_availability(day) - Check available time slots for a given day
5. Done - E-mail has been sent
"""

# Tool descriptions for HITL workflow
HITL_TOOLS_PROMPT = """
1. write_email(to, subject, content) - Send emails to specified recipients
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
3. check_calendar_availability(day) - Check available time slots for a given day
4. Question(content) - Ask the user any follow-up questions
5. Done - E-mail has been sent
"""

# Tool descriptions for HITL with memory workflow
# Note: Additional memory specific tools could be added here
HITL_MEMORY_TOOLS_PROMPT = """
1. write_email(to, subject, content) - Send emails to specified recipients
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
3. check_calendar_availability(day) - Check available time slots for a given day
4. Question(content) - Ask the user any follow-up questions
5. Done - E-mail has been sent
"""

# Tool descriptions for agent workflow without triage
AGENT_TOOLS_PROMPT = """
1. write_email(to, subject, content) - Send emails to specified recipients
2. schedule_meeting(attendees, subject, duration_minutes, preferred_day, start_time) - Schedule calendar meetings where preferred_day is a datetime object
3. check_calendar_availability(day) - Check available time slots for a given day
4. Done - E-mail has been sent
"""


def build_agent_tools_prompt(tools: list) -> str:
    lines = []
    for i, tool in enumerate(tools, start=1):
        tool_name = tool.name
        if tool_name != "Question":
            desc = tool.description
            schema = tool.args_schema
            if hasattr(schema, "__annotations__"):
                tool_args = ", ".join(
                    f"{arg}: {typ.__name__ if hasattr(typ, '__name__') else str(typ)}"
                    for arg, typ in schema.__annotations__.items()
                )
            else:
                tool_args = ""
            lines.append(f"{i}. {tool_name}({tool_args}) - {desc}")
    return "\n".join(lines)
