from functools import partial
from typing import Optional

from langgraph.graph import END, START, StateGraph
from langgraph.store.base import BaseStore
from langgraph.types import Checkpointer

from email_assistant import SRC_ROOT
from email_assistant.consts import (
    INTERRUPT_HANDLER_NODE,
    LLM_CALL_NODE_HITL,
    MARK_EMAIL_AS_READ_NODE,
    RESPONSE_AGENT,
    TRIAGE_INTERRUPT_HANDLER_NODE,
    TRIAGE_ROUTER_HITL_NODE,
)
from email_assistant.nodes.interrupt_handler import interrupt_handler_node
from email_assistant.nodes.llm_call import llm_call_hitl_node
from email_assistant.nodes.mark_gmail_email_as_read import mark_as_read_node
from email_assistant.nodes.tool import should_call_tool
from email_assistant.nodes.triage_interrupt_handler import triage_interrupt_handler_node
from email_assistant.nodes.triage_router import triage_router_hitl_node
from email_assistant.schemas import EmailAgentState, StateInput
from email_assistant.tools import (  # noqa F401
    Done,
    Question,
    check_calendar_availability,
    schedule_meeting,
    write_email,
)
from email_assistant.utils import show_graph


class EmailAssistantHumanInLoopWorkflows:
    def __init__(self, checkpointer: Checkpointer, store: Optional[BaseStore] = None, use_gmail_tools: bool = False):
        # self.config_data = get_email_config()
        self.checkpointer = checkpointer
        self.store = store
        self.use_gmail_tools = use_gmail_tools

    def _create_overall_workflow(self) -> StateGraph:
        response_agent_workflow = self._create_response_agent_workflow()
        response_agent = response_agent_workflow.compile(checkpointer=self.checkpointer, store=self.store)

        overall_workflow = StateGraph(EmailAgentState, input_schema=StateInput)
        overall_workflow.add_node(TRIAGE_ROUTER_HITL_NODE, partial(triage_router_hitl_node, use_gmail_tools=self.use_gmail_tools))
        overall_workflow.add_node(
            TRIAGE_INTERRUPT_HANDLER_NODE, partial(triage_interrupt_handler_node, use_gmail_tools=self.use_gmail_tools)
        )
        overall_workflow.add_node(RESPONSE_AGENT, response_agent)

        overall_workflow.add_edge(START, TRIAGE_ROUTER_HITL_NODE)

        return overall_workflow

    def _create_response_agent_workflow(self) -> StateGraph:
        workflow = StateGraph(EmailAgentState)
        workflow.add_node(LLM_CALL_NODE_HITL, partial(llm_call_hitl_node, use_gmail_tools=self.use_gmail_tools))
        workflow.add_node(INTERRUPT_HANDLER_NODE, partial(interrupt_handler_node, use_gmail_tools=self.use_gmail_tools))
        workflow.add_node(MARK_EMAIL_AS_READ_NODE, partial(mark_as_read_node, use_gmail_tools=self.use_gmail_tools))
        self._add_response_agent_workflow_edges(workflow)

        return workflow

    def _add_response_agent_workflow_edges(self, workflow: StateGraph):
        workflow.add_edge(START, LLM_CALL_NODE_HITL)
        workflow.add_conditional_edges(
            LLM_CALL_NODE_HITL,
            should_call_tool,
            {"Action": INTERRUPT_HANDLER_NODE, MARK_EMAIL_AS_READ_NODE: MARK_EMAIL_AS_READ_NODE},
        )
        workflow.add_edge(MARK_EMAIL_AS_READ_NODE, END)
        # TODO - investigate why show_graph does not display conditional edge interrupt_handler_node --> llm_call_hitl
        # Note: interrupt_handler_node uses Command(goto=...) for routing
        # LangGraph automatically handles this routing, but visualization does not show it.
        # No explicit conditional edge needed between interrupt_handler_node and llm_call_hitl
        # Command objects take precedence

    def build_graph(self, draw: bool = False):
        workflow = self._create_overall_workflow()

        compiled_graph = workflow.compile(checkpointer=self.checkpointer, store=self.store)

        if draw:
            # graph_ascii = compiled_graph.get_graph(xray=True).draw_ascii()
            # print(graph_ascii)
            show_graph(compiled_graph, output_file_path=f"{SRC_ROOT}/images/agent_hitl_workflow.png", xray=True)
        return compiled_graph

    def run(self, input_state: EmailAgentState, config: dict = None):
        compiled_graph = self.build_graph()

        return compiled_graph.invoke(input=input_state, config=config or {})
