from fastapi import APIRouter
from ..dtos.chat_dto import ChatDto
from ..services.rag_pipeline import answer

from ..services.retriever import connect_weaviate
from ..services.llm_client import init_llm

client = connect_weaviate()
llm = init_llm()

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
def chat(dto: ChatDto):
    result = answer(client, llm, dto.content)

    return {
        "history": dto.history,
        "received_role": dto.role,
        "received_content": str(result.message.content),
        "history_length": len(dto.history)
    }