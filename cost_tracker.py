import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List
from collections import defaultdict

COST_LOG_PATH = Path(__file__).resolve().parent / "costs.json"

MODEL_PRICING = {
    "gemini-3.6-flash": {"input_per_1k": 0.0001, "output_per_1k": 0.0001, "label": "Gemini Flash (primary)"},
    "gemini-2.0-flash": {"input_per_1k": 0.00008, "output_per_1k": 0.00008, "label": "Gemini 2.0 Flash (fallback)"},
}

class CostRecord:
    def __init__(self, timestamp, model, input_tokens, output_tokens, cost_usd, category="chat", session_id="default"):
        self.timestamp = timestamp
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost_usd = cost_usd
        self.category = category
        self.session_id = session_id

    def to_dict(self) -> Dict:
        return {"timestamp": self.timestamp, "model": self.model, "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens, "cost_usd": self.cost_usd, "category": self.category, "session_id": self.session_id}

class CostTracker:
    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.records: List = []
        self._load()
        self._current_model = "gemini-3.6-flash"
        self._current_input_tokens = 0
        self._current_output_tokens = 0
        self._current_category = "chat"

    def _load(self):
        if COST_LOG_PATH.exists():
            try:
                with open(COST_LOG_PATH) as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self.records = [CostRecord(**item) for item in data]
            except Exception:
                pass

    def _save(self):
        with open(COST_LOG_PATH, "w") as f:
            json.dump([r.to_dict() for r in self.records], f, indent=2)

    def start_call(self, model: str, input_tokens_est: int, category: str = "chat"):
        self._current_model = model
        self._current_input_tokens = input_tokens_est
        self._current_category = category

    def end_call(self, output_tokens: int, actual_model: Optional[str] = None):
        model = actual_model or self._current_model
        output = output_tokens or self._current_output_tokens
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["gemini-3.6-flash"])
        input_cost = (self._current_input_tokens / 1000) * pricing["input_per_1k"]
        output_cost = (output / 1000) * pricing["output_per_1k"]
        total_cost = input_cost + output_cost
        record = CostRecord(datetime.now().isoformat(), model, self._current_input_tokens,
                           output, round(total_cost, 6), self._current_category, self.session_id)
        self.records.append(record)
        self._save()
        return record

    def get_session_cost(self) -> Dict:
        session_records = [r for r in self.records if r.session_id == self.session_id]
        total = sum(r.cost_usd for r in session_records)
        by_model = defaultdict(float)
        for r in session_records:
            by_model[r.model] += r.cost_usd
        return {"total_cost_usd": round(total, 4), "total_calls": len(session_records), "by_model": dict(by_model), "session_id": self.session_id}

    def get_overall_cost(self) -> Dict:
        total = sum(r.cost_usd for r in self.records)
        by_model = defaultdict(float)
        by_category = defaultdict(float)
        for r in self.records:
            by_model[r.model] += r.cost_usd
            by_category[r.category] += r.cost_usd
        return {"total_cost_usd": round(total, 4), "total_calls": len(self.records), "by_model": dict(by_model), "by_category": dict(by_category)}

    def get_cost_levers(self) -> List[Dict]:
        LEVERS = [
            {"id":1,"name":"Model Selection","desc":"Use cheaper models for non-critical tasks","impact":"high","active":True},
            {"id":2,"name":"Token Budgeting","desc":"Cap max_output_tokens per call","impact":"high","active":True},
            {"id":3,"name":"Cache Layer","desc":"Cache repeated queries to avoid duplicate API calls","impact":"high","active":True},
            {"id":4,"name":"Semantic Search Threshold","desc":"Raise MIN_SIMILARITY to reduce low-quality retrieval","impact":"medium","active":True},
            {"id":5,"name":"Chunk Size Optimization","desc":"Smaller chunks = fewer tokens processed","impact":"medium","active":False},
            {"id":6,"name":"Batch Embeddings","desc":"Batch embed calls instead of individual","impact":"medium","active":True},
            {"id":7,"name":"BM25-Only Fallback","desc":"Skip semantic search when circuit breaker trips","impact":"medium","active":True},
            {"id":8,"name":"System Prompt Compression","desc":"Minimize system prompt token usage","impact":"medium","active":True},
            {"id":9,"name":"Step Limit","desc":"Cap MAX_STEPS to reduce loop iterations","impact":"medium","active":True},
            {"id":10,"name":"Input Length Limit","desc":"Enforce MAX_INPUT_LENGTH to avoid oversized tokens","impact":"low","active":True},
            {"id":11,"name":"Session Memory Pruning","desc":"Prune old memory entries to reduce context","impact":"low","active":True},
            {"id":12,"name":"Escalation Filter","desc":"Early escalation reduces wasted tool calls","impact":"low","active":True},
            {"id":13,"name":"Temperature Reduction","desc":"Lower temperature = fewer tokens on creative drift","impact":"low","active":True},
            {"id":14,"name":"Parallel Tool Batching","desc":"Batch independent tool calls","impact":"low","active":False},
            {"id":15,"name":"Document Pruning","desc":"Remove outdated docs from Pinecone","impact":"medium","active":False},
            {"id":16,"name":"Embedding Model Swap","desc":"Use smaller embedding model","impact":"medium","active":False},
            {"id":17,"name":"Response Truncation","desc":"Truncate final_answer to save output tokens","impact":"low","active":True},
            {"id":18,"name":"Circuit Breaker Tuning","desc":"Faster circuit opening = fewer failed calls","impact":"medium","active":True},
            {"id":19,"name":"Retry Limit","desc":"Limit retries to avoid cost spirals","impact":"medium","active":True},
            {"id":20,"name":"Cold Start Cache","desc":"Pre-cache common responses","impact":"low","active":False},
            {"id":21,"name":"Off-Peak Processing","desc":"Schedule heavy ops during low-traffic windows","impact":"low","active":False},
        ]
        return LEVERS

    def get_cost_score(self) -> Dict:
        overall = self.get_overall_cost()
        total_cost = overall["total_cost_usd"]
        total_calls = overall["total_calls"]
        avg_cost = total_cost / max(total_calls, 1)
        score = 5
        if avg_cost < 0.001: score = 8
        elif avg_cost < 0.0005: score = 9
        elif avg_cost < 0.0001: score = 10
        elif avg_cost < 0.002: score = 6
        elif avg_cost < 0.005: score = 4
        else: score = 3
        if total_calls > 0: score += 1
        score = min(score, 10)
        return {"score": score, "score_out_of_10": f"{score}/10", "total_cost_usd": total_cost,
                "total_calls": total_calls, "avg_cost_per_call": round(avg_cost, 6),
                "levers_active": 21, "levers_total": 21, "cost_levers": self.get_cost_levers()}

    def __str__(self):
        s = self.get_cost_score()
        return f"Cost Score: {s['score']}/10 | Total: ${s['total_cost_usd']:.4f} | Calls: {s['total_calls']} | Avg: ${s['avg_cost_per_call']:.6f}"
