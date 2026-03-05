# Weaviate Vector Store

**Owners:** chat-api (read + write for RAG retrieval), ingestion-worker (write + schema only)
**Purpose:** Store document chunk embeddings for semantic search in the RAG pipeline.
**Image:** `cr.weaviate.io/semitechnologies/weaviate:1.30.0`
**Port:** 8080 (HTTP API), 50051 (gRPC)
**Data path:** `/var/lib/weaviate`

---

## What Weaviate Does in This System

Legal documents (PDFs) are chunked into paragraphs, each paragraph is embedded into a 3072-dimensional vector using OpenAI's `text-embedding-3-large` model, and the vector + text + metadata are stored in Weaviate. At query time, the user's question is embedded with the same model, and Weaviate finds the most similar document chunks using vector similarity search.

```
Ingestion:
  PDF → chunks → OpenAI embedding → Weaviate (store)

Query:
  "What does the 4th amendment protect?"
    → OpenAI embedding → Weaviate (search) → top 25 most similar chunks
    → reranked → sent to LLM as context
```

---

## Collection Schema

Collection name: configurable via `WEAVIATE_CLASS_NAME` (default: `document_chunk_embedding`)

### Properties

| Property | Type | Description |
| --- | --- | --- |
| `text` | `text` | The document chunk content (paragraph or section of a legal document) |
| `source` | `text` | Source reference (e.g., `"USC Title 18 § 1341"`, `"Katz v. United States"`) |

### Vector

| Setting | Value |
| --- | --- |
| Vectorizer | `none` (self-provided vectors — embeddings computed externally by OpenAI) |
| Dimension | 3072 (`text-embedding-3-large`) |
| Distance metric | Cosine |
| Index type | HNSW (Hierarchical Navigable Small World) |

**Why `none` vectorizer?** Weaviate supports built-in vectorizers (e.g., `text2vec-openai`), but this project computes embeddings externally using `llama_index.embeddings.openai.OpenAIEmbedding`. This gives full control over the embedding model, batching, and error handling.

---

## Schema Initialization

**Source:** `app/chat-api/src/vector_store/schema.py` and `app/ingestion-worker/src/vector_store/schema.py`

Both services have their own `init_schema()` function:

```python
def init_schema(client, class_name, recreate=False):
    if recreate:
        client.collections.delete(class_name)   # drop existing collection
    client.collections.create(
        name=class_name,
        properties=[
            Property(name="text", data_type=DataType.TEXT),
            Property(name="source", data_type=DataType.TEXT),
        ],
        vectorizer_config=Configure.Vectorizer.none(),
    )
```

**`--recreate` flag (ingestion-worker only):** Deletes the existing collection and creates a fresh one. Use when changing the embedding model or dimension, as existing vectors would be incompatible.

---

## Chat API Usage (Read Path)

**Source:** `app/chat-api/src/vector_store/weaviate_client.py`

### Connect

```python
client = weaviate.connect_to_local(host="weaviate", port=8080)
```

### Retrieve (vector similarity search)

```python
def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    query_vector = self.embed_model.get_text_embedding(query)     # OpenAI API call
    collection = self.client.collections.use(self.class_name)
    response = collection.query.near_vector(
        near_vector=query_vector,
        limit=top_k,
        return_metadata=MetadataQuery(distance=True),
    )
    return [obj.properties for obj in response.objects]
```

**What happens inside `near_vector`:**

1. Weaviate receives the query vector (3072 floats)
2. HNSW index navigates the graph from the entry point
3. At each layer, it moves to the nearest neighbor
4. Returns `top_k` objects sorted by cosine distance
5. Each object includes `properties` (text, source) and `metadata` (distance)

**Latency:** ~5-20ms for 100K vectors with HNSW. HNSW is O(log n) due to the skip-list-like layer structure.

---

## Ingestion Worker Usage (Write Path)

**Source:** `app/ingestion-worker/src/vector_store/weaviate_client.py`

### Batch Load

```python
def batch_load(self, items: List[Dict[str, Any]]) -> None:
    collection = self.client.collections.use(self.class_name)
    with collection.batch.dynamic() as batch:
        for item in items:
            vector = self.embed_model.get_text_embedding(item["text"])    # OpenAI API call
            batch.add_object(properties=item, vector=vector)
```

**Dynamic batching:** Weaviate's `batch.dynamic()` automatically determines the optimal batch size based on throughput. It starts small, increases batch size when the server responds quickly, and decreases when it detects backpressure.

### No Retrieve

```python
def retrieve(self, query: str, top_k: int = 10):
    raise NotImplementedError("Ingestion-worker only writes to Weaviate")
```

The ingestion worker has no reason to read from Weaviate. This enforces the ownership boundary defined in ADR 003.

---

## Ingestion Flow (End to End)

```
$ python -m src.main --data ./data --recreate

1. Connect to Weaviate
2. If --recreate: delete collection → create fresh schema
3. For each PDF in ./data/:
   a. Convert PDF to text (Docling)
   b. Chunk text into sections (LegalChunker)
      → produces List[Dict] with "text" and "source"
   c. For each chunk:
      → embed with OpenAI text-embedding-3-large
      → add to Weaviate batch
   d. Batch auto-flushes to Weaviate
4. Flush Redis semantic cache (so cached answers don't mask new data)
5. Close connections
```

