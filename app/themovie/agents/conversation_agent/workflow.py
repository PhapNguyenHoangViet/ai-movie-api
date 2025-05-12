from typing import Any

from langgraph.constants import START, END

from app.themovie.agents.conversation_agent.nodes.chat_node import chat_node
from app.themovie.agents.conversation_agent.state import ConversationState
from app.themovie.agents.workflow import BaseWorkflow


def get_conversation_graph(state: ConversationState, checkpointer: Any):
    conversation_workflow = BaseWorkflow(state)

    conversation_workflow.add_node("chat_node", chat_node)

    conversation_workflow.add_edge(START, "chat_node")
    conversation_workflow.add_edge("chat_node", END)

    conversation_graph = conversation_workflow.get_graph()
    return conversation_graph.compile(checkpointer=checkpointer)


def get_conversation_workflow(state, checkpointer):
    return get_conversation_graph(state=state, checkpointer=checkpointer)
