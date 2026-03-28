## SearchType Research and Test Plan

### Cognee .search()

Just as a quick review, the cognee .search function allows you to query information after running .add and .cognify to create a knowledge graph.

Cognee uses a hybrid retrieval method (ie. implementing vectors, graphs, and LLMs) for higher accuracy. 

The five main search types that Cortex will utilize are INSIGHTS, SUMMARIES, CHUNKS, GRAPH_COMPLETIION, GRAPH_COMPLETION_COT. See below for information on what each SearchType does and how to query with them. 

*If no SearchType is identified, cognee will default to SearchType.GRAPH_COMPLETION

### Search Types

1. INSIGHTS

What is [INSIGHTS]:

* INSIGHTS was not listed as a SearchType in the official cognee docs.
(info is pulled from https://dev.to/chinmay_bhosale_9ceed796b/search-types-in-cognee-1jo7)

Conducts a vector search, finds relevant entities, and then returns the connecting edges on the graph. Allows for better understanding of knowledge graph.

Output: Raw relationship data, 
ie. Entity A --[relationship_type]--> Entity B

Sample Query:

await cognee.search(
    query_text="List coding guidelines",
    query_type=SearchType.INSIGHTS,
)

2. SUMMARIES

What is [SUMMARIES]:

Conducts a vector search on TextSummary (generated from .cognify). Useful when you want concise info over full data chunks.

Output: Dictionary of summary "text" and "made-from" data.
{"made-from": document_trace, "text": document_summary}

Sample Query:

await cognee.search(
    query_text="List coding guidelines",
    query_type=SearchType.SUMMARIES,
)

3. CHUNKS

What is [CHUNKS]:

Conducts a vector search on text chunks (generated from .cognify). Useful when you want raw sections of data.

Output: Dictionary of chunk data, including "text", "chunk_index", "chunk_size", "is_part_of"

Sample Query:

await cognee.search(
    query_text="List coding guidelines",
    query_type=SearchType.CHUNKS,
)

4. GRAPH_COMPLETION

What is [GRAPH_COMPLETION]:

Graph-aware question answering - basically combines vectors and knowledge graph info with an LLM on top to answer the question based on the vector and knowledge graph results.

Output: Natural-language answer with graph references

Sample Query:

await cognee.search(
    query_text="List coding guidelines",
)

5. GRAPH_COMPLETION_COT

What is [GRAPH_COMPLETION_COT]:

Utilizes multiple rounds of graph retrieval and LLM reasoning for refined answers. Useful for complex questions that require reierating.

*COT: Chain-of-Thought

Output: Natural-language answer with multiple reasoning steps

Sample Query:

await cognee.search(
    query_text="List coding guidelines",
    query_type=SearchType.GRAPH_COMPLETION_COT,
)