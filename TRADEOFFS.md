# ✦ Trade-Offs — Glow AI Skincare Agent

## Architecture Decisions

### 1. Streamlit over FastAPI 🎨
- **Chose**: Streamlit for rapid deployment, native chat UI
- **Trade-off**: Less streaming control vs. FastAPI's SSE
- **Impact**: Faster time-to-market, free public URL on Streamlit Cloud
- **Mitigation**: Streamlit's `st.chat_message` + HTML/CSS provides polished streaming

### 2. Gemini 3.6 Flash Primary + 2.0 Flash Fallback ⚡
- **Chose**: Two Gemini models for cost-aware routing
- **Trade-off**: Fallback slightly less capable but 20% cheaper
- **Impact**: Cost score 5/10 baseline, reachable 7-8/10
- **Mitigation**: Circuit breaker auto-routes to fallback on failure

### 3. Pinecone + BM25 Hybrid Search 🔍
- **Chose**: Reciprocal Rank Fusion of semantic + keyword search
- **Trade-off**: Dual-query pipeline adds latency
- **Impact**: More accurate results, slower per query
- **Mitigation**: Circuit breaker falls back to BM25-only when Pinecone fails

### 4. Cached Responses with TTL 💾
- **Chose**: Cache repeated queries for 1 hour
- **Trade-off**: Stale responses vs. significant cost savings
- **Impact**: Reduces redundant API calls
- **Mitigation**: TTL balances freshness and cost

### 5. Circuit Breaker State Persistence 🔄
- **Chose**: Persist circuit breaker state to `circuit_state.json`
- **Trade-off**: File I/O overhead vs. state survives restarts
- **Impact**: Agent doesn't spam failed services after restart
- **Mitigation**: Lightweight JSON, single file per instance

### 6. 21 Cost Levers 📊
- **Chose**: Catalog all 21 cost optimization levers
- **Trade-off**: Many levers to manage vs. clear optimization path
- **Impact**: Users see exactly what affects cost
- **Mitigation**: Levers categorized by impact (high/medium/low)

### 7. Eval Suite of 213 Cases 🧪
- **Chose**: 213 cases across 4 categories
- **Trade-off**: Longer eval run vs. comprehensive coverage
- **Impact**: Accurate scoring across all dimensions
- **Mitigation**: Automated, runs in seconds

### 8. Guardrails Pattern Expansion 🛡️
- **Chose**: 30 injection patterns, rate limiting, input sanitization
- **Trade-off**: More blocking rules vs. potential false positives
- **Impact**: Strong security, some legitimate queries may be blocked
- **Mitigation**: Patterns tested against real user queries

### 9. Glassmorphism UI Design 🎨
- **Chose**: Premium CSS with gradients, glass cards, animations
- **Trade-off**: More CSS complexity vs. standard Streamlit styling
- **Impact**: Visually impressive for capstone demo
- **Mitigation**: All CSS embedded in app.py, no external dependencies

### 10. Tool Chain Visualization 🔧
- **Chose**: Display each tool call in chat UI
- **Trade-off**: Extra rendering vs. opaque agent behavior
- **Impact**: Transparent, impressive demo of agent reasoning
- **Mitigation**: Simple HTML rendering in Streamlit

## Known Limitations
- Streaming is via markdown updates, not true SSE
- Cache is local per session (not distributed)
- Circuit breaker state is per-process
- Cost tracking estimates based on token counts, not exact billing
- 30 injection patterns may occasionally false-positive on edge cases

## Visual Design
- Dark theme with indigo/purple gradient accents
- Glassmorphism cards with backdrop blur
- Score bars with gradient fills
- Tool call display with colored left borders
- Polished chat bubbles with role labels
- Typing indicators with pulse animation
