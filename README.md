End-to-end deployment of a scalable RAG pipeline for U.S. legal QA, featuring Kubernetes microservices, vector-based retrieval, CI/CD automation, and high-performance LLM serving.

##### Set up project

```bash
git clone https://github.com/gitHuyNgo/production-ready-rag-us-law.git

cd path/to/production-ready-rag-us-law
python -m venv .venv # or python3

source .venv/bin/activate  # MacOS
.venv\Scripts\activate # Window

pip install -r requirements.txt # or pip3
```

##### Run project

```bash
uvicorn src.rag-controller.app.main:app --reload
```

##### Test API

Test API on http://localhost:8000/docs
