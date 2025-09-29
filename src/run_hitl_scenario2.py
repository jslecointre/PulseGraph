import uuid

from run_utils import resume_agent, run_interrupted_scenario, start_agent


# Interrupts Allow Us to Edit Tool Calls
async def run_scenario2_logic(compiled_workflow):
    email_input_respond = {
        "to": "JS Lecointre <js@company.com",
        "author": "Project Manager <pm@client.com>",
        "subject": "Tax season let's schedule call",
        "email_thread": "Lance,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax planning strategies for this year. I have some suggestions that could potentially save you money.\n\nAre you available sometime next week? Tuesday or Thursday afternoon would work best for me, for about 45 minutes.\n\nRegards,\nProject Manager",  # noqa E501
    }

    print("Running Email Assistant with Human in the Loop Workflows")
    thread_id = f"{uuid.uuid4()}"

    interrupt_object1 = await start_agent(email=email_input_respond, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # schedule_meeting edit
    print(f"\nSimulating user editing the {interrupt_object1.value[0]['action_request']['action']} tool call...")
    edited_schedule_args = {
        "attendees": ["pm@client.com", "lance@company.com"],
        "subject": "Tax Planning Discussion",
        "duration_minutes": 30,  # Changed from 45 to 30
        "preferred_day": "2025-05-06",
        "start_time": 14,
    }
    resume_input1 = {"type": "edit", "args": {"args": edited_schedule_args}}
    interrupt_object2 = await resume_agent(resume_input=resume_input1, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # write_email edit
    print(f"\nSimulating user editing the {interrupt_object2.value[0]['action_request']['action']} tool call...")

    edited_email_args = {
        "to": "pm@client.com",
        "subject": "Re: Tax season let's schedule call",
        "content": "Hello Project Manager,\n\nThank you for reaching out about tax planning. I scheduled a 30-minute call next Thursday at 3:00 PM. Would that work for you?\n\nBest regards,\nJS Lecointre",  # noqa E501
    }
    resume_input2 = {"type": "edit", "args": {"args": edited_email_args}}
    # resume_input2 = {"type": "accept"}
    await resume_agent(resume_input=resume_input2, thread_id=thread_id, compiled_workflow=compiled_workflow)
    # TODO Error with Postgres - resume workflow to a previous state - missing last 2 messages
    #  TOOL and AI could be related to issue https://github.com/langchain-ai/langgraph/issues/5769

    state = await compiled_workflow.aget_state(config={"configurable": {"thread_id": thread_id}}, subgraphs=True)
    for m in state.values["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    import asyncio

    from email_assistant.config import USE_GMAIL

    checkpointer_type = "postgres"  # "memory" "postgres" "sqlite"
    store_type = None  # "None" "memory" "postgres" "sqlite"
    print(checkpointer_type, store_type)
    asyncio.run(
        run_interrupted_scenario(
            checkpointer_type=checkpointer_type,
            workflow_logic=run_scenario2_logic,
            store_type=store_type,
            use_gmail_tools=USE_GMAIL,
        )
    )
