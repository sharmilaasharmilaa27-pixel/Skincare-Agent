from typing import List, Dict, Any, Optional
import json
import os
import re
import math
from datetime import datetime
from pathlib import Path

from config import (
    DOCS_DIR,
    get_gemini_client,
    GEMINI_EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
    TOP_K,
    PINECONE_INDEX_NAME,
)
from embedder import embed_query
from store import query_index, get_or_create_index

BASE_DIR = Path(__file__).resolve().parent
ESCALATION_LOG_PATH = BASE_DIR / "escalations.log"
MEMORY_PATH = BASE_DIR / "memory.json"

from rank_bm25 import BM25Okapi


def _tokenize(text: str) -> List[str]:
    return re.findall(r'\b\w+\b', text.lower())


def _get_all_docs_for_bm25() -> List[str]:
    documents = []
    for file_path in sorted(DOCS_DIR.glob("*.md")):
        text = file_path.read_text(encoding="utf-8").strip()
        if text:
            documents.append(text)
    return documents


def _get_bm25_scores(query: str, documents: List[str]) -> List[float]:
    tokenized_corpus = [_tokenize(doc) for doc in documents]
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = _tokenize(query)
    scores = bm25.get_scores(tokenized_query)
    return scores.tolist()


def _reciprocal_rank_fusion(
    semantic_results: List[Dict],
    keyword_scores: List[float],
    all_texts: List[str],
    k: int = 60,
) -> List[Dict]:
    rrf_scores: Dict[str, float] = {}
    doc_info: Dict[str, Dict] = {}

    for rank, match in enumerate(semantic_results, start=1):
        meta = match.get("metadata", {})
        text = meta.get("text", "")
        if text not in rrf_scores:
            rrf_scores[text] = 0.0
            doc_info[text] = match
        rrf_scores[text] += 1.0 / (rank + k)

    for idx, score in enumerate(keyword_scores):
        text = all_texts[idx]
        if text not in rrf_scores:
            rrf_scores[text] = 0.0
            doc_info[text] = {
                "score": float(score),
                "metadata": {
                    "source": "keyword_match",
                    "text": text,
                },
            }
        rrf_scores[text] += score / (k * math.log(1 + score + 1))

    sorted_texts = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
    results = []
    for text, rrf_score in sorted_texts[:TOP_K]:
        info = doc_info[text]
        info["score"] = rrf_score
        results.append(info)

    return results


def _read_all_doc_texts() -> Dict[str, str]:
    doc_texts = {}
    for file_path in sorted(DOCS_DIR.glob("*.md")):
        doc_texts[file_path.name] = file_path.read_text(encoding="utf-8").strip()
    return doc_texts


