from pathlib import Path
from typing import List, Dict

from config import DOCS_DIR, CHUNK_SIZE, CHUNK_OVERLAP


def read_markdown_files() -> List[Dict]:
    documents = []
    for file_path in sorted(DOCS_DIR.glob("*.md")):
        text = file_path.read_text(encoding="utf-8").strip()
        if not text:
            continue
        documents.append(
            {
                "source": file_path.name,
                "path": str(file_path),
                "text": text,
            }
        )
    return documents


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> List[str]:
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = end - chunk_overlap

    return chunks


def create_chunks() -> List[Dict]:
    documents = read_markdown_files()
    all_chunks = []
    for document in documents:
        chunks = chunk_text(document["text"])
        for chunk_number, chunk in enumerate(chunks):
            all_chunks.append(
                {
                    "source": document["source"],
                    "chunk_id": chunk_number,
                    "text": chunk,
                }
            )
    return all_chunks


if __name__ == "__main__":
    chunks = create_chunks()
    print(f"Documents found: {len(read_markdown_files())}")
    print(f"Chunks created: {len(chunks)}")
    for chunk in chunks[:3]:
        print("\n---")
        print(chunk["source"])
        print(chunk["text"][:300])