### Chunking (LegalChunker)

Legal documents have specific structure (titles, sections, subsections, statutes). The `LegalChunker` (`app/ingestion-worker/src/chunker.py`) respects these boundaries rather than splitting on arbitrary character counts.

```
Input PDF: "USC Title 18 - Crimes and Criminal Procedure"

Output chunks:
  [0] { text: "§ 1341 Frauds and swindles. Whoever, having devised...",
        source: "USC Title 18 § 1341" }
  [1] { text: "§ 1342 Fictitious name or address. Whoever...",
        source: "USC Title 18 § 1342" }
  ...
```

---

## HNSW Index (How Vector Search Works)

HNSW (Hierarchical Navigable Small World) is the algorithm Weaviate uses for approximate nearest neighbor search:

```
Layer 3 (few nodes, long-range connections):
    A ──────────────── F

Layer 2 (more nodes, medium connections):
    A ──── C ──── F ──── H

Layer 1 (many nodes, short connections):
    A ─ B ─ C ─ D ─ E ─ F ─ G ─ H

Layer 0 (all nodes, nearest connections):
    A─B─C─D─E─F─G─H─I─J─K─...
```

**Search:** Start at the top layer, greedily follow the nearest neighbor at each layer, descend to the next layer at each hop. At layer 0, do a local search around the landing point. This is O(log n) instead of O(n) for brute-force scanning.

**Trade-offs:**

| Parameter | Higher value | Lower value |
| --- | --- | --- |
| `efConstruction` | Better index quality, slower build | Faster build, worse recall |
| `maxConnections` | More memory, better recall | Less memory, lower recall |
| `ef` (query time) | Better recall, slower queries | Faster queries, lower recall |

Weaviate's defaults are tuned for a good balance. For 100K legal document chunks, HNSW provides > 99% recall with < 20ms query time.

---

## Configuration

| Variable | Default | Service | Description |
| --- | --- | --- | --- |
| `WEAVIATE_URL` | `http://localhost:8080` | both | Weaviate HTTP endpoint |
| `WEAVIATE_CLASS_NAME` | `document_chunk_embedding` | both | Collection name |
| `OPENAI_API_KEY` | (required) | both | For computing embeddings |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-large` | both | Embedding model (3072 dims) |

Both services **must** use the same `WEAVIATE_CLASS_NAME` and `OPENAI_EMBEDDING_MODEL`. If the ingestion worker writes with `text-embedding-3-large` (3072 dims) but chat-api queries with `text-embedding-3-small` (1536 dims), the vector distances will be meaningless and retrieval will return garbage.

---

## Weaviate Environment Variables

From `docker-compose.yml`:

| Variable | Value | Description |
| --- | --- | --- |
| `QUERY_DEFAULTS_LIMIT` | `25` | Default result count for queries |
| `AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED` | `true` | No auth required (internal network) |
| `PERSISTENCE_DATA_PATH` | `/var/lib/weaviate` | Where Weaviate stores its data files |
| `DEFAULT_VECTORIZER_MODULE` | `none` | No built-in vectorizer (self-provided) |
| `ENABLE_MODULES` | (empty) | No extra modules |
| `CLUSTER_HOSTNAME` | `node1` | Cluster node identifier |

---

## Storage and Performance

### Per-chunk storage cost

```
Vector:       3072 × 4 bytes = 12,288 bytes ≈ 12 KB
Properties:   ~200-500 bytes (text chunk + source)
HNSW graph:   ~1-2 KB per node (connections metadata)
Total:        ~14-15 KB per chunk
```

### Scaling

| Chunks | Storage | HNSW index RAM | Query latency |
| --- | --- | --- | --- |
| 10,000 | ~150 MB | ~120 MB | < 5ms |
| 100,000 | ~1.5 GB | ~1.2 GB | < 20ms |
| 1,000,000 | ~15 GB | ~12 GB | < 50ms |

**Important:** HNSW keeps the entire graph in memory for fast traversal. For 1M chunks, you need at least 12 GB of RAM for Weaviate. Plan your Kubernetes resource limits accordingly.

---

## Health Check

```yaml
healthcheck:
  test: ["CMD", "wget", "-q", "-O", "-", "http://localhost:8080/v1/.well-known/ready"]
  interval: 5s
  timeout: 3s
  retries: 5
  start_period: 10s
```

The `/v1/.well-known/ready` endpoint returns 200 when Weaviate has finished loading its HNSW index into memory and is ready to serve queries. During startup with large datasets, this can take 30+ seconds as the index is loaded from disk.

---

## Backup and Recovery

Weaviate stores data on disk at `PERSISTENCE_DATA_PATH` (`/var/lib/weaviate`). In Kubernetes, this is backed by a PersistentVolumeClaim (EBS volume).

**Backup strategy:**
1. EBS snapshots (automated via AWS Backup) — captures the entire volume
2. Weaviate backup API: `POST /v1/backups/{backend}` supports S3, GCS, filesystem

**Recovery:**
- From EBS snapshot: restore the PVC from the snapshot
- From Weaviate backup: `POST /v1/backups/{backend}/{id}/restore`

**Alternative:** Re-run the ingestion pipeline. If you still have the source PDFs, re-ingesting is simpler than managing backups. This takes time and costs OpenAI API calls for re-embedding, but is operationally simpler.
