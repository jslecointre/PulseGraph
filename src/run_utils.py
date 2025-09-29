import time
from typing import Awaitable, Dict, Optional

from langgraph.checkpoint.memory import InMemorySaver  # noqa F401
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore  # noqa F401
from langgraph.store.postgres.aio import AsyncPostgresStore  # noqa F401
from langgraph.store.sqlite.aio import AsyncSqliteStore  # noqa F401
from langgraph.types import Checkpointer, Command
from psycopg_pool import AsyncConnectionPool

from email_assistant import SRC_ROOT
from email_assistant.email_assistant_hitl_workflow import (
    EmailAssistantHumanInLoopWorkflows,
)
from email_assistant.persistence.long_term_memory import display_memory_content
from email_assistant.persistence.postgres_utils import check_connection, get_db_uri

memory_updates_mapping = {"write_email": "response_preferences", "schedule_meeting": "cal_preferences"}


async def run_interrupted_scenario(
    checkpointer_type: str, workflow_logic: Awaitable[None], store_type: Optional[str] = None, use_gmail_tools: bool = False
) -> None:
    async def create_and_run_workflow(checkpointer: Checkpointer, store: Optional[BaseStore] = None):
        """Helper to create workflow and run logic"""
        workflow = EmailAssistantHumanInLoopWorkflows(checkpointer=checkpointer, store=store, use_gmail_tools=use_gmail_tools)
        compiled_workflow = workflow.build_graph(draw=False)
        await workflow_logic(compiled_workflow=compiled_workflow)

    def create_postgres_pool():
        """Helper to create PostgreSQL connection pool"""
        return AsyncConnectionPool(
            conninfo=get_db_uri(),
            max_size=20,
            max_lifetime=120,
            check=check_connection,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )

    if checkpointer_type == "postgres":
        async with create_postgres_pool() as pool:
            checkpointer = AsyncPostgresSaver(pool)
            await checkpointer.setup()

            if store_type == "postgres":
                store = AsyncPostgresStore(pool)
                await store.setup()
                await create_and_run_workflow(checkpointer, store)
            elif store_type == "sqlite":
                async with AsyncSqliteStore.from_conn_string(f"{SRC_ROOT}/config/store.sqlite") as store:
                    await create_and_run_workflow(checkpointer, store)
            else:
                store = InMemoryStore() if store_type == "memory" else None
                await create_and_run_workflow(checkpointer, store)

    elif checkpointer_type == "sqlite":
        async with AsyncSqliteSaver.from_conn_string(f"{SRC_ROOT}/config/checkpoints.sqlite") as checkpointer:
            if store_type == "postgres":
                async with create_postgres_pool() as store_pool:
                    store = AsyncPostgresStore(store_pool)
                    await store.setup()
                    await create_and_run_workflow(checkpointer, store)
            elif store_type == "sqlite":
                async with AsyncSqliteStore.from_conn_string(f"{SRC_ROOT}/config/store.sqlite") as store:
                    await create_and_run_workflow(checkpointer, store)
            else:
                store = InMemoryStore() if store_type == "memory" else None
                await create_and_run_workflow(checkpointer, store)

    elif checkpointer_type == "memory":
        checkpointer = InMemorySaver()
        if store_type == "postgres":
            async with create_postgres_pool() as store_pool:
                store = AsyncPostgresStore(store_pool)
                await store.setup()
                await create_and_run_workflow(checkpointer, store)
        elif store_type == "sqlite":
            async with AsyncSqliteStore.from_conn_string(f"{SRC_ROOT}/config/store.sqlite") as store:
                await create_and_run_workflow(checkpointer, store)
        else:
            store = InMemoryStore() if store_type == "memory" else None
            await create_and_run_workflow(checkpointer, store)

    else:
        raise ValueError(f"Invalid checkpointer_type: {checkpointer_type}. Choose from 'postgres', 'memory', or 'sqlite'.")


async def start_agent(email: Dict, thread_id: str, compiled_workflow: CompiledStateGraph):
    config = {"configurable": {"thread_id": thread_id, "recursion_limit": 100}}
    config["run_name"] = f'start_email_hitl_workflow_{time.strftime("%m-%d-%Hh%M", time.localtime())}'
    if store := compiled_workflow.store:
        print("\nChecking memory before running the agent :")
        await display_memory_content(store)
    async for chunk in compiled_workflow.astream({"email_input": email}, config=config):
        # Inspect interrupt object if present
        if "__interrupt__" in chunk:
            Interrupt_Object = chunk["__interrupt__"][0]
            print("\nINTERRUPT OBJECT:")
            print(f"Action Request: {Interrupt_Object.value[0]['action_request']}")
            # Check long-term memory after first interrupt
            action = Interrupt_Object.value[0]["action_request"]["action"]
            if store:
                namespace = (
                    ("email_assistant", memory_updates_mapping.get(action)) if memory_updates_mapping.get(action) else None
                )
                await display_memory_content(store, namespace)
            return Interrupt_Object


async def resume_agent(resume_input: Dict, thread_id: str, compiled_workflow: CompiledStateGraph):
    print("Resume Email Assistant after interrupt")
    config = {"configurable": {"thread_id": thread_id, "recursion_limit": 100}}
    config["run_name"] = f'resume_email_hitl_workflow_{time.strftime("%m-%d-%Hh%M", time.localtime())}'
    if store := compiled_workflow.store:
        print("\nChecking memory after interrupt before resuming agent :")
        await display_memory_content(store)
    async for chunk in compiled_workflow.astream(Command(resume=[resume_input]), config=config):
        if "response_agent" in chunk:
            chunk["response_agent"]["messages"][-1].pretty_print()
        # Inspect interrupt object if present
        if "__interrupt__" in chunk:
            Interrupt_Object = chunk["__interrupt__"][0]
            print("\nINTERRUPT OBJECT:")
            print(f"Action Request: {Interrupt_Object.value[0]['action_request']}")
            action = Interrupt_Object.value[0]["action_request"]["action"]
            if store:
                await display_memory_content(store, ("email_assistant", memory_updates_mapping.get(action)))
            return Interrupt_Object


# set to None for langgraph dev
workflow = EmailAssistantHumanInLoopWorkflows(checkpointer=None, use_gmail_tools=True)
compiled_workflow = workflow.build_graph(draw=True)
