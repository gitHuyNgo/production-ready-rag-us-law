from dotenv import load_dotenv
load_dotenv()

from services.retriever import connect_weaviate
from services.llm_client import init_llm
from services.rag_pipeline import answer

client = connect_weaviate()
llm = init_llm()

def main():

    try:
        while True:
            q = input("\nAsk (or exit): ")
            if q.lower() == "exit":
                break
            resp = answer(client, llm, q)
            print(resp)
    finally:
        client.close()

if __name__ == "__main__":
    main()