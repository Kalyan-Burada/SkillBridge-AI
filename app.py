"""
app.py  —  Career Copilot Streamlit app (fully offline).
Run:
    streamlit run app.py
All analysis logic is in pipeline.py — no duplication.
"""
import os
import traceback
import streamlit as st

st.set_page_config(
    page_title="SkillBridge-AI Orchestrator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Space+Grotesk:wght@300;400;500;600&family=Inter:wght@300;400;500&display=swap');

/* ══════════════════════════════════════════════
   TOKENS (Aurora & Glassmorphism Theme)
══════════════════════════════════════════════ */
:root {
  --bg-dark:       #06080F;
  --bg-panel:      rgba(13, 17, 28, 0.6);
  --bg-panel-hover:rgba(20, 25, 40, 0.8);
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-glow:   rgba(0, 240, 255, 0.3);
  --cyan:          #00F0FF;
  --cyan-dim:      rgba(0, 240, 255, 0.1);
  --violet:        #8A2BE2;
  --emerald:       #00FFA3;
  --emerald-dim:   rgba(0, 255, 163, 0.1);
  --rose:          #FF0055;
  --rose-dim:      rgba(255, 0, 85, 0.1);
  --text-main:     #F8FAFC;
  --text-muted:    #94A3B8;
  
  --ff-head:       'Space Grotesk', sans-serif;
  --ff-body:       'Outfit', sans-serif;
  --ff-mono:       'Inter', monospace;
  
  --r:             12px;
  --r2:            16px;
  --blur:          backdrop-filter: blur(12px);
}

/* ══════════════════════════════════════════════
   GLOBAL
══════════════════════════════════════════════ */
html, body, [class*="css"] {
  font-family: var(--ff-body) !important;
  background: var(--bg-dark) !important;
  color: var(--text-main) !important;
}
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
  padding: 2rem 2.5rem 4rem !important;
  max-width: 1360px !important;
  background: radial-gradient(circle at top right, rgba(138, 43, 226, 0.1), transparent 40%),
              radial-gradient(circle at bottom left, rgba(0, 240, 255, 0.05), transparent 40%);
}

/* ══════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════ */
[data-testid="stSidebar"] {
  background: rgba(6, 8, 15, 0.95) !important;
  border-right: 1px solid var(--border-subtle) !important;
  backdrop-filter: blur(20px) !important;
}
[data-testid="stSidebar"] > div { padding: 2rem 1.5rem !important; }

/* ── Sidebar Custom Components ── */
@keyframes pulse {
  0% { box-shadow: 0 0 0 0 rgba(0, 255, 163, 0.4); }
  70% { box-shadow: 0 0 0 6px rgba(0, 255, 163, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 255, 163, 0); }
}
.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--emerald-dim);
  border: 1px solid rgba(0, 255, 163, 0.2);
  padding: 8px 12px;
  border-radius: var(--r);
  margin-top: 10px;
  margin-bottom: 30px;
}
.status-dot {
  height: 8px; width: 8px;
  background-color: var(--emerald);
  border-radius: 50%;
  animation: pulse 2s infinite;
}
.status-text {
  font-family: var(--ff-mono);
  font-size: 0.7rem;
  color: var(--emerald);
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
.sidebar-header {
  font-family: var(--ff-mono);
  font-size: 0.75rem;
  color: var(--cyan);
  text-transform: uppercase;
  letter-spacing: 0.15em;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 8px;
  margin-bottom: 16px;
  margin-top: 24px;
}
.pipeline-container {
  border-left: 1px solid var(--border-subtle);
  margin-left: 6px;
  padding-left: 18px;
  margin-top: 16px;
}
.pipe-step {
  position: relative;
  font-family: var(--ff-mono);
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 16px;
  line-height: 1.3;
}
.pipe-step:last-child { margin-bottom: 0; }
.pipe-step::before {
  content: '';
  position: absolute;
  left: -22.5px;
  top: 4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--bg-dark);
  border: 1px solid var(--cyan);
  transition: all 0.3s;
}
.pipe-step.active::before {
  background: var(--cyan);
  box-shadow: 0 0 8px var(--cyan);
}
.sidebar-footer {
  margin-top: 40px;
  font-family: var(--ff-mono);
  font-size: 0.65rem;
  color: var(--text-muted);
  opacity: 0.6;
  text-align: center;
}

