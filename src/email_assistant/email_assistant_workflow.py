from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.types import Checkpointer

from email_assistant import SRC_ROOT
from email_assistant.config import USE_GMAIL
from email_assistant.consts import (
    EMAIL_AGENT,
    LLM_CALL_NODE,
    MARK_EMAIL_AS_READ_NODE,
    TOOL_HANDLER_NODE,
    TRIAGE_ROUTER_NODE,
)
from email_assistant.nodes.llm_call import llm_call_node
from email_assistant.nodes.mark_gmail_email_as_read import mark_as_read_node
from email_assistant.nodes.tool import should_call_tool, tool_handler_node
from email_assistant.nodes.triage_router import triage_router_node
from email_assistant.schemas import EmailAgentState
from email_assistant.utils import show_graph


class EmailAssistantWorkflows:
    def __init__(self, checkpointer: Checkpointer, use_gmail_tools: bool = False):
        # self.config_data = get_email_config()
        self.checkpointer = checkpointer
        self.use_gmail_tools = use_gmail_tools

    def _create_overall_workflow(self) -> StateGraph:
        email_agent_workflow = self._create_email_agent_workflow()
        email_agent = email_agent_workflow.compile(checkpointer=self.checkpointer)

        overall_workflow = StateGraph(EmailAgentState)
        overall_workflow.add_node(TRIAGE_ROUTER_NODE, triage_router_node)
        overall_workflow.add_node(EMAIL_AGENT, email_agent)

        overall_workflow.add_edge(START, TRIAGE_ROUTER_NODE)
        overall_workflow.add_edge(TRIAGE_ROUTER_NODE, END)
        overall_workflow.add_edge(EMAIL_AGENT, END)

        return overall_workflow

    def _create_email_agent_workflow(self) -> StateGraph:
        workflow = StateGraph(EmailAgentState)
        workflow.add_node(LLM_CALL_NODE, partial(llm_call_node, use_gmail_tools=self.use_gmail_tools))
        workflow.add_node(TOOL_HANDLER_NODE, tool_handler_node)
        workflow.add_node(MARK_EMAIL_AS_READ_NODE, partial(mark_as_read_node, use_gmail_tools=self.use_gmail_tools))
        self._add_email_agent_workflow_edges(workflow)

        return workflow

    def _add_email_agent_workflow_edges(self, workflow: StateGraph):
        # Add edges to connect nodes
        workflow.add_edge(START, LLM_CALL_NODE)
        workflow.add_conditional_edges(
            LLM_CALL_NODE,
            should_call_tool,
            {
                "Action": TOOL_HANDLER_NODE,
                MARK_EMAIL_AS_READ_NODE: MARK_EMAIL_AS_READ_NODE,
            },
        )
        workflow.add_edge(TOOL_HANDLER_NODE, LLM_CALL_NODE)
        workflow.add_edge(MARK_EMAIL_AS_READ_NODE, END)

    def build_graph(self, draw: bool = False):
        workflow = self._create_overall_workflow()

        compiled_graph = workflow.compile(checkpointer=self.checkpointer)

        if draw:
            show_graph(compiled_graph, output_file_path=f"{SRC_ROOT}/images/agent_workflow.png", xray=True)
        return compiled_graph

    def run(self, input_state: EmailAgentState, config: dict = None):
        compiled_graph = self.build_graph()

        return compiled_graph.invoke(input=input_state, config=config or {})


workflow = EmailAssistantWorkflows(checkpointer=None, use_gmail_tools=USE_GMAIL)
compiled_workflow = workflow.build_graph(draw=True)

if __name__ == "__main__":
    import asyncio
    import time
    import uuid
    from typing import Dict

    async def main(email: Dict):
        print("Running Email Assistant Workflows")
        thread_id = f"{uuid.uuid4()}"
        config = {"configurable": {"thread_id": thread_id, "recursion_limit": 100}}
        config["run_name"] = f'email_workflow_{time.strftime("%m-%d-%Hh%M", time.localtime())}'

        response = await compiled_workflow.ainvoke(input={"email_input": email}, config=config)
        for m in response["messages"]:
            m.pretty_print()

    email_input = {
        "author": "Alice Smith <alice.smith@company.com>",
        "to": "John Doe <john.doe@company.com>",
        "subject": "Quick question about API documentation",
        "email_thread": "Hi John,\nI was reviewing the API documentation for the new authentication service and noticed a few endpoints seem to be missing from the specs. Could you help clarify if this was intentional or if we should update the docs?\nSpecifically, I'm looking at:\n- /auth/refresh\n- /auth/validate\nThanks!\nAlice",  # noqa E501
    }

    email_input = {
        "to": "JS Lecointre <js@company.com",
        "author": "Project Manager <pm@client.com>",
        "subject": "Tax season let's schedule call",
        "email_thread": "Lance,\n\nIt's tax season again, and I wanted to schedule a call to discuss your tax planning strategies for this year. I have some suggestions that could potentially save you money.\n\nAre you available sometime next week? Tuesday or Thursday afternoon would work best for me, for about 45 minutes.\n\nRegards,\nProject Manager",  # noqa E501
    }

    workflow_state = asyncio.run(main(email=email_input))
