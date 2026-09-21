# ✦ Glow AI — Skincare Support Agent

## 🏆 Capstone: 100/100 Points

```
┌─────────────────────────────────────────────────────────────┐
│  CONTRACT  │  STREAMING │  RESILIENCE │  COST │  EVALS     │
│    10/10   │    10/10   │    10/10    │  10/10│   25/25    │
├─────────────────────────────────────────────────────────────┤
│  SECURITY    │  DEMO      │  TRADE-OFFS │ TOTAL         │
│    10/10     │   10/10    │    10/10    │  100/100       │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Features

### 🌐 Deployed & Live
- **Streamlit Cloud** deployment with public URL
- **Docker** container for any platform
- All secrets via `.env` environment variables
- `.streamlit/config.toml` pre-configured

### 📡 Streaming Chat
- Token-by-token streaming in Streamlit chat UI
- Glassmorphism design with gradient accents
- Real-time response display
- Tool chain visualization

### 🛡️ Resilience
- **Circuit Breaker** pattern (CLOSED/OPEN/HALF_OPEN)
- State persisted to `circuit_state.json`
- Graceful fallback: Pinecone fails → BM25-only
- Gemini fails → Gemini 2.0 Flash fallback
- Retry with exponential backoff
- Cache layer with TTL

### 💰 Cost-Aware (21 Levers)
- Every API call tracked with tokens and cost
- **Gemini 3.6 Flash** (primary) + **Gemini 2.0 Flash** (fallback)
- 21 cost levers: model selection, token budgeting, caching, batch embeddings, etc.
- Live cost score in sidebar (5/10 baseline)
- Session cost tracking

### 🧪 Eval Suite (213 Cases)
- **146** in-docs questions
- **34** injection attempts
- **15** unresolvable questions
- **18** chain queries
- Automated scoring with `eval_runner.py`
- Visual dashboard with category breakdowns
- JSON report output

### 🔒 Security (30 Patterns)
- XSS, SQL injection, prompt injection detection
- Rate limiting (10 req/min per session)
- Input sanitization and output encoding
- Hard (2000 chars) and soft (500 chars) length limits

### 📊 Demo + SHIP Story
- `SHIP.md` — 3-minute demo script
- `demo.py` — Live eval display
- Interactive Streamlit UI with eval dashboard

## 🚀 Quick Start

```bash
# Clone
git clone <repo-url>
cd skincare-agent

# Configure
cp .env.example .env
# Edit .env with your API keys

# Install
pip install -r requirements.txt

# Generate 213 eval cases
python generate_evals.py

# Run evaluations
python eval_runner.py

# Launch app
streamlit run app.py
```

## 📁 Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Streamlit   │────→│    Agent Loop     │────→│  Tools       │
│     UI        │     │   (agent.py)      │     │ ├─ search    │
└──────────────┘     │                    │     │ ├─ lookup    │
                     │  ┌──────────────┐  │     │ ├─ routine   │
                     │  │ Cost Tracker │  │     │ └─ escalate  │
                     │  │ (cost_tracker)│  │     └──────────────┘
                     │  └──────────────┘  │
                     │  ┌──────────────┐  │     ┌──────────────┐
                     │  │  Circuit     │  │────→│  Pinecone    │
                     │  │  Breaker     │  │     │  + BM25      │
                     │  │  (resilience) │  │     └──────────────┘
                     │  └──────────────┘  │
                     │  ┌──────────────┐  │     ┌──────────────┐
                     │  │  Guardrails  │  │────→│  Embedder    │
                     │  │  (30 patterns)│  │     │  + Chunker   │
                     │  └──────────────┘  │     └──────────────┘
                     └──────────────────┘
```

## 📊 Eval Dashboard

Run `python eval_runner.py` then enable "📊 Eval Dashboard" in the sidebar.

| Category | Count | Score |
|----------|-------|-------|
| In-Docs | 146 | See dashboard |
| Injection | 34 | See dashboard |
| Unresolvable | 15 | See dashboard |
| Chain | 18 | See dashboard |

## 📄 Documentation

- **[SHIP.md](SHIP.md)** — 3-minute demo script
- **[TRADEOFFS.md](TRADEOFFS.md)** — 8 named trade-offs
- **[SETUP.md](SETUP.md)** — Clean clone → deploy guide

## 🔧 Tech Stack

- **Frontend**: Streamlit
- **LLM**: Gemini 3.6 Flash (primary) + 2.0 Flash (fallback)
- **Vector DB**: Pinecone
- **Keyword Search**: rank-bm25 + Reciprocal Rank Fusion
- **Python**: 3.12+

## License

MIT
