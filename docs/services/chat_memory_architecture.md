# Chat Memory Architecture

## 1. Architectural Overview

Modern Large Language Models (LLMs) are inherently stateless. To create conversational agents that "remember" past interactions without exhausting system RAM, applications must externalize their state.

Using **Apache Cassandra** as the chat memory persistence layer allows you to decouple the memory from the application server. In this architecture, the chat application remains stateless, fetching necessary context from Cassandra just-in-time, calling the LLM, and asynchronously writing the new interaction back to the database.

## 2. Core Components

- **Client / User Interface:** The front-end where the user interacts with the chatbot.
- **Application / Orchestration Layer (e.g., LangChain, Spring AI):** The middleware that manages the conversation flow, orchestrates database reads/writes, and handles prompt construction.
- **Cassandra Persistence Layer:** A highly available, distributed NoSQL database used to store the raw message history, session metadata, and context.
- **Large Language Model (LLM):** The AI engine that processes the injected context and generates a response.

## 3. Cassandra Data Model Architecture

To ensure high performance and low-latency message retrieval, the data model in Cassandra is optimized around the query pattern rather than relational normalization.

- **Partition Key (`session_id`):** All messages belonging to a specific conversation or user session share the same partition key. This guarantees that an entire chat history is stored contiguously on the same physical node (and its replicas), making retrieval extremely fast.
- **Clustering Column (`timestamp` or `TimeUUID`):** Messages within a session partition are ordered chronologically by default. This allows the application to efficiently slice the data (e.g., "fetch only the last 10 messages").
- **Time-To-Live (TTL):** Cassandra's native TTL feature is heavily utilized at the row level. Chat memories can be configured to automatically expire and self-delete after a specific period of inactivity, effortlessly managing storage costs and adhering to data privacy policies.

## 4. System Flow

1.  **Ingestion:** A user submits a new message to the chat application.
2.  **Context Retrieval:** The orchestrator queries the Cassandra cluster using the current `session_id` to retrieve the recent conversational history (or a summarized context window).
3.  **Prompt Construction:** The retrieved history is appended to the current prompt alongside the system instructions and the new user message.
4.  **LLM Execution:** The combined prompt is sent to the LLM.
5.  **Persistence:** The orchestrator writes both the user's original message and the LLM's generated response back to the Cassandra database. This is typically done asynchronously to prevent blocking the user experience.

## 5. Why Cassandra for Chat Memory?

- **Massive Write Scalability:** Chat applications are highly write-intensive. Cassandra's Log-Structured Merge-tree (LSM) architecture easily handles millions of concurrent message writes without performance degradation.
- **High Availability & Fault Tolerance:** The masterless, peer-to-peer architecture ensures there is no single point of failure. If a node goes down, chat histories remain accessible via replica nodes.
- **Global Distribution:** Cassandra natively supports multi-datacenter replication. This allows global chat applications to serve user memory locally from the closest geographic region, drastically reducing latency.
- **Built-in Data Expiration:** Native TTLs mean application developers do not need to build background jobs to clean up stale or abandoned chat sessions.
