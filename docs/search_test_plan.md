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
    query_text="List industrial friers",
    query_type=SearchType.INSIGHTS,
)

Sample Output:
[
    ("Industrial Frier", "requires", "380V Power Supply"),
    ("Industrial Frier", "has_component", "Thermostat Control Unit"),
    ("Industrial Frier", "manufactured_by", "HeatTech Corp"),
    ("Oil Filtration System", "is_part_of", "Industrial Frier")
]

2. SUMMARIES

What is [SUMMARIES]:

Conducts a vector search on TextSummary (generated from .cognify). Useful when you want concise info over full data chunks.

Output: Dictionary of summary "text" and "made-from" data.
{"made-from": document_trace, "text": document_summary}

Sample Query:
await cognee.search(
    query_text="List industrial friers",
    query_type=SearchType.SUMMARIES,
)

Sample Output:
[
    {
        "made_from": "documents/industrial_frier_manual.pdf",
        "text": "Industrial friers operate at temperatures between 325°F and 375°F and require regular oil filtration. Key components include the thermostat control unit, basket assembly, and oil drainage system. Routine maintenance should be performed every 500 operating hours."
    }
]

3. CHUNKS

What is [CHUNKS]:

Conducts a vector search on text chunks (generated from .cognify). Useful when you want raw sections of data.

Output: Dictionary of chunk data, including "text", "chunk_index", "chunk_size", "is_part_of"

Sample Query:
await cognee.search(
    query_text="List industrial friers",
    query_type=SearchType.CHUNKS,
)

Sample Output:
[
    {
        "text": "The industrial frier unit requires a dedicated 380V power supply and must be installed on a level, heat-resistant surface. Prior to first use, fill the oil reservoir to the indicated MAX line and allow the unit to preheat for 15 minutes.",
        "chunk_index": 3,
        "chunk_size": 247,
        "is_part_of": "documents/industrial_frier_manual.pdf"
    },
    {
        "text": "Thermostat calibration should be verified monthly using an external probe thermometer. If readings deviate by more than ±5°F, contact HeatTech Corp service department for recalibration.",
        "chunk_index": 7,
        "chunk_size": 189,
        "is_part_of": "documents/industrial_frier_manual.pdf"
    }
]

4. GRAPH_COMPLETION

What is [GRAPH_COMPLETION]:

Graph-aware question answering - basically combines vectors and knowledge graph info with an LLM on top to answer the question based on the vector and knowledge graph results.

Output: Natural-language answer with graph references

Sample Query:
await cognee.search(
    query_text="List industrial friers",
)

Sample Output:
[
    "The industrial frier is a commercial cooking unit manufactured by HeatTech Corp. It operates at temperatures between 325°F and 375°F, requires a dedicated 380V power supply, and includes key components such as a thermostat control unit, basket assembly, and oil filtration system. Routine maintenance is recommended every 500 operating hours, including oil filtration and thermostat calibration."
]

5. GRAPH_COMPLETION_COT

What is [GRAPH_COMPLETION_COT]:

Utilizes multiple rounds of graph retrieval and LLM reasoning for refined answers. Useful for complex questions that require reierating.

*COT: Chain-of-Thought

Output: Natural-language answer with multiple reasoning steps

Sample Query:
await cognee.search(
    query_text="List industrial friers",
    query_type=SearchType.GRAPH_COMPLETION_COT,
)

Sample Output:
[
    "Step 1: Identified 'Industrial Frier' as a primary entity with connections to power requirements, components, and manufacturer.",
    "Step 2: Retrieved maintenance schedule details — routine service every 500 operating hours, monthly thermostat calibration.",
    "Step 3: Cross-referenced oil filtration system as a subcomponent linked to both maintenance procedures and daily operation guidelines.",
    "Final Answer: The industrial frier is manufactured by HeatTech Corp and requires a 380V power supply. It operates between 325°F and 375°F. Core components include the thermostat control unit, basket assembly, and oil filtration system. Maintenance involves oil filtration and thermostat calibration every 500 hours, with monthly verification using an external probe thermometer."
]