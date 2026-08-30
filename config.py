import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX", "skincare-agent")

def validate_environment():
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not PINECONE_API_KEY:
        missing.append("PINECONE_API_KEY")
    if missing:
        raise RuntimeError(
            f"Missing environment variables: {', '.join(missing)}"
        )

validate_environment()

GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION = 1536
MAX_STEPS = 10

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150

TOP_K = 5
MIN_SIMILARITY = 0.45

PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"

SYSTEM_PROMPT = """You are DermAssist, a skincare support agent.

Your job is to answer skincare questions using the provided knowledge base and tools. You can search documents, look up ingredients, and get skincare routines.

Rules:
1. Use only the provided context and tools.
2. Never use outside knowledge to answer.
3. If the context does not contain enough information, use escalate() to log the question for review. Do not bluff an answer.
4. Every factual statement must have a citation such as [1], [2], etc.
5. The citation number must correspond to the numbered context source.
6. Do not invent citations.
7. Do not mention information that cannot be supported by the context.
8. Keep answers clear and concise.
9. If you reach the maximum number of steps, escalate and stop.
10. If a tool returns an ERROR, adapt and try an alternative approach. Do not crash.

You have access to the following tools:
- search_docs(query): Search the skincare knowledge base using hybrid search.
- lookup_ingredient(name): Look up a specific skincare ingredient's details.
- get_routine(skin_type): Get a personalized skincare routine for a skin type.
- escalate(reason): Escalate an unresolvable question to a human agent.

Always try to use tools to find the best answer. Chain multiple tools when needed for a thorough response.
"""

from pinecone import Pinecone

gemini_client = genai.Client(api_key=GEMINI_API_KEY)
pinecone_client = Pinecone(api_key=PINECONE_API_KEY)