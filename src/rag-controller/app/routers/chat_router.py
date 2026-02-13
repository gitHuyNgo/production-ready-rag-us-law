from fastapi import APIRouter
from ..dtos.chat_dto import ChatDto
from ..services.rag_pipeline import answer

from main import client, llm

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
def chat(dto: ChatDto):
    result = answer(client, llm, dto.content)

    return {
        "history": dto.history,
        "received_role": dto.role,
        "received_content": result,
        "history_length": len(dto.history)
    }