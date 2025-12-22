from pydantic import BaseModel
from typing import List
from enum import Enum

class Role(Enum):
    user = "user"
    agent = "agent"

class ChatMessageDto(BaseModel):
    role: Role
    content: str

class ChatDto(BaseModel):
    history: List[ChatMessageDto]
    role: Role
    content: str