/* ══════════════════════════════════════════════
   TABS
══════════════════════════════════════════════ */
[data-testid="stTabs"] {
  border-bottom: 1px solid var(--border-subtle) !important;
  margin-bottom: 2.5rem !important;
}
[data-testid="stTabs"] button {
  font-family: var(--ff-head) !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.05em !important;
  color: var(--text-muted) !important;
  padding: 12px 24px !important;
  border-bottom: 2px solid transparent !important;
  border-radius: 0 !important;
  background: none !important;
  transition: all 0.3s ease !important;
}
[data-testid="stTabs"] button:hover { color: var(--text-main) !important; }
[data-testid="stTabs"] button[aria-selected="true"] {
  color: var(--cyan) !important;
  border-bottom-color: var(--cyan) !important;
  text-shadow: 0 0 10px var(--cyan-dim) !important;
}

/* ══════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════ */
[data-testid="stButton"] button {
  font-family: var(--ff-head) !important;
  font-size: 0.85rem !important;
  font-weight: 600 !important;
  letter-spacing: 0.05em !important;
  text-transform: uppercase !important;
  background: linear-gradient(135deg, var(--cyan), var(--violet)) !important;
  color: #fff !important;
  border: none !important;
  border-radius: 50px !important;
  padding: 12px 32px !important;
  transition: all 0.2s ease !important;
  box-shadow: 0 4px 15px rgba(0, 240, 255, 0.2) !important;
}
[data-testid="stButton"] button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 20px rgba(138, 43, 226, 0.4) !important;
}
[data-testid="stButton"] button:active { transform: scale(0.98) !important; }

/* ══════════════════════════════════════════════
   FORM ELEMENTS
══════════════════════════════════════════════ */
[data-testid="stFileUploader"] {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--r2) !important;
  padding: 12px !important;
  backdrop-filter: blur(10px) !important;
  transition: border-color 0.3s !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--cyan) !important; }

textarea, input[type="text"] {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--r2) !important;
  color: var(--text-main) !important;
  font-family: var(--ff-body) !important;
  font-size: 0.9rem !important;
  backdrop-filter: blur(10px) !important;
  transition: all 0.3s !important;
}
textarea:focus, input:focus {
  border-color: var(--cyan) !important;
  outline: none !important;
  box-shadow: 0 0 15px var(--cyan-dim) !important;
}

/* ══════════════════════════════════════════════
   METRICS
══════════════════════════════════════════════ */
[data-testid="stMetric"] {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--r2) !important;
  padding: 20px !important;
  backdrop-filter: blur(10px) !important;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
}
[data-testid="stMetric"] label {
  font-family: var(--ff-head) !important;
  font-size: 0.75rem !important;
  font-weight: 500 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
  color: var(--text-muted) !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
  font-family: var(--ff-head) !important;
  font-size: 2.2rem !important;
  font-weight: 600 !important;
  color: var(--cyan) !important;
}

/* ══════════════════════════════════════════════
   EXPANDERS
══════════════════════════════════════════════ */
[data-testid="stExpander"] {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--r) !important;
  margin-bottom: 12px !important;
  backdrop-filter: blur(10px) !important;
}
[data-testid="stExpander"] summary {
  font-family: var(--ff-head) !important;
  font-size: 0.9rem !important;
  color: var(--text-main) !important;
  padding: 16px !important;
}
[data-testid="stExpander"] .streamlit-expanderContent {
  padding: 8px 16px 16px !important;
  font-size: 0.9rem !important;
  color: var(--text-muted) !important;
}

/* ══════════════════════════════════════════════
   CUSTOM COMPONENTS (Glass & Neon)
══════════════════════════════════════════════ */

/* ── Hero ── */
.sb-hero {
  padding: 1rem 0 3rem;
  margin-bottom: 2rem;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
}
.sb-eyebrow {
  font-family: var(--ff-mono);
  font-size: 0.7rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--cyan);
  margin-bottom: 12px;
}
.sb-name {
  font-family: var(--ff-head);
  font-size: 4rem;
  font-weight: 700;
  background: linear-gradient(to right, #FFF, var(--cyan));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
  letter-spacing: -1px;
}
.sb-name em {
  font-style: normal;
  background: linear-gradient(to right, var(--cyan), var(--violet));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.sb-sub {
  font-family: var(--ff-body);
  font-size: 1rem;
  color: var(--text-muted);
  margin-top: 12px;
}
.sb-badge {
  font-family: var(--ff-mono);
  font-size: 0.65rem;
  text-transform: uppercase;
  padding: 6px 12px;
  border-radius: 50px;
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  background: var(--bg-panel);
  backdrop-filter: blur(5px);
}

/* ── Section headers ── */
.sec-head {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 0 0 24px;
}
.sec-num {
  font-family: var(--ff-head);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--bg-dark);
  background: var(--cyan);
  border-radius: 50%;
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
}
.sec-title {
  font-family: var(--ff-head);
  font-size: 1.1rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--text-main);
}
.sec-rule { flex: 1; height: 1px; background: linear-gradient(90deg, var(--border-subtle), transparent); }

