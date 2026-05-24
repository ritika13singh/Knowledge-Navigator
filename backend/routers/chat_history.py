"""
Chat History API — endpoints for persisting user chat conversations.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.auth import RequiredUser
from backend import chat_history_db

router = APIRouter(prefix="/api/chat-history", tags=["chat-history"])


class SaveConversationRequest(BaseModel):
    conversation_id: str
    title: str
    messages: list[dict]


class DeleteConversationRequest(BaseModel):
    conversation_id: str


@router.get("/conversations")
def get_conversations(user: RequiredUser):
    """
    Get all conversations for the authenticated user.
    Returns list of conversations with metadata and messages.
    """
    conversations = chat_history_db.get_user_conversations(user.sub)
    return {"conversations": conversations}


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str, user: RequiredUser):
    """
    Get a specific conversation for the authenticated user.
    """
    conversation = chat_history_db.get_conversation(user.sub, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"conversation": conversation}


@router.post("/conversations")
def save_conversation(body: SaveConversationRequest, user: RequiredUser):
    """
    Save or update a conversation for the authenticated user.
    """
    success = chat_history_db.save_conversation(
        user_id=user.sub,
        conversation_id=body.conversation_id,
        title=body.title,
        messages=body.messages,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save conversation")
    return {"ok": True}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str, user: RequiredUser):
    """
    Delete a conversation for the authenticated user.
    """
    success = chat_history_db.delete_conversation(user.sub, conversation_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete conversation")
    return {"ok": True}
