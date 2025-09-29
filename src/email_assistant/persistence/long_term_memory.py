from typing import List, Optional, Tuple

from langchain_core.messages import BaseMessage
from langchain_core.runnables import Runnable
from langgraph.store.base import BaseStore

from email_assistant.chains.long_term_memory_chain import UserPreferences
from email_assistant.logger import logger
from email_assistant.prompts import MEMORY_UPDATE_INSTRUCTIONS


async def get_memory(store: BaseStore, namespace: Tuple[str, str], default_content: Optional[str] = None):
    """Get memory from the store or initialize with default if it doesn't exist.

    Args:
        store: LangGraph BaseStore instance to search for existing memory
        namespace: Tuple defining the memory namespace, e.g. ("email_assistant", "triage_preferences")
        default_content: Default content to use if memory doesn't exist

    Returns:
        str: The content of the memory profile, either from existing memory or the default
    """
    # Search for existing memory with namespace and key
    user_preferences = await store.aget(namespace, "user_preferences")

    # If memory exists, return its content (the value)
    if user_preferences:
        return user_preferences.value

    # If memory doesn't exist, add it to the store and return the default content
    else:
        # Namespace, key, value
        await store.aput(namespace, "user_preferences", default_content)
        user_preferences = default_content

    # Return the default content
    return user_preferences


async def update_memory(
    store: BaseStore, llm: Runnable[List[BaseMessage], UserPreferences], namespace: Tuple[str, str], messages: List[BaseMessage]
):
    """Update memory profile in the store.

    Args:
        store: LangGraph BaseStore instance to update memory
        llm: instantiate LLM with structured UserPreferences output
        namespace: Tuple defining the memory namespace, e.g. ("email_assistant", "triage_preferences")
        messages: List of messages to update the memory with
    """

    user_preferences = await store.aget(namespace, "user_preferences")

    result = await llm.ainvoke(
        [
            {
                "role": "system",
                "content": MEMORY_UPDATE_INSTRUCTIONS.format(current_profile=user_preferences.value, namespace=namespace),
            },
        ]
        + messages,
        config={},
    )
    logger.info(f"UPDATE LONG-TERM MEMORY [{namespace[1]}] WITH USER PREFERENCES: {user_preferences.value}")
    # Save the updated memory to the store
    await store.aput(namespace, "user_preferences", result.user_preferences)
    return result


async def display_memory_content(store, namespace: Optional[Tuple[str, str]] = None):
    # Display current memory content for all namespaces
    if namespace:
        print(f"\n======= CURRENT MEMORY CONTENT FOR [{namespace[1]}] =======")
        memory = await store.aget(namespace, "user_preferences")
        if memory:
            print(f"\n--- {namespace[1]} ---")
            print(memory.value)
        else:
            print(f"\n--- {namespace[1]} ---")
            print("No memory found")
    else:
        print("\n======= CURRENT MEMORY CONTENT =======")
        for namespace in [
            ("email_assistant", "triage_preferences"),
            ("email_assistant", "response_preferences"),
            ("email_assistant", "cal_preferences"),
            ("email_assistant", "background"),
        ]:
            memory = await store.aget(namespace, "user_preferences")
            if memory:
                print(f"\n--- {namespace[1]} ---")
                print(memory.value)
            else:
                print(f"\n--- {namespace[1]} ---")
                print("No memory found")
            print("=======================================\n")
