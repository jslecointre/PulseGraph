import uuid

from langgraph.checkpoint.memory import InMemorySaver  # noqa F401

from run_utils import resume_agent, run_interrupted_scenario, start_agent


# Interrupts Allow Us to Review and Accept Tool Calls
async def run_scenario1_logic(compiled_workflow):
    if USE_GMAIL:
        email_input_respond = {
            "from": "JS <my-name@email.com>",
            "to": '"agentic@gmail.com" <agentic@gmail.com>',
            "subject": "Tax season let's schedule call",
            "body": "Jean,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax planning strategies for this year. I have some suggestions that could potentially save you money.\n\nAre you available sometime next week? Tuesday or Thursday afternoon would work best for me, for about 45 minutes.\n\nRegards,\nProject Manager",  # noqa E501
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

    # schedule_meeting accept
    print(f"\nSimulating user accepting the {interrupt_object1.value[0]['action_request']} tool call...")
    resume_input1 = {"type": "accept"}
    interrupt_object2 = await resume_agent(resume_input=resume_input1, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # write_email accept
    print(f"\nSimulating user accepting the {interrupt_object2.value[0]['action_request']} tool call...")
    resume_input2 = {"type": "accept"}
    await resume_agent(resume_input=resume_input2, thread_id=thread_id, compiled_workflow=compiled_workflow)
    # TODO Error with Postgres TypeError: Object of type AIMessage is not JSON serializable
    #  issue https://github.com/langchain-ai/langgraph/issues/5769

    state = await compiled_workflow.aget_state(config={"configurable": {"thread_id": thread_id}})
    for m in state.values["messages"]:
        m.pretty_print()


if __name__ == "__main__":
    import asyncio

    from email_assistant.config import USE_GMAIL

    checkpointer_type = "sqlite"  # "memory" "postgres" "sqlite"
    store_type = "memory"  # None "memory" "postgres" "sqlite"
    print(f"Checkpointer type: {checkpointer_type}")
    print(f"Use Gmail tools: {USE_GMAIL}")
    asyncio.run(
        run_interrupted_scenario(
            checkpointer_type=checkpointer_type,
            workflow_logic=run_scenario1_logic,
            store_type=store_type,
            use_gmail_tools=USE_GMAIL,
        )
    )
