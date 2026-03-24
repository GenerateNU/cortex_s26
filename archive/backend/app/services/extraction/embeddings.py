import json

from app.core.litellm import EmbeddingModelType, LLMClient

# Initialize client with Gemini embeddings
client = LLMClient()
client.set_embedding_model(EmbeddingModelType.GEMINI_TEXT_EMBEDDING)


async def generate_embedding(extracted_json: dict) -> list[float]:
    """
    Generate embedding for entire document.
    Converts JSON to text representation for embedding.

    Returns 768-dimensional vector (Gemini default)
    """
    # Convert JSON to structured text
    text = _json_to_text(extracted_json)

    # Generate embedding using Gemini
    embedding = await client.embed(text)

    return embedding


def _json_to_text(data: dict) -> str:
    """
    Convert extracted JSON to readable text format.
    Better than json.dumps() for semantic meaning.
    """
    parts = []

    # If the input is actually the full result wrapper
    if "result" in data:
        result = data["result"]
        if "file_name" in data:
            parts.append(f"Document: {data['file_name']}")
    else:
        # Input is already the inner result
        result = data

    # Process the result dictionary/list
    if isinstance(result, dict):
        for key, value in result.items():
            if isinstance(value, dict | list):
                parts.append(f"{key}: {json.dumps(value)}")
            else:
                parts.append(f"{key}: {value}")

    elif isinstance(result, list):
        parts.append(f"Content structure: {json.dumps(result)}")

    else:
        parts.append(f"Content: {str(result)}")

    return "\n".join(parts)
