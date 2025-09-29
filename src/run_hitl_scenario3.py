import uuid

from run_utils import resume_agent, run_interrupted_scenario, start_agent


# Interrupts Allow Us to Provide Feedback on Tool Calls
async def run_scenario3_logic(compiled_workflow):
    # gmail format
    if USE_GMAIL:
        email_input_respond = {
            "from": "JS <my-name@email.com>",
            "to": '"agentic@gmail.com" <agentic@gmail.com>',
            "subject": "Important schedule call for tax planning",
            "body": "Jacques,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax planning strategies for this year. I have some suggestions that could potentially save you money.\n\nAre you available sometime next week? Tuesday or Thursday afternoon would work best for me, for about 45 minutes.\n\nRegards,\nProject Manager",  # noqa E501
            "id": "1998e1ebafd2ff64",
        }
    else:
        email_input_respond = {
            "to": "JS Lecointre <js@company.com",
            "author": "Project Manager <pm@client.com>",
            "subject": "Tax season let's schedule call",
            "email_thread": "Lance,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax planning strategies for this year. I have some suggestions that could potentially save you money.\n\nAre you available sometime next week? Tuesday or Thursday afternoon would work best for me, for about 45 minutes.\n\nRegards,\nProject Manager",  # noqa E501
        }
    print("Running Email Assistant with Human in the Loop Workflows")
    thread_id = f"{uuid.uuid4()}"

    interrupt_object1 = await start_agent(email=email_input_respond, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # schedule_meeting feedback
    print(f"\nSimulating user providing feedback for the {interrupt_object1.value[0]['action_request']['action']} tool call...")
    resume_input1 = {
        "type": "response",
        "args": "Please schedule this for 30 minutes instead of 45 minutes, and I prefer afternoon meetings after 2pm.",
    }
    interrupt_object2 = await resume_agent(resume_input=resume_input1, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # schedule_meeting accept
    print(f"\nSimulating user accepting the {interrupt_object2.value[0]['action_request']} tool call...")
    resume_input2 = {"type": "accept"}
    interrupt_object3 = await resume_agent(resume_input=resume_input2, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # write_email feedback
    print(f"\nSimulating user providing feedback for the {interrupt_object3.value[0]['action_request']['action']} tool call...")
    resume_input3 = {
        "type": "response",
        "args": "Shorter and less formal. Include a closing statement about looking forward to the meeting!",
    }
    interrupt_object4 = await resume_agent(resume_input=resume_input3, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # write_email accept
    print(f"\nSimulating user accepting the {interrupt_object4} tool call...")
    resume_input4 = {"type": "accept"}
    await resume_agent(resume_input=resume_input4, thread_id=thread_id, compiled_workflow=compiled_workflow)
    # TODO Error with Postgres TypeError: Object of type AIMessage is not JSON serializable
    #  issue https://github.com/langchain-ai/langgraph/issues/5769

    state = await compiled_workflow.aget_state(config={"configurable": {"thread_id": thread_id}})
    for m in state.values["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    import asyncio

    from email_assistant.config import USE_GMAIL

    checkpointer_type = "memory"  # "memory"  # "memory" "postgres" "sqlite"
    store_type = "memory"  # "memory"  # "memory" "postgres" "sqlite"
    print(checkpointer_type)
    asyncio.run(
        run_interrupted_scenario(
            checkpointer_type=checkpointer_type,
            workflow_logic=run_scenario3_logic,
            store_type=store_type,
            use_gmail_tools=USE_GMAIL,
        )
    )