INGREDIENT_DB = {
    "niacinamide": {
        "name": "Niacinamide",
        "type": "Vitamin B3",
        "mechanism": "Regulates sebum production, strengthens skin barrier, reduces inflammation, inhibits melanin transfer",
        "benefits": "Controls oil, fades dark spots, reduces redness, improves barrier function, enhances skin elasticity",
        "best_for": "All skin types, especially oily, acne-prone, and sensitive skin",
        "concentration": "2% to 10%",
        "compatible_with": ["Retinol", "Vitamin C", "Hyaluronic Acid", "Ceramides", "Peptides"],
        "side_effects": "Rare; mild flushing at high concentrations initially",
        "usage": "Daily, morning and night. Apply after cleansing, before moisturizer.",
    },
    "retinol": {
        "name": "Retinol",
        "type": "Vitamin A derivative",
        "mechanism": "Accelerates cell turnover, stimulates collagen production, normalizes desquamation",
        "benefits": "Reduces fine lines and wrinkles, treats acne, fades hyperpigmentation, improves skin texture",
        "best_for": "Normal to oily skin; sensitive skin should start low",
        "concentration": "OTC 0.25% to 0.5%; prescription 0.025% to 0.1%",
        "compatible_with": ["Niacinamide", "Ceramides", "Hyaluronic Acid", "Moisturizer"],
        "side_effects": "Dryness, peeling, redness, irritation (retinoid purge lasting 4-6 weeks)",
        "usage": "Start 2x per week on alternating nights, gradually increase. PM only. Always use SPF the next morning.",
    },
    "hyaluronic acid": {
        "name": "Hyaluronic Acid",
        "type": "Humectant",
        "mechanism": "Powerful humectant that binds up to 1000x its weight in water",
        "benefits": "Deep hydration, plumping effect, improves skin texture, reduces appearance of fine lines",
        "best_for": "All skin types, especially dry and dehydrated skin",
        "concentration": "0.5% to 2% in serums",
        "compatible_with": ["All ingredients including retinoids, vitamin C, niacinamide, ceramides"],
        "side_effects": "None significant; can feel tacky if over-applied",
        "usage": "Apply to damp skin. Layer under moisturizer to lock in hydration.",
    },
    "salicylic acid": {
        "name": "Salicylic Acid",
        "type": "Beta-hydroxy acid (BHA)",
        "mechanism": "Oil-soluble BHA that penetrates pores, dissolves excess oil and dead skin cells",
        "benefits": "Treats and prevents acne, reduces blackheads and whiteheads, exfoliates surface, anti-inflammatory",
        "best_for": "Oily, acne-prone, combination skin",
        "concentration": "0.5% to 2%",
        "compatible_with": ["Niacinamide", "Moisturizer", "Ceramides"],
        "side_effects": "Dryness, peeling, mild irritation with overuse",
        "usage": "1-2x daily for acne treatment. Apply after cleansing, before moisturizer.",
    },
    "benzoyl peroxide": {
        "name": "Benzoyl Peroxide",
        "type": "Antibacterial agent",
        "mechanism": "Kills Cutibacterium acnes bacteria, reduces inflammation, mild comedolytic properties",
        "benefits": "Treats inflammatory acne, prevents new breakouts, reduces redness",
        "best_for": "Acne-prone skin, especially inflammatory acne",
        "concentration": "2.5% to 10%",
        "compatible_with": ["Retinoids (at different times), Niacinamide, Moisturizer"],
        "side_effects": "Dryness, peeling, redness, bleaching of fabrics",
        "usage": "Apply thin layer to affected areas after cleansing. Start every other day.",
    },
    "vitamin c": {
        "name": "Vitamin C (L-Ascorbic Acid)",
        "type": "Antioxidant",
        "mechanism": "Neutralizes free radicals, inhibits melanin synthesis, co-factor for collagen production",
        "benefits": "Brightens skin, fades hyperpigmentation, protects against UV/sun damage, boosts collagen",
        "best_for": "All skin types, especially dull, uneven tone, or sun-damaged skin",
        "concentration": "10% to 20% L-ascorbic acid",
        "compatible_with": ["Vitamin E", "Ferulic acid", "Niacinamide", "Sunscreen", "Hyaluronic Acid"],
        "side_effects": "Mild tingling at higher concentrations; irritation above 20%",
        "usage": "AM routine after cleansing, before moisturizer and sunscreen.",
    },
    "ceramides": {
        "name": "Ceramides",
        "type": "Lipid molecule",
        "mechanism": "Form the protective lipid matrix of the stratum corneum",
        "benefits": "Restore skin barrier, prevent transepidermal water loss, reduce sensitivity, improve hydration",
        "best_for": "All skin types, especially dry, sensitive, eczema-prone, and barrier-compromised skin",
        "concentration": "Included in moisturizers at effective barrier-repair levels",
        "compatible_with": ["All ingredients; best paired with cholesterol and fatty acids in 1:1:1 ratio"],
        "side_effects": "None; extremely well-tolerated",
        "usage": "Daily, morning and night as part of moisturizer routine.",
    },
    "azelaic acid": {
        "name": "Azelaic Acid",
        "type": "Dicarboxylic acid",
        "mechanism": "Inhibits tyrosinase, has anti-inflammatory and antimicrobial properties",
        "benefits": "Treats acne, reduces redness and inflammation, fades hyperpigmentation, gentle exfoliation",
        "best_for": "Sensitive, acne-prone, rosacea-prone skin; suitable for all skin types",
        "concentration": "10% OTC, 15% to 20% prescription",
        "compatible_with": ["Niacinamide", "Retinol (at different times)", "Ceramides", "Sunscreen"],
        "side_effects": "Mild tingling or itching initially; well-tolerated overall",
        "usage": "1-2x daily after cleansing. Can be used long-term.",
    },
    "squalane": {
        "name": "Squalane",
        "type": "Lightweight oil",
        "mechanism": "Mimics skin's natural sebum; emollient and antioxidant",
        "benefits": "Deep hydration without clogging pores, antioxidant protection, improves skin texture, balances oil production",
        "best_for": "All skin types, especially oily, combination, and acne-prone skin",
        "concentration": "1% to 100% in serums and moisturizers",
        "compatible_with": ["All ingredients; excellent carrier for other active ingredients"],
        "side_effects": "None; non-comedogenic and highly tolerable",
        "usage": "2-3 drops after serum, before moisturizer. AM and PM.",
    },
    "peptides": {
        "name": "Peptides",
        "type": "Amino acid chains",
        "mechanism": "Signal fibroblasts to produce collagen and elastin",
        "benefits": "Improve skin firmness, reduce fine lines, support wound healing, enhance skin elasticity",
        "best_for": "All skin types, especially aging, mature, or thinning skin",
        "concentration": "1% to 10% depending on peptide type",
        "compatible_with": ["Vitamin C", "Niacinamide", "Retinol", "Ceramides", "Hyaluronic Acid", "Sunscreen"],
        "side_effects": "None significant; extremely gentle",
        "usage": "Daily in serum or moisturizer step. AM and PM.",
    },
    "centella asiatica": {
        "name": "Centella Asiatica (Cica)",
        "type": "Botanical extract",
        "mechanism": "Contains asiaticoside, madecassoside that promote wound healing, reduce inflammation, stimulate collagen",
        "benefits": "Calms irritated skin, reduces redness, repairs damaged barriers, promotes wound healing",
        "best_for": "Sensitive, reactive, irritated skin; excellent for barrier repair",
        "concentration": "1% to 10% in formulations",
        "compatible_with": ["Niacinamide", "Ceramides", "Hyaluronic Acid", "Sunscreen"],
        "side_effects": "None significant; extremely gentle",
        "usage": "Daily as a serum or treatment step. AM and PM.",
    },
}

