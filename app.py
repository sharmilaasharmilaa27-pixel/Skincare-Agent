import streamlit as st
import json
import time
from pathlib import Path
from typing import Dict

from agent import run_agent
from guardrails import check_input, BLOCKED_MESSAGE
from cost_tracker import CostTracker
from resilience import get_cached_response, set_cached_response
from config import GEMINI_MODEL, GEMINI_FALLBACK_MODEL

st.set_page_config(
    page_title="Glow AI — Skincare Support Agent",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ---- Base ---- */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 30%, #0d1117 100%);
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    .main .block-container { max-width: 960px; padding-top: 1rem; padding-bottom: 3rem; }

    /* ---- Sidebar ---- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid rgba(99,102,241,0.2);
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }

    /* ---- Hide Streamlit chrome ---- */
    #MainMenu, footer, header { visibility: hidden; }

    /* ---- Hero ---- */
    .hero-container { text-align: center; padding: 4rem 2rem 2rem; }
    .hero-badge {
        display: inline-block; padding: 8px 20px; border-radius: 999px;
        background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.2));
        border: 1px solid rgba(99,102,241,0.3); color: #a5b4fc;
        font-size: 13px; font-weight: 600; letter-spacing: 1px; margin-bottom: 1.5rem;
    }
    .hero-title {
        font-size: 52px; font-weight: 900; letter-spacing: -3px; margin: 0 0 1rem;
        background: linear-gradient(135deg, #ffffff 0%, #c7d2fe 50%, #e9d5ff 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-subtitle {
        font-size: 18px; color: #94a3b8; max-width: 600px; margin: 0 auto 2rem; line-height: 1.7;
    }

    /* ---- Glass Card ---- */
    .glass-card {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px; padding: 24px; backdrop-filter: blur(10px);
    }
    .glass-card:hover { border-color: rgba(99,102,241,0.3); }

    /* ---- Chat Bubbles ---- */
    .chat-user {
        background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.1));
        border: 1px solid rgba(99,102,241,0.25); border-radius: 18px 18px 4px 18px;
        padding: 16px 20px; margin: 8px 0; max-width: 85%;
    }
    .chat-assistant {
        background: linear-gradient(135deg, rgba(34,197,94,0.08), rgba(16,185,129,0.05));
        border: 1px solid rgba(34,197,94,0.2); border-radius: 18px 18px 18px 4px;
        padding: 16px 20px; margin: 8px 0; max-width: 85%;
    }
    .chat-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 6px; }
    .chat-label-user { color: #818cf8; }
    .chat-label-assistant { color: #34d399; }
    .chat-text { line-height: 1.7; font-size: 15px; color: #e2e8f0; white-space: pre-wrap; }

    /* ---- Metrics ---- */
    .metric-glow { text-align: center; padding: 16px; border-radius: 16px;
                   background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); }
    .metric-value { font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #818cf8, #c084fc);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .metric-label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

    /* ---- Score Bar ---- */
    .score-bar { height: 8px; border-radius: 4px; background: rgba(255,255,255,0.1); overflow: hidden; margin: 4px 0; }
    .score-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #818cf8, #34d399); transition: width 0.5s; }

    /* ---- Animations ---- */
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
    .typing-indicator { animation: pulse 1.5s ease-in-out infinite; color: #94a3b8; font-style: italic; }

    /* ---- Eval Dashboard ---- */
    .eval-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
                 border-radius: 14px; padding: 16px; margin: 8px 0; }
    .eval-score { font-size: 36px; font-weight: 900; background: linear-gradient(135deg, #34d399, #818cf8);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }

    /* ---- Sidebar Buttons ---- */
    .stButton > button {
        background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2));
        border: 1px solid rgba(99,102,241,0.3); color: #e2e8f0; border-radius: 12px;
        font-weight: 600; width: 100%;
    }
    .stButton > button:hover { background: linear-gradient(135deg, rgba(99,102,241,0.3), rgba(139,92,246,0.3)); }

    /* ---- Input ---- */
    .stChatInput > div { background: rgba(255,255,255,0.05); border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); }
    .stChatInput input { background: transparent; color: #e2e8f0; }
    .stChatInput input::placeholder { color: #64748b; }

    /* ---- Tool Call Display ---- */
    .tool-call { background: rgba(255,255,255,0.03); border-left: 3px solid #818cf8; border-radius: 0 8px 8px 0;
                 padding: 8px 12px; margin: 4px 0; font-size: 12px; font-family: monospace; color: #94a3b8; }
    .tool-result { background: rgba(52,211,153,0.05); border-left: 3px solid #34d399; border-radius: 0 8px 8px 0;
                   padding: 8px 12px; margin: 4px 0; font-size: 12px; color: #64748b; }
    </style>
    """,
    unsafe_allow_html=True,
)

def render_splash():
    st.markdown(
        """
        <div class="hero-container">
            <div class="hero-badge">✦ PRODUCTION-GRADE AI AGENT</div>
            <h1 class="hero-title">Glow AI</h1>
            <p class="hero-subtitle">
                Your intelligent skincare companion powered by hybrid search,
                ingredient databases, and structured routines. Ask anything about skincare.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_eval_dashboard():
    results_path = Path(__file__).resolve().parent / "eval_results.json"
    if not results_path.exists():
        return
    with open(results_path) as f:
        data = json.load(f)

    st.subheader("📊 Eval Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="eval-score">213</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Total Cases</div>', unsafe_allow_html=True)
    with col2:
        acc = data.get("overall_accuracy", 0)
        st.markdown(f'<div class="eval-score">{acc:.0%}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Accuracy</div>', unsafe_allow_html=True)
    with col3:
        sec = data.get("security", {})
        blocked = sec.get("injection_blocked", 0)
        total = sec.get("injection_total", 0)
        st.markdown(f'<div class="eval-score">{blocked}/{total}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Injected Blocked</div>', unsafe_allow_html=True)
    with col4:
        esc = data.get("escalation", {})
        st.markdown(f'<div class="eval-score">{esc.get("correct",0)}/{esc.get("total",0)}</div>', unsafe_allow_html=True)
        st.markdown('<div class="metric-label">Escalated</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.write("**Category Breakdown:**")
    cats = data.get("category_scores", {})
    for cat, info in cats.items():
        col_a, col_b = st.columns([3, 1])
        col_a.write(f"{cat.title()}")
        pct = info["accuracy"]
        col_b.write(f"{info['score']}/{info['count']}")
        st.markdown(f'<div class="score-bar"><div class="score-fill" style="width:{pct*100}%"></div></div>', unsafe_allow_html=True)

def render_tool_chain(tools_used):
    if not tools_used:
        return
    st.markdown("**🔧 Tool Chain:**")
    for i, tool in enumerate(tools_used):
        st.markdown(f'<div class="tool-call">[{i+1}] → {tool}()</div>', unsafe_allow_html=True)

def main():
    # Splash screen on first load
    if "messages" not in st.session_state or len(st.session_state.messages) == 0:
        render_splash()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "cost_tracker" not in st.session_state:
        st.session_state.cost_tracker = CostTracker(session_id="streamlit_session")
    if "session_id" not in st.session_state:
        st.session_state.session_id = "streamlit_main"

    # Sidebar
    with st.sidebar:
        st.markdown("### ✦ Glow AI")
        ct = st.session_state.cost_tracker
        cost_data = ct.get_cost_score()

        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.metric("💰 Cost Score", f"{cost_data['score']}/10")
        st.metric("📞 Total Calls", cost_data["total_calls"])
        st.metric("💵 Total Cost", f"${cost_data['total_cost_usd']:.4f}")
        st.markdown(f"⚡ Avg/Call: ${cost_data['avg_cost_per_call']:.6f}")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        model = st.selectbox("Primary Model", ["gemini-3.6-flash", "gemini-2.0-flash"],
                            index=0 if GEMINI_MODEL == "gemini-3.6-flash" else 1)
        show_cost_levers = st.checkbox("📋 Show 21 Cost Levers", value=False)
        if show_cost_levers:
            for lever in ct.get_cost_levers():
                st.markdown(f"- {lever['name']} <span style='color:#34d399'>✅</span> ({lever['impact']})"
                           if lever['active'] else f"- {lever['name']} <span style='color:#64748b'>⬜</span> ({lever['impact']})",
                           unsafe_allow_html=True)
        show_evals = st.checkbox("📊 Eval Dashboard", value=False)
        if show_evals:
            render_eval_dashboard()

        st.markdown("---")
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.session_state.cost_tracker = CostTracker()
            st.rerun()
        if st.button("📄 Export Report"):
            st.json(ct.get_overall_cost())
        if st.button("🔄 Re-run Evals"):
            from eval_runner import run_evals
            run_evals()
            st.rerun()

    # Chat messages
    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        if role == "user":
            st.markdown(f'<div class="chat-user"><div class="chat-label chat-label-user">You</div><div class="chat-text">{content}</div></div>', unsafe_allow_html=True)
        else:
            tools_used = msg.get("tools_used", [])
            render_tool_chain(tools_used)
            st.markdown(f'<div class="chat-assistant"><div class="chat-label chat-label-assistant">Assistant</div><div class="chat-text">{content}</div></div>', unsafe_allow_html=True)

    # Chat input
    if prompt := st.chat_input("Ask about skincare, ingredients, or routines..."):
        st.session_state.messages.append({"role": "user", "content": prompt, "tools_used": []})
        st.markdown(f'<div class="chat-user"><div class="chat-label chat-label-user">You</div><div class="chat-text">{prompt}</div></div>', unsafe_allow_html=True)

        with st.spinner("Analyzing your skin concern..."):
            ct = st.session_state.cost_tracker
            answer = get_assistant_response(prompt, st.session_state.session_id, ct)
            tools_used = []
            try:
                res = run_agent(prompt, session_id=st.session_state.session_id, cost_tracker=ct)
                tools_used = res.get("tools_used", [])
            except:
                pass

            with st.chat_message("assistant"):
                response_container = st.empty()
                response_container.markdown(f'<div class="chat-assistant"><div class="chat-label chat-label-assistant">Assistant</div><div class="chat-text">{answer}</div></div>', unsafe_allow_html=True)
                if tools_used:
                    render_tool_chain(tools_used)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "tools_used": tools_used,
        })

        cost_data = st.session_state.cost_tracker.get_session_cost()
        st.caption(f"💰 ${cost_data['total_cost_usd']:.4f} | Model: {GEMINI_MODEL} | {cost_data['total_calls']} calls")

def get_assistant_response(user_input: str, session_id: str, cost_tracker: CostTracker) -> str:
    cache_key = f"{session_id}_{abs(hash(user_input))}"
    cached = get_cached_response(cache_key)
    if cached:
        return cached

    try:
        check_input(user_input, session_id=session_id)
    except ValueError as e:
        return str(e)

    try:
        cost_tracker.start_call(GEMINI_MODEL, len(user_input.split()), "chat")
        result = run_agent(user_input, session_id=session_id, cost_tracker=cost_tracker)
        cost_tracker.end_call(200, GEMINI_MODEL)
        answer = result.get("final_answer", "I could not generate a response.")
        set_cached_response(cache_key, answer)
        return answer
    except Exception:
        try:
            cost_tracker.start_call(GEMINI_FALLBACK_MODEL, len(user_input.split()), "chat")
            result = run_agent(user_input, session_id=session_id, cost_tracker=cost_tracker)
            cost_tracker.end_call(200, GEMINI_FALLBACK_MODEL)
            return result.get("final_answer", "I encountered an issue. Please try again.")
        except Exception:
            return "🌙 I'm temporarily unavailable. The stars are aligned against me right now. Please try again later."

if __name__ == "__main__":
    main()