/* ── Score card ── */
.score-card {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--r2);
  padding: 30px;
  text-align: center;
  backdrop-filter: blur(12px);
  position: relative;
}
.score-number {
  font-family: var(--ff-head);
  font-size: 5.5rem;
  font-weight: 700;
  line-height: 1;
  color: var(--text-main);
}
.score-pct {
  font-size: 3rem;
  color: var(--cyan);
}
.score-verdict {
  font-family: var(--ff-mono);
  font-size: 0.8rem;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  margin: 12px 0 20px;
}
.score-bar-bg { height: 4px; background: rgba(255,255,255,0.05); border-radius: 4px; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 4px; transition: width 1s ease-out; }

/* ── Skills panels ── */
.skills-panel {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--r2);
  backdrop-filter: blur(10px);
  overflow: hidden;
}
.skills-panel-head {
  padding: 16px 20px;
  display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid var(--border-subtle);
}
.skills-panel-head-label {
  font-family: var(--ff-head);
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}
.skills-panel-head.jade { border-top: 3px solid var(--emerald); }
.skills-panel-head.rose { border-top: 3px solid var(--rose); }
.skills-panel-count { font-family: var(--ff-head); font-size: 1.8rem; font-weight: 600; }
.skills-panel-body { padding: 20px; }
.tag-row { display: flex; flex-wrap: wrap; gap: 8px; }

/* ── Tags ── */
.matched-tag {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--emerald-dim);
  border: 1px solid rgba(0,255,163,0.3);
  color: var(--emerald);
  padding: 6px 12px;
  font-family: var(--ff-mono);
  font-size: 0.75rem;
  border-radius: 50px;
}
.missing-tag {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--rose-dim);
  border: 1px solid rgba(255,0,85,0.3);
  color: var(--rose);
  padding: 6px 12px;
  font-family: var(--ff-mono);
  font-size: 0.75rem;
  border-radius: 50px;
}

.score-chip { font-size: 0.65rem; opacity: 0.8; margin-left: 4px; }
.pass-badge { font-size: 0.6rem; padding: 2px 6px; border-radius: 4px; margin-left: 6px; }
.p1, .p2, .p3, .p4, .p-impl-a, .p-impl-b, .p-impl-c, .p-impl-d {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: #fff;
}

/* ── Summary & Plans ── */
.adv-summary {
  background: var(--bg-panel);
  border-left: 4px solid var(--cyan);
  border-radius: 0 var(--r2) var(--r2) 0;
  padding: 24px;
  font-size: 1.05rem;
  line-height: 1.6;
  color: var(--text-main);
}
.plan-col, .path-card, .str-list {
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-radius: var(--r2);
  backdrop-filter: blur(10px);
}
.plan-col-head, .path-head {
  padding: 16px;
  font-family: var(--ff-head);
  font-size: 0.8rem;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  border-bottom: 1px solid var(--border-subtle);
}
.plan-col-head.w1 { color: var(--cyan); }
.plan-col-head.w2 { color: var(--violet); }
.plan-col-head.w3 { color: var(--emerald); }
.path-head.now { color: var(--cyan); }
.path-head.after { color: var(--emerald); }

.plan-item, .str-item, .path-role {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-size: 0.9rem;
  color: var(--text-muted);
}
</style>
""", unsafe_allow_html=True)


# ── HEADER ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="sb-hero">
  <div class="sb-hero-left">
    <div class="sb-eyebrow">Enterprise Process Health Monitor</div>
    <div class="sb-name">SkillBridge<em>-AI</em></div>
    <div class="sb-sub">Autonomous Orchestrator & Agentic Workflow Engine</div>
  </div>
  <div style="display: flex; gap: 10px;">
    <span class="sb-badge">Multi-Agent</span>
    <span class="sb-badge">Auditable</span>
  </div>
</div>
""", unsafe_allow_html=True)


