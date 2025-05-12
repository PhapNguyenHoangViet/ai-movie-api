import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from motor.motor_asyncio import AsyncIOMotorClientSession

from app.themovie.agents.conversation_agent.state import ConversationState
from app.themovie.exceptions import DefaultException
from app.themovie.models.message import Message
from app.themovie.models.message import MessageTypes
from app.themovie.repositories.conversation_repository import ConversationRepository
from app.themovie.schemas.base import (
    ConversationRequest,
    SuccessResponse,
    ResponseStatus,
)
from app.themovie.databases.mongo import get_db_session_dependency

from app.themovie.services.conversation_service import stream_chat
from app.themovie.databases.postgres import get_postgres_service, PostgreSQLSingleton
import os
from typing import Optional, List
from pydantic import BaseModel

from app.themovie.databases.postgres import PostgreSQLSingleton, get_postgres_service
from app.themovie.services.movie_service import MovieRecommender

router = APIRouter()

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../../services/gcn_model.pth")


class RecommendationResponse(BaseModel):
    movie_id: int
    score: float
    title: Optional[str] = None


@router.get("/recommendations/{user_id}", response_model=List[RecommendationResponse])
async def get_recommendations(
    user_id: int,
    top_k: int = 10,
    pg_service: PostgreSQLSingleton = Depends(get_postgres_service),
):
    """Get movie recommendations for a specific user."""
    try:
        # Initialize the movie recommender with the model
        recommender = MovieRecommender(model_path=MODEL_PATH)

        # Get recommendations
        raw_recommendations = recommender.get_recommendations(user_id, top_k=top_k)

        if not raw_recommendations:
            return []

        # Get movie titles for the recommended movie IDs
        movie_ids = [rec[0] for rec in raw_recommendations]
        placeholders = ", ".join(["%s"] * len(movie_ids))

        query = f"""
            SELECT movie_id, movie_title
            FROM core_movie
            WHERE movie_id IN ({placeholders})
        """

        columns, movie_data = pg_service.execute_query(query, tuple(movie_ids))
        movie_titles = {row[0]: row[1] for row in movie_data} if movie_data else {}

        # Format the recommendations with titles
        recommendations = [
            RecommendationResponse(
                movie_id=rec[0],
                score=rec[1],
                title=movie_titles.get(rec[0], "Unknown Title"),
            )
            for rec in raw_recommendations
        ]

        return recommendations

    except Exception as e:
        logging.error(f"Error getting recommendations: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error getting recommendations: {str(e)}"
        )


@router.get("/users")
async def get_users(pg_service: PostgreSQLSingleton = Depends(get_postgres_service)):
    query = "SELECT * FROM core_user LIMIT 10"
    columns, data = pg_service.execute_query(query)

    if data:
        # Convert data to dictionary format
        result = [dict(zip(columns, row)) for row in data]
        return {"users": result}
    return {"users": []}


@router.post("/chat", response_model=SuccessResponse)
async def chat(
    request: ConversationRequest,
    session: AsyncIOMotorClientSession = Depends(get_db_session_dependency),
):
    """
    This endpoint is used to create a new conversation or continue a conversation.
    """
    try:
        if request.conversation_id is None:
            new_conversation = await ConversationRepository.create_new_conversation(
                request, session
            )
            logging.info(
                f"[CONVERSATION_ROUTER] - New conversation created: {json.dumps(new_conversation)}"
            )
            return JSONResponse(
                status_code=200,
                content={"status": ResponseStatus.SUCCESS, "data": new_conversation},
            )

        await Message(
            conversation_id=UUID(request.conversation_id),
            message=request.message,
            type=MessageTypes.HUMAN,
        ).create(session=session)

        initial_state = ConversationState(
            conversation_id=request.conversation_id,
            messages=[request.message],
            node_name="",
            type=MessageTypes.HUMAN,
        )

        return StreamingResponse(
            stream_chat(
                request,
                initial_state,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Connection": "keep-alive",
                "Transfer-Encoding": "chunked",
            },
        )

    except Exception as e:
        logging.error(
            f"[CONVERSATION_ROUTER] - Error in chat: {str(e)} - conversation_id: {request.conversation_id}"
        )
        emitted_error = DefaultException(
            message="ERROR"
        )
        await Message(
            conversation_id=UUID(request.conversation_id),
            message=emitted_error.message,
            type=MessageTypes.SYSTEM,
        ).create(session=session)
        return JSONResponse(
            status_code=400, content={"status": ResponseStatus.ERROR, "message": str(e)}
        )
