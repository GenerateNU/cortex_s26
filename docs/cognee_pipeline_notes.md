# Cognee Pipeline Notes

## How `cognify()` Chunks a Document

The first processing step is splitting your document into smaller text segments called **chunks**. The default `TextChunker` works in two steps:

1. **Identify paragraph boundaries** — looks for double newlines (`\n\n`).
2. **Group paragraphs up to the token limit** — walks through paragraphs, adding them to the current chunk until the next one would exceed the limit, then starts a new chunk.

If a single paragraph exceeds the token limit, it gets split further.

### Example

Five paragraphs: 300, 200, 400, 500, and 150 tokens. With a 1024-token limit:

- **Chunk 1:** Paragraphs 1+2+3 = 900 tokens (adding Paragraph 4 would exceed 1024)
- **Chunk 2:** Paragraphs 4+5 = 650 tokens

Paragraph breaks determine *where* it can split; the token limit determines *when*.

### Chunk Size Tradeoffs

- **Smaller chunks (256–512):** More precise extraction and sharper search, but more LLM calls and less context.
- **Larger chunks (1500–2000):** More context and fewer LLM calls, but fuzzier embeddings and may miss smaller entities.
- **Default (1024):** Balanced middle ground.

### Other Chunkers

- **`CsvChunker`** — splits by rows, keeping CSV records intact.
- **`LangchainChunker`** — uses hierarchical separators with chunk overlap support.
- **`TextChunkerWithOverlap`** — like TextChunker but with configurable overlap between chunks.

## Entity Extraction and Knowledge Graph

After chunking, each chunk is sent to an LLM with a prompt asking it to identify all named entities (people, companies, products, locations, etc.) and any relationships between them. The LLM reads the chunk text and returns structured output — essentially a list of entities it found and how they relate to each other.

The relationships come back as **triplets**: **subject – relation – object**. For example, from "TechVision manufactures hydraulic pumps":

- **Subject:** TechVision
- **Relation:** manufactures
- **Object:** hydraulic pumps

These triplets are stored as a knowledge graph in **Kuzu** (a graph database at `.cognee_system/databases/kuzu/`). Each entity becomes a **node** and each relationship becomes an **edge** connecting two nodes. So the example above creates two nodes ("TechVision" and "hydraulic pumps") connected by a "manufactures" edge.

This lets Cognee traverse connections across different chunks and documents — even if two entities appear in separate files, the graph links them together.


## Storage Layers

Cognee uses three databases, each serving a different role:

- **SQLite (relational)** — Tracks which documents were ingested, what chunks they were split into, and where everything came from (provenance). Located at `.cognee_system/databases/cognee_db`.
- **LanceDB (vector)** — Stores embeddings (numerical representations of meaning) for every chunk and entity. Powers semantic similarity search — matching by concept, not exact words. Located at `.cognee_system/databases/lancedb/`.
- **KuzuDB (graph)** — Stores entities as nodes and relationships as edges. Powers graph traversal — following connections between concepts across chunks and documents. Located at `.cognee_system/databases/kuzu/`.
```
project_root/
├── .cognee_system/
│   └── databases/
│       ├── kuzu/          # Graph (nodes + edges)
│       ├── lancedb/       # Vectors (embeddings)
│       └── cognee_db      # Relational (metadata, provenance)
```
## Search Types

Cognee's `cognee.search()` supports multiple `SearchType` variants that control how results are retrieved:

**`SUMMARIES`** — Returns pre-generated summary nodes created during `cognify()`. It runs a vector similarity search against stored summaries and returns the most relevant ones. No LLM call happens at query time since the summaries were already created during processing, making this fast. Use this when you need a quick high-level overview of a topic.

*In short: summaries are pre-made and embedded during cognify(). Searching just matches your query against those summary embeddings.*

**`CHUNKS`** — Returns the raw text segments stored during ingestion, found via vector similarity search. This is the fastest search type since it skips both graph traversal and LLM generation. Use this when you need the original source text or want to trace exactly where an answer came from.

*In short: returns the original source text, fastest option.*

**`INSIGHTS`** — Returns structured relationship triplets directly from the knowledge graph. It finds relevant entities via vector search, then traverses the graph to extract their connections, returning results like "TechVision –[manufactures]→ hydraulic pumps." Use this when you want to see how entities relate to each other without generating a natural language answer.

*In short: returns relationship triplets (subject–relation–object) from the graph.*

**`GRAPH_COMPLETION`** — The most sophisticated type. It runs vector search across chunks, summaries, and entities, builds a small subgraph of related edges, converts that subgraph to plain text, and passes it to an LLM to generate a natural language answer. Use this when you want an intelligent response that understands how concepts connect through the graph.

*In short: finds relevant graph context and has an LLM generate a natural language answer.*

**`GRAPH_COMPLETION_COT`** — Same as `GRAPH_COMPLETION` but with chain-of-thought reasoning. After an initial answer, it generates follow-up questions, retrieves additional graph context, and refines the answer over multiple rounds. Use this for complex questions that benefit from stepwise reasoning.

*In short: same as above but the LLM goes through multiple rounds of reasoning before returning a final answer.*

### Which Type for What

For **structured extraction** (pulling specific data or source text): use `SUMMARIES` or `CHUNKS` — they return stored content directly without LLM generation.

For **relationship search** (exploring how entities connect): use `INSIGHTS` — it returns triplets straight from the knowledge graph.

For **question answering** (getting a natural language response): use `GRAPH_COMPLETION` or `GRAPH_COMPLETION_COT` — they combine graph context with LLM reasoning.