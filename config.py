import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_FALLBACK_API_KEY = os.getenv("GEMINI_FALLBACK_API_KEY", GEMINI_API_KEY)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX", "skincare-agent")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_DIMENSION = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
MAX_STEPS = int(os.getenv("MAX_STEPS", "6"))

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))

TOP_K = int(os.getenv("TOP_K", "5"))
MIN_SIMILARITY = float(os.getenv("MIN_SIMILARITY", "0.45"))

PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

MAX_INPUT_LENGTH = int(os.getenv("MAX_INPUT_LENGTH", "500"))
MAX_INPUT_LENGTH_HARD = int(os.getenv("MAX_INPUT_LENGTH_HARD", "2000"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))

CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))
CIRCUIT_BREAKER_RECOVERY_TIMEOUT = int(os.getenv("CIRCUIT_BREAKER_RECOVERY_TIMEOUT", "60"))

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
COST_LOG_PATH = BASE_DIR / "costs.json"

SYSTEM_PROMPT = """
You are a Skincare Support Agent.

TOOL RULES:
1. Use tools to obtain reliable information instead of guessing.
2. For questions about a specific skincare ingredient, use lookup_ingredient.
3. For skincare routines, use get_routine.
4. Use search_docs when additional information from the skincare knowledge base is useful.
5. For multi-part questions, use multiple relevant tools and combine their results.
6. Do not repeatedly call the same tool with the same query.
7. Do not use unnecessary tools when you already have enough information.
8. If the user asks something outside the available knowledge or requires professional medical intervention, use escalate.
9. Never invent skincare information.
10. Keep the final answer clear and concise.
11. Stop once you have enough information to answer the user's question.
"""

_gemini_client: Optional["object"] = None
_pinecone_client: Optional["object"] = None

def validate_environment():
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not PINECONE_API_KEY:
        missing.append("PINECONE_API_KEY")
    if missing:
        raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
    return True

def _init_clients():
    global _gemini_client, _pinecone_client
    validate_environment()
    from google import genai
    from pinecone import Pinecone
    _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    return _gemini_client, _pinecone_client

@property
def gemini_client():
    if _gemini_client is None:
        _init_clients()
    return _gemini_client

@property
def pinecone_client():
    if _pinecone_client is None:
        _init_clients()
    return _pinecone_client

def get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    return _gemini_client

def get_pinecone_client():
    global _pinecone_client
    if _pinecone_client is None:
        from pinecone import Pinecone
        _pinecone_client = Pinecone(api_key=PINECONE_API_KEY)
    return _pinecone_client
