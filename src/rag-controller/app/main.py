from fastapi import FastAPI
from .dtos.chat_dto import ChatDto


app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "200 OK"}

@app.post("/")
def chat(dto: ChatDto):
    return {
        "history": dto.history,
        "received_role": dto.role,
        "received_content": dto.content,
        "history_length": len(dto.history)
    }