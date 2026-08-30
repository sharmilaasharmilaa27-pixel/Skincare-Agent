from typing import List, Dict

from pinecone import ServerlessSpec

from config import (
    pinecone_client,
    PINECONE_INDEX_NAME,
    EMBEDDING_DIMENSION,
    PINECONE_CLOUD,
    PINECONE_REGION,
    TOP_K,
)


def get_or_create_index():
    existing_indexes = pinecone_client.list_indexes()
    index_names = [index["name"] for index in existing_indexes]

    if PINECONE_INDEX_NAME not in index_names:
        print(f"Creating Pinecone index: {PINECONE_INDEX_NAME}")
        pinecone_client.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(
                cloud=PINECONE_CLOUD,
                region=PINECONE_REGION,
            ),
        )

    return pinecone_client.Index(PINECONE_INDEX_NAME)


def build_vector_id(source: str, chunk_id: int) -> str:
    safe_source = source.rsplit(".", 1)[0]
    return f"{safe_source}_{chunk_id}"


def upsert_chunks(
    chunks: List[Dict],
    embeddings: List[List[float]],
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            "Number of chunks and embeddings must match."
        )

    index = get_or_create_index()
    vectors = []

    for chunk, embedding in zip(chunks, embeddings):
        vector_id = build_vector_id(
            chunk["source"],
            chunk["chunk_id"],
        )
        vectors.append(
            {
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "source": chunk["source"],
                    "chunk_id": chunk["chunk_id"],
                    "text": chunk["text"],
                },
            }
        )

    batch_size = 100
    for start in range(0, len(vectors), batch_size):
        batch = vectors[start:start + batch_size]
        index.upsert(vectors=batch)

    return len(vectors)


def query_index(
    embedding: List[float],
    top_k: int = TOP_K,
):
    index = get_or_create_index()
    results = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
    )
    return results


def get_vector_count() -> int:
    index = get_or_create_index()
    stats = index.describe_index_stats()
    return stats.total_vector_count