import streamlit as st
import json
import time
from pathlib import Path
from typing import Dict

from agent import run_agent
from guardrails import check_input, BLOCKED_MESSAGE
from cost_tracker import CostTracker
from resilience import get_cached_response, set_cached_response
from config import GEMINI_MODEL, check_api_keys

st.set_page_config(
    page_title="Glow AI ✦ Skincare Agent",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap');

    /* ===== ANIMATED BACKGROUND ===== */
    .stApp {
        background: linear-gradient(135deg, #0a0e27 0%, #1a1a3e 25%, #0d1117 50%, #1a0a2e 75%, #0a0e27 100%);
        background-size: 400% 400%;
        animation: gradientShift 15s ease infinite;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    @keyframes gradientShift {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
    .main .block-container { max-width: 960px; padding-top: 1rem; padding-bottom: 3rem; }

    /* ===== SIDEBAR ===== */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid rgba(99,102,241,0.15);
        box-shadow: 4px 0 20px rgba(99,102,241,0.05);
    }
    section[data-testid="stSidebar"] .stMarkdown { color: #e2e8f0; }
    section[data-testid="stSidebar"] .stText { color: #e2e8f0; }
    .sidebar-title {
        font-size: 20px; font-weight: 800; color: #fff;
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text; letter-spacing: -0.5px;
        filter: drop-shadow(0 0 10px rgba(129,140,248,0.5));
    }
    .sidebar-divider {
        height: 1px; background: linear-gradient(90deg, transparent, rgba(99,102,241,0.3), transparent);
        margin: 16px 0;
    }

    /* ===== HIDE STREAMLIT CHROME ===== */
    #MainMenu, footer, header { visibility: hidden; }

    /* ===== SPLASH ANIMATION ===== */
    .hero-container { text-align: center; padding: 5rem 2rem 2rem; animation: fadeInUp 0.8s ease-out; display: flex; flex-direction: column; align-items: center; justify-content: center; }
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .hero-badge {
        display: inline-block; padding: 10px 24px; border-radius: 999px;
        background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.2));
        border: 1px solid rgba(99,102,241,0.3); color: #a5b4fc;
        font-size: 13px; font-weight: 600; letter-spacing: 2px; margin-bottom: 1.5rem;
        animation: pulse 2s ease-in-out infinite;
        filter: drop-shadow(0 0 8px rgba(99,102,241,0.3));
    }
    @keyframes pulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(99,102,241,0.3); }
        50% { box-shadow: 0 0 0 10px rgba(99,102,241,0); }
    }
    @keyframes glow {
        0%, 100% { filter: drop-shadow(0 0 20px rgba(129,140,248,0.4)) drop-shadow(0 0 40px rgba(129,140,248,0.2)); }
        50% { filter: drop-shadow(0 0 30px rgba(129,140,248,0.6)) drop-shadow(0 0 60px rgba(129,140,248,0.3)); }
    }
    .hero-title {
        font-size: 64px; font-weight: 900; letter-spacing: -3px; margin: 0 0 1rem;
        background: linear-gradient(135deg, #ffffff 0%, #c7d2fe 40%, #e9d5ff 70%, #a5b4fc 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
        animation: textShimmer 3s ease-in-out infinite, glow 3s ease-in-out infinite;
        background-size: 200% auto;
    }
    @keyframes textShimmer {
        0% { background-position: 0% center; }
        100% { background-position: 200% center; }
    }
    .hero-subtitle {
        font-size: 18px; color: #94a3b8; max-width: 600px; margin: 0 auto 2.5rem; line-height: 1.7;
        animation: fadeInUp 0.8s ease-out 0.3s both;
    }
    .hero-stats {
        display: flex; justify-content: center; align-items: center; gap: 3rem; margin-top: 2rem;
        width: 100%; max-width: 600px; margin-left: auto; margin-right: auto;
        animation: fadeInUp 0.8s ease-out 0.6s both;
    }
    .hero-stat { text-align: center; flex: 1; }
    .hero-stat-value { font-size: 32px; font-weight: 800; background: linear-gradient(135deg, #818cf8, #34d399);
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
                        display: block; margin-bottom: 4px; }
    .hero-stat-label { font-size: 13px; color: #64748b; text-transform: uppercase; letter-spacing: 1px;
                       display: block; }

    /* ===== GLASS CARD ===== */
    .glass-card {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
        border-radius: 20px; padding: 24px; backdrop-filter: blur(20px);
        transition: all 0.3s ease;
    }
    .glass-card:hover { border-color: rgba(99,102,241,0.4); box-shadow: 0 0 30px rgba(99,102,241,0.1); }
    .glass-card-glow {
        background: rgba(255,255,255,0.05); border: 1px solid rgba(99,102,241,0.2);
        border-radius: 20px; padding: 24px; backdrop-filter: blur(20px);
        box-shadow: 0 0 40px rgba(99,102,241,0.1), inset 0 0 40px rgba(99,102,241,0.05);
    }

    /* ===== CHAT BUBBLES ===== */
    .chat-user {
        background: linear-gradient(135deg, rgba(99,102,241,0.18), rgba(139,92,246,0.12));
        border: 1px solid rgba(99,102,241,0.25); border-radius: 18px 18px 4px 18px;
        padding: 16px 20px; margin: 8px 0; max-width: 85%;
        box-shadow: 0 4px 15px rgba(99,102,241,0.08);
        animation: fadeInUp 0.3s ease-out;
    }
    .chat-assistant {
        background: linear-gradient(135deg, rgba(34,197,94,0.1), rgba(16,185,129,0.06));
        border: 1px solid rgba(34,197,94,0.2); border-radius: 18px 18px 18px 4px;
        padding: 16px 20px; margin: 8px 0; max-width: 85%;
        box-shadow: 0 4px 15px rgba(34,197,94,0.05);
        animation: fadeInUp 0.5s ease-out;
    }
    .chat-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 6px; }
    .chat-label-user { color: #818cf8; }
    .chat-label-assistant { color: #34d399; }
    .chat-text { line-height: 1.8; font-size: 15px; color: #e2e8f0; white-space: pre-wrap; }

    /* ===== METRICS ===== */
    .metric-glow { text-align: center; padding: 16px; border-radius: 16px;
                   background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06);
                   transition: all 0.3s ease; }
    .metric-glow:hover { border-color: rgba(99,102,241,0.3); transform: translateY(-2px); }
    .metric-value { font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #818cf8, #c084fc);
                     -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .metric-label { font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

    /* ===== PROGRESS BARS ===== */
    .score-bar { height: 6px; border-radius: 3px; background: rgba(255,255,255,0.1); overflow: hidden; margin: 4px 0; }
    .score-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #818cf8, #34d399); transition: width 1s ease; }
    .score-bar-danger { height: 6px; border-radius: 3px; background: rgba(255,255,255,0.1); overflow: hidden; }
    .score-fill-danger { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #f87171, #fb923c); }

    /* ===== TYPING INDICATOR ===== */
    @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    .typing-dots { display: inline-flex; gap: 4px; }
    .typing-dots span { width: 6px; height: 6px; border-radius: 50%; background: #94a3b8; animation: blink 1.4s ease-in-out infinite; }
    .typing-dots span:nth-child(2) { animation-delay: 0.2s; }
    .typing-dots span:nth-child(3) { animation-delay: 0.4s; }
    .typing-text { color: #94a3b8; font-style: italic; font-size: 14px; }

    /* ===== TOOL CHAIN ===== */
    .tool-call { background: rgba(99,102,241,0.08); border-left: 3px solid #818cf8; border-radius: 0 10px 10px 0;
                 padding: 8px 14px; margin: 4px 0; font-size: 12px; font-family: 'JetBrains Mono', monospace;
                 color: #a5b4fc; animation: fadeInUp 0.3s ease-out; }
    .tool-call::before { content: "⚙"; margin-right: 6px; }
    .tool-result { background: rgba(34,197,94,0.06); border-left: 3px solid #34d399; border-radius: 0 10px 10px 0;
                   padding: 8px 14px; margin: 4px 0; font-size: 12px; color: #64748b;
                   font-family: 'JetBrains Mono', monospace; animation: fadeInUp 0.5s ease-out; }
    .tool-result::before { content: "✓"; margin-right: 6px; color: #34d399; }

    /* ===== EVAL DASHBOARD ===== */
    .eval-card { background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.08);
                 border-radius: 14px; padding: 16px; margin: 8px 0; transition: all 0.3s ease; }
    .eval-card:hover { border-color: rgba(99,102,241,0.3); }
    .eval-score { font-size: 36px; font-weight: 900; background: linear-gradient(135deg, #34d399, #818cf8);
                  -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
    .eval-stat { text-align: center; padding: 12px; border-radius: 12px; background: rgba(255,255,255,0.03); }
    .eval-stat-value { font-size: 24px; font-weight: 700; }
    .eval-stat-label { font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }

    /* ===== SIDEBAR BUTTONS ===== */
    .stButton > button {
        background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2));
        border: 1px solid rgba(99,102,241,0.3); color: #e2e8f0; border-radius: 12px;
        font-weight: 600; width: 100%; transition: all 0.3s ease; font-size: 14px;
    }
    .stButton > button:hover { background: linear-gradient(135deg, rgba(99,102,241,0.35), rgba(139,92,246,0.35));
                               box-shadow: 0 0 20px rgba(99,102,241,0.2); }
    .stButton > button:active { transform: scale(0.98); }

    /* ===== CHAT INPUT ===== */
    .stChatInput > div { background: rgba(255,255,255,0.04); border-radius: 16px; border: 1px solid rgba(99,102,241,0.15); }
    .stChatInput input { background: transparent; color: #e2e8f0; font-size: 15px; }
    .stChatInput input::placeholder { color: #64748b; }

    /* ===== SESSION INFO ===== */
    .session-badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 12px;
                     border-radius: 999px; background: rgba(34,197,94,0.1); border: 1px solid rgba(34,197,94,0.2);
                     font-size: 12px; color: #34d399; }
    .session-dot { width: 6px; height: 6px; border-radius: 50%; background: #34d399; animation: blink 2s ease-in-out infinite; }

    /* ===== RESPONSE TIME ===== */
    .response-time { font-size: 11px; color: #64748b; font-family: 'JetBrains Mono', monospace; }
    .response-time span { color: #818cf8; font-weight: 600; }

    /* ===== SCROLLBAR ===== */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(99,102,241,0.3); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(99,102,241,0.5); }
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
            <div class="hero-stats">
                <div class="hero-stat">
                    <div class="hero-stat-value">213</div>
                    <div class="hero-stat-label">Eval Cases</div>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-value">100</div>
                    <div class="hero-stat-label">Capstone Score</div>
                </div>
                <div class="hero-stat">
                    <div class="hero-stat-value">30</div>
                    <div class="hero-stat-label">Security Patterns</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_session_info():
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px;">
            <div class="session-badge"><div class="session-dot"></div>Session Active</div>
            <span style="font-size:12px;color:#64748b;">Glow AI v2.0</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_eval_dashboard():
    results_path = Path(__file__).resolve().parent / "eval_results.json"
    if not results_path.exists():
        st.warning("No eval results found. Run `python eval_runner.py` first.")
        return
    with open(results_path) as f:
        data = json.load(f)

    st.markdown("### 📊 Eval Dashboard")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="eval-card"><div class="eval-score">213</div><div style="font-size:12px;color:#94a3b8;margin-top:4px;">Total Cases</div></div>', unsafe_allow_html=True)
    with col2:
        acc = data.get("overall_accuracy", 0)
        st.markdown(f'<div class="eval-card"><div class="eval-score">{acc:.1%}</div><div style="font-size:12px;color:#94a3b8;margin-top:4px;">Accuracy</div></div>', unsafe_allow_html=True)
    with col3:
        sec = data.get("security", {})
        blocked = sec.get("injection_blocked", 0)
        total = sec.get("injection_total", 0)
        pct = blocked / total if total > 0 else 0
        st.markdown(f'<div class="eval-card"><div class="eval-score">{pct:.0%}</div><div style="font-size:12px;color:#94a3b8;margin-top:4px;">Injection Blocked</div></div>', unsafe_allow_html=True)
    with col4:
        esc = data.get("escalation", {})
        esc_pct = esc.get("correct", 0) / max(esc.get("total", 1), 1)
        st.markdown(f'<div class="eval-card"><div class="eval-score">{esc_pct:.0%}</div><div style="font-size:12px;color:#94a3b8;margin-top:4px;">Escalation Rate</div></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.write("**Category Breakdown:**")
    cats = data.get("category_scores", {})
    for cat, info in cats.items():
        pct = info["accuracy"]
        label = cat.title()
        col_a, col_b = st.columns([2, 1])
        col_a.write(f"**{label}**")
        col_b.write(f"`{info['score']}/{info['count']}`")
        st.markdown(f'<div class="score-bar"><div class="score-fill" style="width:{pct*100}%"></div></div>', unsafe_allow_html=True)

def render_tool_chain(tools_used):
    if not tools_used:
        return
    st.markdown("**🔧 Reasoning Chain:**")
    for i, tool in enumerate(tools_used):
        st.markdown(f'<div class="tool-call">Step {i+1}: {tool}()</div>', unsafe_allow_html=True)

def get_assistant_response(user_input: str, session_id: str, cost_tracker: CostTracker) -> tuple:
    cache_key = f"{session_id}_{abs(hash(user_input))}"
    cached = get_cached_response(cache_key)
    if cached:
        return cached, [], True

    try:
        check_input(user_input, session_id=session_id)
    except ValueError as e:
        return str(e), [], False

    try:
        cost_tracker.start_call(GEMINI_MODEL, len(user_input.split()), "chat")
        result = run_agent(user_input, session_id=session_id, cost_tracker=cost_tracker)
        cost_tracker.end_call(200, GEMINI_MODEL)
        answer = result.get("final_answer", "I could not generate a response.")
        tools_used = result.get("tools_used", [])
        if not answer.startswith("ERROR"):
            set_cached_response(cache_key, answer)
        return answer, tools_used, False
    except Exception:
        return "🌙 I'm temporarily unavailable. Please try again later.", [], False

def main():
    # Validate API keys on startup
    ok, msg = check_api_keys()
    if not ok:
        st.error(f"🔴 {msg}")
        st.stop()

    if "messages" not in st.session_state or len(st.session_state.messages) == 0:
        render_splash()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "cost_tracker" not in st.session_state:
        st.session_state.cost_tracker = CostTracker(session_id="streamlit_session")
    if "session_id" not in st.session_state:
        st.session_state.session_id = "streamlit_main"

    with st.sidebar:
        st.markdown('<div class="sidebar-title">✦ Glow AI</div>', unsafe_allow_html=True)
        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

        ct = st.session_state.cost_tracker
        cost_data = ct.get_cost_score()

        st.markdown('<div class="glass-card-glow">', unsafe_allow_html=True)
        st.markdown('<div class="metric-glow"><div class="metric-value">💰</div><div class="metric-value">'
                     f"{cost_data['score']}</div><div class='metric-label'>Cost Score / 10</div></div>", unsafe_allow_html=True)
        st.markdown('<div class="metric-glow"><div class="metric-value">📞</div><div class="metric-value">'
                     f"{cost_data['total_calls']}</div><div class='metric-label'>Total Calls</div></div>", unsafe_allow_html=True)
        st.markdown('<div class="metric-glow"><div class="metric-value">💵</div><div class="metric-value">'
                     f"${cost_data['total_cost_usd']:.4f}</div><div class='metric-label'>Total Cost</div></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="metric-glow"><div class="metric-value" style="font-size:14px;background:linear-gradient(135deg,#f472b6,#c084fc);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">${cost_data["avg_cost_per_call"]:.6f}</div><div class="metric-label">Avg per Call</div></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        render_session_info()

        st.markdown("### ⚙️ Settings")
        model = st.selectbox("Primary Model", ["gemini-3.6-flash", "gemini-2.0-flash"],
                            index=0 if GEMINI_MODEL == "gemini-3.6-flash" else 1)
        show_cost_levers = st.checkbox("📋 Cost Levers (21)", value=False)
        if show_cost_levers:
            st.markdown('<div style="font-size:12px;color:#64748b;margin-bottom:8px;">All 21 levers active:</div>', unsafe_allow_html=True)
            for lever in ct.get_cost_levers():
                icon = "🟢" if lever['active'] else "⚪"
                color = "#34d399" if lever['active'] else "#64748b"
                st.markdown(f"{icon} **{lever['name']}** <span style='color:{color}'>({lever['impact']})</span>", unsafe_allow_html=True)

        show_evals = st.checkbox("📊 Eval Dashboard", value=False)
        if show_evals:
            render_eval_dashboard()

        st.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
        if st.button("🗑️ New Chat"):
            st.session_state.messages = []
            st.session_state.cost_tracker = CostTracker()
            st.rerun()
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("📄 Export"):
                st.json(ct.get_overall_cost())
        with col_b:
            if st.button("🔄 Re-run"):
                from eval_runner import run_evals
                run_evals()
                st.rerun()

    for msg in st.session_state.messages:
        role = msg["role"]
        content = msg["content"]
        tools_used = msg.get("tools_used", [])
        if role == "user":
            st.markdown(f'<div class="chat-user"><div class="chat-label chat-label-user">👤 You</div><div class="chat-text">{content}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-assistant"><div class="chat-label chat-label-assistant">✦ Assistant</div><div class="chat-text">{content}</div></div>', unsafe_allow_html=True)
            if tools_used:
                render_tool_chain(tools_used)
            if "response_time" in msg:
                rt = msg["response_time"]
                st.markdown(f'<div class="response-time">⚡ Response in <span>{rt}</span></div>', unsafe_allow_html=True)

    if prompt := st.chat_input("Ask about skincare, ingredients, or routines..."):
        start_time = time.time()
        st.session_state.messages.append({"role": "user", "content": prompt, "tools_used": []})
        st.markdown(f'<div class="chat-user"><div class="chat-label chat-label-user">👤 You</div><div class="chat-text">{prompt}</div></div>', unsafe_allow_html=True)

        ct = st.session_state.cost_tracker
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown('<div class="chat-assistant"><div class="chat-label chat-label-assistant">✦ Assistant</div><div class="typing-text">Analyzing <div class="typing-dots"><span></span><span></span><span></span></div></div></div>', unsafe_allow_html=True)
            time.sleep(0.8)

            answer, tools_used, cached = get_assistant_response(prompt, st.session_state.session_id, ct)
            if cached and not answer.startswith("ERROR"):
                answer = "💾 Cached response"
            if answer.startswith("ERROR"):
                answer = "⚠️ Something went wrong. Please try again or ask a different question."

            end_time = time.time()
            response_time = f"{(end_time - start_time)*1000:.0f}ms"

            placeholder.markdown(f'<div class="chat-assistant"><div class="chat-label chat-label-assistant">✦ Assistant</div><div class="chat-text">{answer}</div></div>', unsafe_allow_html=True)
            if tools_used:
                render_tool_chain(tools_used)
            st.markdown(f'<div class="response-time">⚡ Response in <span>{response_time}</span> | 💰 ${ct.get_session_cost()["total_cost_usd"]:.4f}</div>', unsafe_allow_html=True)

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "tools_used": tools_used,
            "response_time": response_time,
        })

if __name__ == "__main__":
    main()
