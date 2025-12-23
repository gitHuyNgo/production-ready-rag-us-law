from fastapi import APIRouter
from ..dtos.chat_dto import ChatDto

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
def chat(dto: ChatDto):
    return {
        "history": dto.history,
        "received_role": dto.role,
        "received_content": dto.content,
        "history_length": len(dto.history)
    }