SKIN_ROUTINES = {
    "oily": {
        "morning": "Gentle cleanser → Salicylic Acid treatment → Lightweight moisturizer → SPF 30+",
        "evening": "Double cleanse → Niacinamide serum → Lightweight moisturizer → Retinol (2-3x per week)",
        "key_ingredients": ["Salicylic Acid", "Niacinamide", "Squalane", "Ceramides"],
        "avoid": ["Heavy occlusives", "Rich creams", "Alcohol-based toners"],
    },
    "dry": {
        "morning": "Gentle cream cleanser → Hyaluronic Acid serum → Rich ceramide moisturizer → SPF 30+",
        "evening": "Gentle cleanser → Hyaluronic Acid serum → Rich moisturizer with ceramides → Occlusive if needed",
        "key_ingredients": ["Hyaluronic Acid", "Ceramides", "Squalane", "Panthenol"],
        "avoid": ["Salicylic Acid (high %)", "Alcohol", "Harsh exfoliants"],
    },
    "sensitive": {
        "morning": "Fragrance-free gentle cleanser → Centella Asiatica serum → Ceramide moisturizer → Mineral SPF 30+",
        "evening": "Gentle cleanser → Centella Asiatica → Ceramide moisturizer → Gentle peptides",
        "key_ingredients": ["Centella Asiatica", "Ceramides", "Niacinamide", "Panthenol"],
        "avoid": ["Fragrance", "Essential oils", "Strong acids", "Retinoids (initially)", "Alcohol"],
    },
    "combination": {
        "morning": "Gentle cleanser → Niacinamide serum → Lightweight moisturizer → SPF 30+",
        "evening": "Gentle cleanser → Niacinamide → Lightweight moisturizer → Retinol (2-3x per week)",
        "key_ingredients": ["Niacinamide", "Hyaluronic Acid", "Squalane", "Ceramides"],
        "avoid": ["Overly drying products", "Heavy creams on T-zone"],
    },
    "normal": {
        "morning": "Gentle cleanser → Vitamin C serum → Lightweight moisturizer → SPF 30+",
        "evening": "Gentle cleanser → Niacinamide or Vitamin C (alternate) → Moisturizer → Retinol (2-3x per week)",
        "key_ingredients": ["Niacinamide", "Vitamin C", "Peptides", "Ceramides"],
        "avoid": ["Over-exfoliation", "Too many actives at once"],
    },
}


