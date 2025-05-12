import logging
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.types import StreamWriter

from app.themovie.agents.conversation_agent.prompts.system_prompts import (
    system_prompt_chat_node,
)
from app.themovie.agents.conversation_agent.prompts.user_prompts import (
    user_prompt_chat_node,
)
from app.themovie.agents.conversation_agent.state import ConversationState
from app.themovie.config import (
    CONVERSATION_CHAT_MODEL_NAME,
    CONVERSATION_CHAT_TOP_P,
    CONVERSATION_CHAT_TEMPERATURE,
    MESSAGES_LIMIT,
)
from app.themovie.exceptions import StreamingException
from app.themovie.factories.ai_model_factory import AIModelFactory
from app.themovie.models.message import Message
from app.themovie.models.message import MessageTypes
from app.themovie.utils.helpers import StreamWriter as ConversationStreamWriter
from app.themovie.databases.mongo import get_db_session_with_context


async def chat_node(
    state: ConversationState, config: RunnableConfig, writer: StreamWriter
) -> ConversationState:
    llm = AIModelFactory.create_model_service(
        model_name=CONVERSATION_CHAT_MODEL_NAME,
        temperature=CONVERSATION_CHAT_TEMPERATURE,
        top_p=CONVERSATION_CHAT_TOP_P,
    )
    conversation_id = state.conversation_id
    node_name = config.get("metadata", {}).get("langgraph_node")
    try:
        async with get_db_session_with_context() as session:
            messages = (
                await Message.find(
                    {
                        "conversation_id": UUID(conversation_id),
                        "type": {
                            "$in": [
                                MessageTypes.HUMAN,
                                MessageTypes.AI,
                                MessageTypes.HIDDEN,
                            ]
                        },
                    },
                    session=session,
                )
                .sort([("created_at", 1)])
                .limit(MESSAGES_LIMIT)
                .to_list()
            )

        user_input = messages[-1].message if messages else ""
        user_prompt = user_prompt_chat_node(user_input)

        context_messages = [
            (
                HumanMessage(content=msg.message)
                if msg.type == MessageTypes.HUMAN
                else AIMessage(content=msg.message)
            )
            for msg in messages[:-1]
        ]
        logging.info(
            f"[CONVERSATION_CHAT_NODE] - LENGTH_OF_CONTEXT_MESSAGES: {len(context_messages)}, conversation_id: {conversation_id}"
        )
        system_prompt = SystemMessage(content=(system_prompt_chat_node()))

        async for chunk in llm.ai_astream(
            [system_prompt] + context_messages + [HumanMessage(content=user_prompt)]
        ):
            writer(
                ConversationStreamWriter(
                    messages=[llm.ai_chunk_stream(chunk)],
                    node_name=node_name,
                    type=MessageTypes.AI,
                ).to_dict()
            )

        state.type = MessageTypes.HIDDEN
        state.messages = ["[END]"]
        state.node_name = node_name

    except Exception as e:
        logging.error(
            f"[CONVERSATION_CHAT_NODE] - Error in chat_node: {str(e)}, conversation_id: {conversation_id}"
        )
        raise StreamingException(config["metadata"].get("langgraph_node"))

    return state
