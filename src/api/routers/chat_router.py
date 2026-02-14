from fastapi import APIRouter, Request
from src.dtos.chat_dto import ChatDto
from src.api.services.rag_pipeline import answer

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("/")
async def chat(request: Request, dto: ChatDto):
    db = request.app.state.db
    llm = request.app.state.llm
    first_reranker = request.app.state.first_reranker
    second_reranker = request.app.state.second_reranker

    result = answer(
        db=db, 
        llm=llm, 
        first_reranker=first_reranker, 
        second_reranker=second_reranker, 
        query=dto.content
    )

    return {
        "history": dto.history,
        "received_role": "assistant",
        "received_content": result,
        "history_length": len(dto.history)
    }