# ✦ SETUP — Clean Clone to Deploy

## Prerequisites
- Python 3.12+
- Git
- A Gemini API key and Pinecone API key
- Streamlit Cloud account (optional)

## Step 1: Clone
```bash
git clone <repo-url>
cd skincare-agent
```

## Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys:
# - GEMINI_API_KEY
# - GEMINI_FALLBACK_API_KEY
# - PINECONE_API_KEY
# - PINECONE_INDEX
# - GEMINI_MODEL
# - GEMINI_FALLBACK_MODEL
```

## Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 4: Generate Eval Cases
```bash
python generate_evals.py
# Creates 213 eval cases in eval_cases.jsonl
```

## Step 5: Run Eval Suite
```bash
python eval_runner.py
# Outputs eval_results.json + eval_dashboard.json
# Shows visual score breakdown in terminal
```

## Step 6: Launch App
```bash
streamlit run app.py
# Opens at http://localhost:8501
# Full glassmorphism UI with streaming chat
# Cost tracker, eval dashboard, and tool chain visualization
```

## Step 7: Docker Build (Optional)
```bash
docker build -t glow-ai .
docker run -p 8501:8501 --env-file .env glow-ai
```

## Step 8: Deploy to Streamlit Cloud
1. Push repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo
4. Set environment variables in Streamlit Cloud dashboard:
   - GEMINI_API_KEY
   - GEMINI_FALLBACK_API_KEY
   - PINECONE_API_KEY
   - PINECONE_INDEX
5. Deploy. Your public URL is live.

## Verification Checklist
- [ ] `streamlit run app.py` starts without errors
- [ ] Agent responds to skincare questions with streaming
- [ ] Injection attempts are blocked by 30 patterns
- [ ] Cost score displays in sidebar (5/10)
- [ ] 21 cost levers visible in settings
- [ ] Eval suite runs: `python eval_runner.py`
- [ ] 213 eval cases execute
- [ ] Visual dashboard generated (eval_dashboard.json)
- [ ] Circuit breaker state persists across restarts
- [ ] Tool chain visualization appears in chat
- [ ] `.env` is in `.gitignore` (secrets not committed)
- [ ] `git clone` → `pip install` → `streamlit run app.py` works end-to-end
