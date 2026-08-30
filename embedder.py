from typing import List

from google.genai import types

from config import (
    gemini_client,
    GEMINI_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
)


def embed_documents(
    texts: List[str],
    batch_size: int = 50,
) -> List[List[float]]:
    all_embeddings = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        response = gemini_client.models.embed_content(
            model=GEMINI_EMBEDDING_MODEL,
            contents=batch,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_DOCUMENT",
                output_dimensionality=EMBEDDING_DIMENSION,
            ),
        )
        batch_embeddings = [
            embedding.values
            for embedding in response.embeddings
        ]
        all_embeddings.extend(batch_embeddings)
        print(
            f"Embedded {min(start + batch_size, len(texts))}"
            f"/{len(texts)} chunks"
        )
    return all_embeddings


def embed_query(query: str) -> List[float]:
    response = gemini_client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=[query],
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSION,
        ),
    )
    return response.embeddings[0].values