# ── SIDEBAR ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div style="font-family:'Space Grotesk',sans-serif; font-size:1.8rem; font-weight:700; color:#00F0FF; line-height:1.2;">
            SkillBridge-AI
        </div>
        <div style="font-family:'Inter',monospace; font-size:0.65rem; color:#94A3B8; letter-spacing:0.1em; margin-bottom: 10px;">
            ET HACKATHON • ORCHESTRATOR
        </div>
        
        <div class="status-indicator">
            <div class="status-dot"></div>
            <div class="status-text">Workflow Health: Optimal</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-header">Enterprise Config</div>', unsafe_allow_html=True)
    show_scores     = st.toggle("Show Agent Diagnostics", value=True)
    show_raw_skills = st.toggle("Expose Raw Extractions", value=False)

    st.markdown('<div class="sidebar-header">Agentic Workflow</div>', unsafe_allow_html=True)

    # Dynamic agent status from session state
    agent_stats = st.session_state.get("agent_stats", {})
    if agent_stats:
        for agent_name, info in agent_stats.items():
            status = info.get("status", "pending")
            icon = {"complete": "✓", "running": "◌", "failed": "✗", "pending": "○"}.get(status, "○")
            color = {"complete": "#00FFA3", "running": "#00F0FF", "failed": "#FF0055", "pending": "#94A3B8"}.get(status, "#94A3B8")
            dur = info.get("duration_ms", 0)
            dur_str = f" · {dur:.0f}ms" if dur > 0 else ""
            st.markdown(f'<div class="pipe-step {"active" if status == "complete" else ""}" style="color:{color};"><b>{icon} {agent_name}</b><br>{status.upper()}{dur_str}</div>', unsafe_allow_html=True)
    else:
        agents_list = ["IngestionAgent", "ExtractionAgent", "AnalysisAgent", "RoutingDecision", "StrategyAgent", "ComplianceAgent"]
        for a in agents_list:
            st.markdown(f'<div class="pipe-step"><b>○ {a}</b><br>STANDBY</div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-header">Optional Setup</div>', unsafe_allow_html=True)
    st.markdown("""
        <div style="font-family:'Inter',monospace; font-size:0.75rem; color:#94A3B8; line-height:1.8;">
        Richer advice via Ollama:<br>
        <span style="color:var(--emerald);">ollama pull llama3.2</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="sidebar-footer">
            WORKFLOW READY<br>
            Awaiting Data Ingestion
        </div>
    """, unsafe_allow_html=True)


# ── CACHE ─────────────────────────────────────────────────────────────────────
_CACHE_VERSION = "v7.0"

@st.cache_resource(show_spinner="Booting neural models…")
def _load(_ver: str = _CACHE_VERSION):
    from pipeline import _get_nlp, _get_model
    _get_nlp()
    _get_model()
    return True


# ── PASS HELPERS ──────────────────────────────────────────────────────────────
def _pass_label(p) -> str:
    return {0:"—",1:"exact",2:"overlap",3:"cosine",4:"abbrev",
            "implied-A":"implied","implied-B":"implied",
            "implied-C":"implied","implied-D":"implied"}.get(p, str(p))

def _pass_css(p) -> str:
    return {0:"",1:"p1",2:"p2",3:"p3",4:"p4",
            "implied-A":"p-impl-a","implied-B":"p-impl-b",
            "implied-C":"p-impl-c","implied-D":"p-impl-d"}.get(p, "")

def _skill_tag(skill: str, kind: str, score_info: dict | None, show: bool) -> str:
    cls    = "matched-tag" if kind == "m" else "missing-tag"
    icon   = "✦" if kind == "m" else "✧"
    suffix = ""
    if show and score_info:
        sc     = score_info.get("best_score", 0)
        p      = score_info.get("pass", 0)
        bm     = score_info.get("best_match") or ""
        suffix = (
            f'<span class="score-chip">[{sc:.2f}]</span>'
            f'<span class="pass-badge {_pass_css(p)}">{_pass_label(p)}</span>'
        )
        if bm and bm.lower() != skill.lower():
            suffix += f'<span class="score-chip">→ {bm}</span>'
    return f'<span class="{cls}">{icon} {skill}{suffix}</span>'


# ── TABS ──────────────────────────────────────────────────────────────────────
tab_main, tab_matrix, tab_audit, tab_about = st.tabs(["Autonomous Output", "Agent Collaboration", "Compliance Audit", "Process Architecture"])


