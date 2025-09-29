import uuid

from run_utils import resume_agent, run_interrupted_scenario, start_agent


# Interrupts Enable New Tools
async def run_scenario4_logic(compiled_workflow):
    # GMAIL
    if USE_GMAIL:
        email_input_respond = {
            "from": "JS <my-name@email.com>",
            "to": '"agentic@gmail.com" <agentic@gmail.com>',
            "subject": "Dinner?",
            "body": "Hey, do you want italian or indian tonight?\r\n\r\n",
            "id": "1998e51524127560",
        }
    else:
        email_input_respond = {
            "to": "JS Lecointre <js@company.com",
            "author": "Partner <partner@home.com>",
            "subject": "Dinner?",
            "email_thread": "Hey, do you want italian or indian tonight?",
        }

    print("Running Email Assistant with Human in the Loop Workflows")
    thread_id = f"{uuid.uuid4()}"

    interrupt_object1 = await start_agent(email=email_input_respond, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # Question tool call feedback
    print(f"\nSimulating user providing feedback for the {interrupt_object1.value[0]['action_request']['action']} tool call...")

    resume_input1 = {"type": "response", "args": "Let's do indian."}
    interrupt_object2 = await resume_agent(resume_input=resume_input1, thread_id=thread_id, compiled_workflow=compiled_workflow)

    # write_emai accept
    print(f"\nSimulating user accepting the {interrupt_object2.value[0]['action_request']['action']} tool call...")
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

    checkpointer_type = "memory"  # "memory" "postgres" "sqlite"
    store_type = "memory"  # "memory" "postgres" "sqlite"
    print(checkpointer_type)
    asyncio.run(
        run_interrupted_scenario(
            checkpointer_type=checkpointer_type,
            workflow_logic=run_scenario4_logic,
            store_type=store_type,
            use_gmail_tools=USE_GMAIL,
        )
    )