def search_docs(query: str) -> str:
    """Hybrid search: Pinecone semantic + rank-bm25 keyword, fused together."""
    query_embedding = embed_query(query)
    semantic_results = query_index(query_embedding, top_k=TOP_K)
    matches = semantic_results.get("matches", [])

    all_texts = _get_all_docs_for_bm25()
    keyword_scores = _get_bm25_scores(query, all_texts)

    fused = _reciprocal_rank_fusion(matches, keyword_scores, all_texts)

    if not fused:
        return "No relevant results found."

    lines = []
    for i, result in enumerate(fused, start=1):
        meta = result.get("metadata", {})
        source = meta.get("source", "Unknown")
        text = meta.get("text", "")[:300]
        score = result.get("score", 0.0)
        lines.append(f"[{i}] Source: {source} (score: {score:.4f})\n{text}")

    return "\n\n".join(lines)


def lookup_ingredient(name: str) -> str:
    """Look up a specific skincare ingredient from the local database."""
    if name.lower().strip() == "broken_test":
        raise ValueError("Simulated error: ingredient lookup failed.")

    name_lower = name.lower().strip()
    for key, info in INGREDIENT_DB.items():
        if name_lower in key.lower() or key.lower() in name_lower:
            details = [
                f"**{info['name']}** ({info['type']})",
                f"Mechanism: {info['mechanism']}",
                f"Benefits: {info['benefits']}",
                f"Best for: {info['best_for']}",
                f"Concentration: {info['concentration']}",
                f"Compatible with: {', '.join(info['compatible_with'])}",
                f"Side effects: {info['side_effects']}",
                f"Usage: {info['usage']}",
            ]
            return "\n".join(details)

    return f"Ingredient '{name}' not found in the database. Try searching the docs for more information."


def get_routine(skin_type: str) -> str:
    """Get a personalized skincare routine for a given skin type."""
    skin_type_lower = skin_type.lower().strip()
    for key, routine in SKIN_ROUTINES.items():
        if skin_type_lower in key.lower() or key.lower() in skin_type_lower:
            return (
                f"Routine for **{key} skin**:\n\n"
                f"🌅 Morning:\n{routine['morning']}\n\n"
                f"🌙 Evening:\n{routine['evening']}\n\n"
                f"Key ingredients: {', '.join(routine['key_ingredients'])}\n"
                f"Avoid: {', '.join(routine['avoid'])}"
            )

    return (
        f"Skin type '{skin_type}' not recognized. "
        f"Known types: {', '.join(SKIN_ROUTINES.keys())}. "
        f"Try searching the docs for your skin type."
    )


def escalate(reason: str) -> str:
    """Append-only escalation log. Returns a ticket ID."""
    os.makedirs(os.path.dirname(ESCALATION_LOG_PATH), exist_ok=True)
    timestamp = datetime.now().isoformat()
    ticket_id = f"ESC-{timestamp.replace(':', '-')}"

    with open(ESCALATION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(
            f"{ticket_id}\t{timestamp}\t{reason}\n"
        )

    return f"Escalated as {ticket_id}. A human agent will review this shortly."


def build_tool_schemas() -> List[Dict]:
    return [
        {
            "function": {
                "name": "search_docs",
                "description": "Search the skincare knowledge base using hybrid semantic and keyword search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The skincare question or topic to search for.",
                        }
                    },
                    "required": ["query"],
                },
            }
        },
        {
            "function": {
                "name": "lookup_ingredient",
                "description": "Look up detailed information about a specific skincare ingredient.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "The name of the skincare ingredient to look up.",
                        }
                    },
                    "required": ["name"],
                },
            }
        },
        {
            "function": {
                "name": "get_routine",
                "description": "Get a personalized skincare routine for a given skin type.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "skin_type": {
                            "type": "string",
                            "description": "The skin type (oily, dry, sensitive, combination, normal).",
                        }
                    },
                    "required": ["skin_type"],
                },
            }
        },
        {
            "function": {
                "name": "escalate",
                "description": "Escalate an unresolvable question to a human agent for review.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "The reason for escalation.",
                        }
                    },
                    "required": ["reason"],
                },
            }
        },
    ]