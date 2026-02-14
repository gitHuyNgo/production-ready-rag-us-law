
from fastapi import FastAPI

from .routers.chat_router import router as chat_router
from .routers.helper_router import router as helper_router

from dotenv import load_dotenv
load_dotenv()



app = FastAPI()

app.include_router(chat_router)
app.include_router(helper_router)



# def main():
#     client = connect_weaviate()
#     llm = init_llm()

#     try:
#         while True:
#             q = input("\nAsk (or exit): ")
#             if q.lower() == "exit":
#                 break
#             resp = answer(client, llm, q)
#             print(resp)
#     finally:
#         client.close()

# if __name__ == "__main__":
#     main()
