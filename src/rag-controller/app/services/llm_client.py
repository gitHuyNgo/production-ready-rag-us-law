import os
from pathlib import Path
from llama_index.llms.openai import OpenAIResponses
from llama_index.core.llms import ChatMessage

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

BASE_FILE = Path(__file__).resolve()
PROJECT_ROOT = BASE_FILE.parents[4]
PROMPT_DIR = PROJECT_ROOT / "llm" / "prompts"
SYSTEM_PROMPT_PATH = PROMPT_DIR / "system_prompt.txt"
ANSWER_STYLE_PATH = PROMPT_DIR / "answer_style.txt"


def _load_prompt(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def init_llm():
    return OpenAIResponses(model="gpt-5.1", api_key=OPENAI_API_KEY)


def ask_llm(llm, query: str, context: str):
    system_prompt = _load_prompt(SYSTEM_PROMPT_PATH)
    answer_style = _load_prompt(ANSWER_STYLE_PATH)
    user_prompt = (f"QUESTION:\n{query}\n\n" f"CONTEXT:\n{context}\n\n") + answer_style

    # messages = [
    #     ChatMessage(
    #         role="system",
    #         content="You are an assistant that helps to answer questions based on the provided context",
    #     ),
    #     ChatMessage(
    #         role="user",
    #         content=f"Answer the following question using the provided context.\n\nQuestion: {query}\n\nContext:\n{context}",
    #     ),
    # ]

    messages = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=user_prompt),
    ]

    resp = llm.chat(messages)
    resp.message.content = "\n" + resp.message.content
    return resp