# ════════════════════════════════════════════════════════════════════════════════
# TAB 1 — ANALYSIS
# ════════════════════════════════════════════════════════════════════════════════
with tab_main:

    st.markdown("""<div class="sec-head">
  <span class="sec-num">1</span>
  <span class="sec-title">Data Ingestion</span>
  <span class="sec-rule"></span>
</div>""", unsafe_allow_html=True)

    col_l, col_r = st.columns(2, gap="large")
    with col_l:
        st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; color:#94A3B8; margin-bottom:8px; font-size:0.9rem;">Enterprise Candidate Payload (PDF)</div>', unsafe_allow_html=True)
        pdf_file = st.file_uploader("resume", type=["pdf"], label_visibility="collapsed")
    with col_r:
        st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; color:#94A3B8; margin-bottom:8px; font-size:0.9rem;">Target Process Requirements (JD)</div>', unsafe_allow_html=True)
        jd_text = st.text_area("jd", height=120,
            placeholder="Paste raw process requirements or JD text here...",
            label_visibility="collapsed")

    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("Execute Autonomous Pipeline", type="primary", use_container_width=True)

    if run_btn:
        if not pdf_file:
            st.error("Missing Enterprise Candidate Payload (PDF).")
            st.stop()
        if not jd_text.strip():
            st.error("Missing Target Process Requirements payload.")
            st.stop()
        with st.spinner("Orchestrating multi-agent workflow…"):
            _load(_CACHE_VERSION)
            try:
                from agent_orchestrator import run_agentic_analysis
                result = run_agentic_analysis(pdf_file.read(), jd_text)
            except ValueError as e:
                st.error(str(e)); st.stop()
            except Exception as e:
                st.error(f"Execution fault: {e}")
                with st.expander("System Traceback"):
                    st.code(traceback.format_exc(), language="python")
                st.stop()
        st.session_state.update({
            "result": result,
            "audit_trail": result.get("audit_trail", ""),
            "audit_json": result.get("audit_json", ""),
            "agent_stats": result.get("agent_stats", {}),
        })
        st.rerun()


    # ── Results
    if "result" in st.session_state:
        result  = st.session_state["result"]
        matched = result["matched_skills"]
        missing = result["missing_skills"]
        jd_sk   = result["jd_skills"]
        res_sk  = result["resume_skills"]
        scores  = result["per_skill_scores"]
        pct     = result["match_score"]

        st.markdown("<br><br>", unsafe_allow_html=True)

        st.markdown("""<div class="sec-head">
  <span class="sec-num">2</span>
  <span class="sec-title">Match Diagnostics</span>
  <span class="sec-rule"></span>
</div>""", unsafe_allow_html=True)

        g_col, m1, m2, m3 = st.columns([2.5, 1, 1, 1], gap="medium")

        route = result.get("route_taken", "strategy")
        fast_tracked = result.get("fast_tracked", False)
        redirected = result.get("redirected", False)

        if fast_tracked:
            verdict = "⚡ Fast Track"
        elif redirected:
            verdict = "🔀 Redirected"
        elif pct >= 70:
            verdict = "Optimal Fit"
        elif pct >= 40:
            verdict = "Viable Fit"
        else:
            verdict = "Low Fit"
        bar_color = "var(--emerald)" if pct >= 70 else ("var(--cyan)" if pct >= 40 else "var(--rose)")
        v_color = "#00FFA3" if pct >= 70 else ("#00F0FF" if pct >= 40 else "#FF0055")

        with g_col:
            st.markdown(f"""
<div class="score-card">
  <div class="score-number">{int(pct)}<span class="score-pct">%</span></div>
  <div class="score-verdict" style="color:{v_color}">{verdict}</div>
  <div class="score-bar-bg"><div class="score-bar-fill" style="width:{pct}%;background:{bar_color};box-shadow: 0 0 10px {bar_color};"></div></div>
</div>""", unsafe_allow_html=True)

        with m1: st.metric("Extracted JD", len(jd_sk))
        with m2: st.metric("Correlated", len(matched))
        with m3: st.metric("Deficit", len(missing))

        if show_raw_skills:
            with st.expander(f"Raw JD Extraction [{len(jd_sk)}]"):
                st.markdown('<div style="font-family:\'Inter\',monospace; font-size:0.8rem; color:#94A3B8; line-height:1.8;">' + " &nbsp;·&nbsp; ".join(jd_sk) + "</div>", unsafe_allow_html=True)
            with st.expander(f"Raw Resume Extraction [{len(res_sk)}]"):
                st.markdown('<div style="font-family:\'Inter\',monospace; font-size:0.8rem; color:#94A3B8; line-height:1.8;">' + " &nbsp;·&nbsp; ".join(res_sk) + "</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""<div class="sec-head">
  <span class="sec-num">3</span>
  <span class="sec-title">Autonomous Screening Outcome</span>
  <span class="sec-rule"></span>
</div>""", unsafe_allow_html=True)

        sk_l, sk_r = st.columns(2, gap="large")

        with sk_l:
            matched_tags = "".join(_skill_tag(s, "m", scores.get(s), show_scores) for s in sorted(matched))
            st.markdown(f"""
<div class="skills-panel">
  <div class="skills-panel-head jade">
    <span class="skills-panel-head-label">Correlated Skills</span>
    <span class="skills-panel-count" style="color:var(--emerald)">{len(matched)}</span>
  </div>
  <div class="skills-panel-body">
    <div class="tag-row">{matched_tags or '<span style="color:#94A3B8;">No correlations found.</span>'}</div>
  </div>
</div>""", unsafe_allow_html=True)

        with sk_r:
            if missing:
                missing_tags = "".join(_skill_tag(s, "x", scores.get(s), show_scores) for s in sorted(missing))
                st.markdown(f"""
<div class="skills-panel">
  <div class="skills-panel-head rose">
    <span class="skills-panel-head-label">Identified Process Deficits</span>
    <span class="skills-panel-count" style="color:var(--rose)">{len(missing)}</span>
  </div>
  <div class="skills-panel-body">
    <div class="tag-row">{missing_tags}</div>
  </div>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown("""
<div class="skills-panel" style="display:flex;align-items:center;justify-content:center;min-height:150px; border-color:var(--emerald);">
  <div style="text-align:center;">
    <div style="font-family:'Space Grotesk',sans-serif; font-size:1.5rem; color:var(--emerald); margin-bottom:8px;">100% Correlation</div>
    <div style="font-family:'Inter',monospace; font-size:0.7rem; color:#94A3B8;">No deficits identified in payload.</div>
  </div>
</div>""", unsafe_allow_html=True)


        # ── Section 04: Agent-Generated Intelligence
        advice = result.get("career_advice")
        if advice:
            st.markdown("<br><br>", unsafe_allow_html=True)

            # Dynamic section title based on route
            if fast_tracked:
                sec_title = "⚡ Fast Track — Interview Readiness"
            elif redirected:
                sec_title = "🔀 Career Redirect — Alternative Paths"
            else:
                sec_title = "Synthesized Strategy"

            st.markdown(f"""<div class="sec-head">
  <span class="sec-num">4</span>
  <span class="sec-title">{sec_title}</span>
  <span class="sec-rule"></span>
</div>""", unsafe_allow_html=True)

            # FastTrack report
            if fast_tracked:
                st.markdown(f'<div class="adv-summary" style="border-left:3px solid var(--emerald);">{advice.get("recommendation", "")}</div>', unsafe_allow_html=True)
                if advice.get("strengths"):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; font-size:1.1rem; color:var(--emerald); margin-bottom:15px;">Key Strengths</div>', unsafe_allow_html=True)
                    for s in advice["strengths"]:
                        st.markdown(f'<div class="plan-item"><span style="color:var(--emerald); margin-right:8px;">✦</span>{s}</div>', unsafe_allow_html=True)
                if advice.get("interview_prep"):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; font-size:1.1rem; color:var(--cyan); margin-bottom:15px;">Interview Preparation</div>', unsafe_allow_html=True)
                    for tip in advice["interview_prep"]:
                        st.markdown(f'<div class="plan-item"><span style="color:var(--cyan); margin-right:8px;">▹</span>{tip}</div>', unsafe_allow_html=True)

            # Redirect report
            elif redirected:
                st.markdown(f'<div class="adv-summary" style="border-left:3px solid var(--rose);">{advice.get("current_match_summary", "")}</div>', unsafe_allow_html=True)
                if advice.get("alternative_roles"):
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; font-size:1.1rem; color:var(--violet); margin-bottom:15px;">Recommended Alternative Roles</div>', unsafe_allow_html=True)
                    for role_info in advice["alternative_roles"][:5]:
                        role = role_info.get("role", "")
                        rec = role_info.get("recommendation", "")
                        skills = role_info.get("supporting_skills", [])
                        with st.expander(f"◈ {role}"):
                            st.markdown(rec)
                            if skills:
                                st.markdown("**Supporting skills:** " + " · ".join(f"`{s}`" for s in skills))
                st.markdown(f'<div class="adv-summary" style="border-left:3px solid var(--violet); margin-top:20px;">{advice.get("recommendation", "")}</div>', unsafe_allow_html=True)

            # Standard strategy report
            else:
                if advice.get("career_summary"):
                    st.markdown(f'<div class="adv-summary">{advice["career_summary"]}</div>', unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

                if advice.get("action_plan"):
                    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; font-size:1.1rem; color:var(--cyan); margin-bottom:15px;">Operational Blueprint</div>', unsafe_allow_html=True)
                    pl = advice["action_plan"]
                    pc1, pc2, pc3 = st.columns(3, gap="medium")

                    def _plan_col_html(items, head_cls, head_txt):
                        rows = "".join(f'<div class="plan-item"><span style="color:var(--cyan); margin-right:8px;">▹</span>{i}</div>' for i in items)
                        return f'<div class="plan-col"><div class="plan-col-head {head_cls}">{head_txt}</div>{rows}</div>'

                    with pc1:
                        st.markdown(_plan_col_html(pl.get("weeks_1_4",[]), "w1", "Phase 1: Acquisition"), unsafe_allow_html=True)
                    with pc2:
                        st.markdown(_plan_col_html(pl.get("weeks_5_8",[]), "w2", "Phase 2: Implementation"), unsafe_allow_html=True)
                    with pc3:
                        st.markdown(_plan_col_html(pl.get("weeks_9_12",[]), "w3", "Phase 3: Deployment"), unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)

                # RESTORED PROJECTS SECTION
                if advice.get("recommended_projects"):
                    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; font-size:1.1rem; color:var(--cyan); margin-bottom:15px; margin-top:10px;">Recommended Projects</div>', unsafe_allow_html=True)
                    for proj in advice["recommended_projects"]:
                        if isinstance(proj, str):
                            st.markdown(f"<div class='plan-item' style='background:var(--bg-panel); border:1px solid var(--border-subtle); border-radius:var(--r2); margin-bottom:10px;'><span style='color:var(--emerald); margin-right:8px;'>◈</span>{proj}</div>", unsafe_allow_html=True)
                        else:
                            with st.expander(f"⚡ {proj.get('name','Project').upper()}"):
                                if proj.get("description"): st.markdown(f"**Description:** {proj['description']}")
                                if proj.get("intuition"):   st.markdown(f"**Why:** {proj['intuition']}")
                                if proj.get("tech_stack"):  st.markdown(f"**Stack:** `{proj['tech_stack']}`")
                                if proj.get("skills_covered"): st.markdown("**Covers:** " + " · ".join(f"`{s}`" for s in proj["skills_covered"]))
                    st.markdown("<br>", unsafe_allow_html=True)

                if advice.get("career_paths"):
                    cp = advice["career_paths"]
                    st.markdown('<div style="font-family:\'Space Grotesk\',sans-serif; font-size:1.1rem; color:var(--cyan); margin-bottom:15px;">Trajectory Mapping</div>', unsafe_allow_html=True)
                    cp1, cp2 = st.columns(2, gap="large")

                    def _path_col_html(roles, head_cls, label, color):
                        rows = "".join(f'<div class="path-role"><span style="color:{color}; margin-right:10px;">◈</span>{r}</div>' for r in roles)
                        return f'<div class="path-card"><div class="path-head {head_cls}">{label}</div>{rows}</div>'

                    with cp1:
                        st.markdown(_path_col_html(cp.get("immediate",[]), "now", "Current Viability", "var(--cyan)"), unsafe_allow_html=True)
                    with cp2:
                        st.markdown(_path_col_html(cp.get("after_upskilling",[]), "after", "Post-Upskill Potential", "var(--emerald)"), unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════════════
# TAB 2 — SIMILARITY MATRIX
# ════════════════════════════════════════════════════════════════════════════════
with tab_matrix:
    if "result" not in st.session_state:
        st.info("Awaiting pipeline execution to generate vector matrix.")
    else:
        result = st.session_state["result"]
        mat    = result["sim_matrix"]
        jd_sk  = result["jd_skills"]
        res_sk = result["resume_skills"]

        st.markdown(f"""<div style="display:flex; gap:30px; margin-bottom:20px; font-family:'Inter',monospace; font-size:0.8rem; color:#94A3B8;">
  <span>Process Requirement Vectors: <strong style="color:var(--cyan)">{len(jd_sk)}</strong></span>
  <span>Candidate Payload Vectors: <strong style="color:var(--cyan)">{len(res_sk)}</strong></span>
  <span>Activation Threshold: <strong style="color:var(--cyan)">0.65</strong></span>
</div>""", unsafe_allow_html=True)

        import pandas as pd
        MAX = 30
        df  = pd.DataFrame(mat[:MAX,:MAX], index=jd_sk[:MAX], columns=res_sk[:MAX]).round(2)

        def _color_cell(val: float) -> str:
            # Modern Neon Cyberpunk Matrix colors (Deep Purple -> Cyan -> Emerald)
            v = max(0.0, min(1.0, float(val)))
            if v < 0.5:
                # Purple to Deep Blue
                t = v / 0.5
                r, g, b = int(30 - t*30), int(10 + t*40), int(40 + t*60)
            else:
                # Blue/Cyan to Emerald
                t = (v - 0.5) / 0.5
                r = 0
                g = int(50 + t * 205)
                b = int(100 + t * 63)
            return f"background-color:rgb({r},{g},{b});color:#fff;font-family:'Inter',monospace;font-size:0.85rem;"

        st.dataframe(df.style.map(_color_cell), use_container_width=True, height=min(600, 35*len(df)+40))
        if len(jd_sk) > MAX or len(res_sk) > MAX:
            st.caption(f"Showing localized subset ({MAX}×{MAX}) of global {len(jd_sk)}×{len(res_sk)} matrix.")


# ════════════════════════════════════════════════════════════════════════════════
# TAB 3 — AUDIT TRAIL
# ════════════════════════════════════════════════════════════════════════════════
with tab_audit:
    if "audit_trail" not in st.session_state:
        st.info("Execute autonomous pipeline to view the immutable agent audit trail. Every exception handled and routing choice will be logged here.")
    else:
        st.markdown("""<div class="sec-head">
  <span class="sec-num">A</span>
  <span class="sec-title">Agent Decision Log</span>
  <span class="sec-rule"></span>
</div>""", unsafe_allow_html=True)

        # Agent status dashboard
        agent_stats = st.session_state.get("agent_stats", {})
        if agent_stats:
            cols = st.columns(min(len(agent_stats), 4))
            for i, (name, info) in enumerate(agent_stats.items()):
                with cols[i % 4]:
                    status = info.get("status", "pending")
                    color = {"complete": "#00FFA3", "running": "#00F0FF", "failed": "#FF0055"}.get(status, "#94A3B8")
                    st.markdown(f"""
<div style="background:var(--bg-panel); border:1px solid var(--border-subtle); border-radius:var(--r2); padding:16px; text-align:center;">
  <div style="font-family:'Space Grotesk',sans-serif; font-size:0.75rem; color:#94A3B8; letter-spacing:0.1em; text-transform:uppercase;">{name}</div>
  <div style="font-family:'Space Grotesk',sans-serif; font-size:1.2rem; color:{color}; margin-top:6px;">{status.upper()}</div>
  <div style="font-family:'Inter',monospace; font-size:0.7rem; color:#94A3B8; margin-top:4px;">{info.get('decisions',0)} decisions · {info.get('duration_ms',0):.0f}ms</div>
</div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Human-readable audit trail
        audit_text = st.session_state.get("audit_trail", "")
        st.code(audit_text, language="text")

        # Downloadable JSON
        audit_json = st.session_state.get("audit_json", "")
        if audit_json:
            st.download_button(
                "Download Full Audit (JSON)",
                audit_json,
                file_name="audit_trail.json",
                mime="application/json",
            )


# ════════════════════════════════════════════════════════════════════════════════
# TAB 4 — SYSTEM CONFIG
# ════════════════════════════════════════════════════════════════════════════════
with tab_about:
    st.markdown("### Agentic Architecture")
    st.code("""Payload (PDF)
  └─ IngestionAgent (pdfplumber + OCR fallback)
  └─ ExtractionAgent (spaCy NLP + Semantic Gate)
  └─ AnalysisAgent (7-Pass Classifier + Implication Engine)
  └─ ⇒ ROUTING DECISION
      ├─ >90%  → FastTrackAgent (Interview Readiness)
      ├─ 40-90% → StrategyAgent (Career Plan)
      └─ <40%  → RedirectAgent (Alt Roles)
  └─ ComplianceAgent (Bias/Hallucination Check)
  └─ ↺ Self-Correction Loop (if compliance fails)
  └─ Final Report""", language="text")