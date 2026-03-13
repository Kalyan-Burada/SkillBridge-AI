"""
app.py  —  Career Copilot Streamlit app (fully offline).

Run:
    streamlit run app.py

All analysis logic is in pipeline.py — no duplication.
Works for any resume and any job description, any industry.
"""
import io
import os
import streamlit as st

st.set_page_config(
    page_title="Career Copilot — Skill Gap Analyzer",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base ── */
.hero-title {
    font-size: 2.6rem; font-weight: 800; color: #00e5b0;
    text-align: center; margin-bottom: .25rem; letter-spacing: -1.5px;
}
.hero-sub {
    font-size: 1rem; color: #94a3b8; text-align: center; margin-bottom: 1.6rem;
}
.privacy-note {
    text-align: center; font-size: .78rem; color: #475569;
    margin-bottom: 2rem;
}

/* ── Skill tags ── */
.tag-row { display: flex; flex-wrap: wrap; gap: 5px; }

.matched-tag {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(0,229,176,.1); border: 1px solid rgba(0,229,176,.28);
    color: #00e5b0; border-radius: 6px; padding: 3px 10px;
    font-size: .82rem; transition: opacity .15s;
}
.missing-tag {
    display: inline-flex; align-items: center; gap: 5px;
    background: rgba(255,77,109,.1); border: 1px solid rgba(255,77,109,.28);
    color: #ff4d6d; border-radius: 6px; padding: 3px 10px;
    font-size: .82rem;
}
.score-chip { font-size: .67rem; color: #64748b; margin-left: 3px; }
.pass-badge {
    font-size: .62rem; padding: 1px 5px; border-radius: 3px; margin-left: 2px;
}
.p1 { background: #1e3a5f; color: #60a5fa; }
.p2 { background: #1a3320; color: #4ade80; }
.p3 { background: #2a1f40; color: #a78bfa; }
.p4 { background: #3a2510; color: #fb923c; }

/* ── Advice blocks ── */
.adv-summary {
    background: rgba(0,229,176,.05);
    border: 1px solid rgba(0,229,176,.14);
    border-radius: 8px; padding: 14px 16px;
    font-size: 13.5px; line-height: 1.7;
}
.str-item {
    display: flex; align-items: flex-start; gap: 7px;
    padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,.06);
    font-size: 12.5px;
}
.str-item:last-child { border-bottom: none; }
.str-ico { color: #00e5b0; font-size: 10px; margin-top: 4px; }

/* ── Plan columns ── */
.plan-col {
    background: rgba(255,255,255,.03);
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 8px; padding: 14px;
}
.plan-item {
    font-size: 12px; color: #94a3b8; padding: 4px 0;
    border-bottom: 1px solid rgba(255,255,255,.05);
    line-height: 1.55;
}
.plan-item:last-child { border-bottom: none; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="hero-title">🚀 Career Copilot</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Offline Skill Gap Analyzer — '
    'works for any industry and any job role</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="privacy-note">🔒 Your documents never leave your machine · '
    'No API key · No internet required</div>',
    unsafe_allow_html=True,
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    show_scores     = st.toggle("Show similarity scores & match type", value=True)
    show_raw_skills = st.toggle("Show all extracted skills", value=False)
    st.divider()

    st.markdown("""
### How it works
1. **PDF parsed** with pdfplumber
2. **Skills extracted** via spaCy NLP
   - Noun chunks, named entities, PROPN tokens
   - Hard-signal bypass for ALL-CAPS / CamelCase / digit / special-char tokens
   - Zero-shot SentenceTransformer classifier filters noise
   - **Domain-agnostic**: works for software, finance, healthcare, supply-chain, marketing, legal, and more
3. **Embeddings** with `all-MiniLM-L6-v2`
4. **Cosine similarity matrix** (n_jd × n_resume)
5. **4-pass matching:**
   - ① Exact string match
   - ② Token-overlap ≥ 85 %
   - ③ Cosine sim ≥ 0.80
   - ④ Abbreviation / initialism

### Why threshold 0.80?
At 0.75 these would **falsely match**:
- react ↔ angular ~0.72
- docker ↔ kubernetes ~0.74
- sql ↔ nosql ~0.76

### Optional richer advice
Install [Ollama](https://ollama.com) and run:
```bash
ollama pull llama3.2
```
Career Copilot detects it automatically.
""")

# ── Cache model loading ───────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading NLP models (first run ~20 s)…")
def _load():
    from pipeline import run_analysis, _get_nlp, _get_model
    _get_nlp()
    _get_model()
    try:
        from llm_client import get_llm_client
        llm = get_llm_client()
    except Exception:
        llm = None
    try:
        from rag_engine import get_rag_engine
        rag = get_rag_engine()
    except Exception:
        rag = None
    return run_analysis, llm, rag


_PASS_LABEL = {1: "exact", 2: "overlap", 3: "cosine", 4: "abbrev", 0: "—"}
_PASS_CSS   = {1: "p1",    2: "p2",      3: "p3",     4: "p4",     0: ""}


def _skill_tag(skill: str, kind: str, score_info: dict | None, show: bool) -> str:
    cls  = "matched-tag" if kind == "m" else "missing-tag"
    icon = "✓" if kind == "m" else "✕"
    suffix = ""
    if show and score_info:
        sc   = score_info.get("best_score", 0)
        p    = score_info.get("pass", 0)
        bm   = score_info.get("best_match") or ""
        plbl = _PASS_LABEL.get(p, "")
        pcls = _PASS_CSS.get(p, "")
        suffix = (
            f'<span class="score-chip">{sc:.2f}</span>'
            f'<span class="pass-badge {pcls}">{plbl}</span>'
        )
        if bm and bm.lower() != skill.lower():
            suffix += f'<span class="score-chip">→ {bm}</span>'
    return f'<span class="{cls}">{icon} {skill}{suffix}</span>'


# ── Main UI ───────────────────────────────────────────────────────────────────
tab_main, tab_matrix, tab_about = st.tabs([
    "📄 Analysis", "🔢 Similarity Matrix", "ℹ️ About"
])

with tab_main:
    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("#### 📄 Resume (PDF)")
        pdf_file = st.file_uploader(
            "Upload PDF", type=["pdf"], label_visibility="collapsed"
        )

    with col_r:
        st.markdown("#### 📋 Job Description")
        jd_text = st.text_area(
            "Job Description",
            height=200,
            placeholder=(
                "Paste the full job description here…\n\n"
                "Works for any role: software engineer, data analyst, "
                "product manager, nurse, financial analyst, supply chain "
                "manager, UX designer, lawyer — any industry."
            ),
            label_visibility="collapsed",
        )

    run_btn = st.button(
        "🔍 Analyze Skill Gap", type="primary", use_container_width=True
    )

    if run_btn:
        if not pdf_file:
            st.error("⚠️ Please upload a PDF resume.")
            st.stop()
        if not jd_text.strip():
            st.error("⚠️ Please paste a job description.")
            st.stop()

        with st.spinner("Loading models and analysing… (first run may take ~30 s)"):
            run_analysis, llm, rag = _load()
            try:
                result = run_analysis(pdf_file.read(), jd_text)
            except ValueError as e:
                st.error(f"❌ {e}")
                st.stop()
            except Exception as e:
                st.error(f"❌ Analysis failed: {e}")
                st.stop()

        st.session_state["result"] = result
        st.session_state["llm"]    = llm
        st.session_state["rag"]    = rag

    # ── Results ───────────────────────────────────────────────────────────────
    if "result" in st.session_state:
        result  = st.session_state["result"]
        llm     = st.session_state.get("llm")
        rag     = st.session_state.get("rag")

        matched = result["matched_skills"]
        missing = result["missing_skills"]
        jd_sk   = result["jd_skills"]
        res_sk  = result["resume_skills"]
        scores  = result["per_skill_scores"]
        pct     = result["match_score"]

        # ── Metrics row
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Match Score",  f"{pct:.1f}%")
        c2.metric("JD Skills",     len(jd_sk))
        c3.metric("✅ Matched",    len(matched))
        c4.metric("❌ Missing",    len(missing))

        colour = "green" if pct >= 70 else ("orange" if pct >= 40 else "red")
        st.progress(int(pct))

        # ── Raw skills (optional)
        if show_raw_skills:
            with st.expander(f"All JD skills extracted ({len(jd_sk)})"):
                st.write(", ".join(jd_sk))
            with st.expander(f"All resume skills extracted ({len(res_sk)})"):
                st.write(", ".join(res_sk))

        # ── Matched / Missing columns
        st.divider()
        col_m, col_x = st.columns(2)

        with col_m:
            st.markdown(f"#### ✅ Matched Skills &nbsp;`{len(matched)}`")
            html = '<div class="tag-row">' + "".join(
                _skill_tag(s, "m", scores.get(s), show_scores)
                for s in sorted(matched)
            ) + "</div>"
            st.markdown(html or "_None matched_", unsafe_allow_html=True)

        with col_x:
            st.markdown(f"#### ❌ Missing Skills &nbsp;`{len(missing)}`")
            if missing:
                html = '<div class="tag-row">' + "".join(
                    _skill_tag(s, "x", scores.get(s), show_scores)
                    for s in sorted(missing)
                ) + "</div>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.success("🎉 All JD skills are present in your resume!")

        # ── Career advice
        if missing and llm:
            st.divider()
            st.markdown("#### 🎯 Career Guidance")

            with st.spinner("Generating personalised roadmap…"):
                try:
                    contexts = (
                        rag.get_context_for_missing_skills(missing[:5])
                        if rag else []
                    )
                    advice = llm.generate_career_advice(
                        matched_skills=matched,
                        missing_skills=missing,
                        skill_contexts=contexts,
                        job_description=jd_text,
                    )
                except Exception as e:
                    st.warning(f"Career advice unavailable: {e}")
                    advice = None

            if advice:
                # Summary
                if advice.get("career_summary"):
                    st.markdown(
                        f'<div class="adv-summary">{advice["career_summary"]}</div>',
                        unsafe_allow_html=True,
                    )

                # Strengths
                if advice.get("strengths"):
                    st.markdown("**💪 Your Strengths**")
                    html = "".join(
                        f'<div class="str-item"><span class="str-ico">✓</span>{s}</div>'
                        for s in advice["strengths"]
                    )
                    st.markdown(html, unsafe_allow_html=True)

                # Priority skills
                if advice.get("priority_skills"):
                    st.markdown("**🎯 Priority Skills to Develop**")
                    for i, sk in enumerate(advice["priority_skills"], 1):
                        with st.expander(
                            f"#{i} — **{sk.get('skill','')}** · ⏱ {sk.get('timeline','')}"
                        ):
                            if sk.get("reason"):
                                st.markdown(f"**Why:** {sk['reason']}")
                            if sk.get("actions"):
                                st.markdown("**Steps:**")
                                for a in sk["actions"]:
                                    st.markdown(f"• {a}")

                # 90-day plan
                if advice.get("action_plan"):
                    st.markdown("**📅 90-Day Action Plan**")
                    pl = advice["action_plan"]
                    pcols = st.columns(3)
                    with pcols[0]:
                        st.markdown("**📖 Weeks 1–4**")
                        items = "\n".join(
                            f'<div class="plan-item">• {i}</div>'
                            for i in pl.get("weeks_1_4", [])
                        )
                        st.markdown(
                            f'<div class="plan-col">{items}</div>',
                            unsafe_allow_html=True,
                        )
                    with pcols[1]:
                        st.markdown("**🔨 Weeks 5–8**")
                        items = "\n".join(
                            f'<div class="plan-item">• {i}</div>'
                            for i in pl.get("weeks_5_8", [])
                        )
                        st.markdown(
                            f'<div class="plan-col">{items}</div>',
                            unsafe_allow_html=True,
                        )
                    with pcols[2]:
                        st.markdown("**🚀 Weeks 9–12**")
                        items = "\n".join(
                            f'<div class="plan-item">• {i}</div>'
                            for i in pl.get("weeks_9_12", [])
                        )
                        st.markdown(
                            f'<div class="plan-col">{items}</div>',
                            unsafe_allow_html=True,
                        )

                # Recommended projects
                if advice.get("recommended_projects"):
                    st.markdown("**🚀 Recommended Projects**")
                    for proj in advice["recommended_projects"]:
                        if isinstance(proj, str):
                            st.markdown(f"- {proj}")
                        else:
                            with st.expander(f"📁 {proj.get('name', 'Project')}"):
                                if proj.get("description"):
                                    st.markdown(proj["description"])
                                if proj.get("intuition"):
                                    st.markdown(f"**Why:** {proj['intuition']}")
                                if proj.get("tech_stack"):
                                    st.markdown(f"**Stack:** {proj['tech_stack']}")
                                if proj.get("skills_covered"):
                                    st.markdown(
                                        "**Covers:** " + ", ".join(proj["skills_covered"])
                                    )

                # Career paths
                if advice.get("career_paths"):
                    cp = advice["career_paths"]
                    st.markdown("**🗺️ Career Paths**")
                    cc1, cc2 = st.columns(2)
                    with cc1:
                        st.markdown("*Immediate roles:*")
                        for r in cp.get("immediate", []):
                            st.markdown(f"• {r}")
                    with cc2:
                        st.markdown("*After upskilling:*")
                        for r in cp.get("after_upskilling", []):
                            st.markdown(f"• {r}")

# ── Tab 2: Similarity matrix ──────────────────────────────────────────────────
with tab_matrix:
    if "result" not in st.session_state:
        st.info("Run an analysis first to see the cosine similarity matrix.")
    else:
        result = st.session_state["result"]
        mat    = result["sim_matrix"]
        jd_sk  = result["jd_skills"]
        res_sk = result["resume_skills"]

        st.markdown(
            f"Full **(n_jd={len(jd_sk)}) × (n_resume={len(res_sk)})** "
            "cosine similarity matrix."
        )
        st.caption(
            "Each cell = cosine similarity between one JD skill (row) and one "
            f"resume skill (column). Match threshold: **{0.80}**."
        )

        import pandas as pd

        MAX = 30
        df  = pd.DataFrame(
            mat[:MAX, :MAX],
            index=jd_sk[:MAX],
            columns=res_sk[:MAX],
        ).round(2)

        st.dataframe(
            df.style.background_gradient(cmap="RdYlGn", vmin=0, vmax=1),
            use_container_width=True,
            height=min(600, 28 * len(df) + 40),
        )
        if len(jd_sk) > MAX or len(res_sk) > MAX:
            st.caption(f"Showing first {MAX} rows and {MAX} columns.")

# ── Tab 3: About ──────────────────────────────────────────────────────────────
with tab_about:
    st.markdown("""
### Pipeline

```
PDF bytes
  └─▶  pdfplumber           → raw text
         └─▶  spaCy NLP      → skill candidates
               (noun-chunks, named entities,
                PROPN tokens, hard-signal bypass,
                zero-shot SentenceTransformer classifier)
                └─▶  all-MiniLM-L6-v2   → embeddings (384-dim, L2-normalised)
                       └─▶  cosine similarity matrix  (n_jd × n_resume)
                              └─▶  4-pass classifier
                                    ① exact string match
                                    ② token-overlap ≥ 85 %
                                    ③ cosine sim ≥ 0.80
                                    ④ abbreviation / initialism
                                     └─▶  matched / missing lists
```

### Technology stack

| Component | Library | Offline? |
|-----------|---------|----------|
| PDF parsing | pdfplumber | ✅ |
| NLP extraction | spaCy `en_core_web_sm` | ✅ |
| Zero-shot skill classifier | `all-MiniLM-L6-v2` | ✅ |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | ✅ |
| Career advice | Template engine | ✅ |
| Richer advice | Ollama `llama3.2` *(optional)* | ✅ |

### Domain coverage

Works out-of-the-box for:
- **Software / Tech**: frontend, backend, data, cloud, DevOps, ML
- **Business**: product management, project management, operations
- **Finance**: financial analysis, accounting, FP&A
- **Healthcare**: clinical research, EHR, nursing, pharmacy
- **Design**: UI/UX, graphic design, brand
- **Marketing**: digital, content, growth, SEO
- **Supply chain / manufacturing**: logistics, procurement, demand planning
- **Legal / compliance**: regulatory affairs, contracts, audit
- **Any other domain**: the zero-shot classifier adapts automatically

### Install

```bash
pip install streamlit fastapi uvicorn pdfplumber spacy \\
            sentence-transformers numpy pandas python-dotenv faiss-cpu
python -m spacy download en_core_web_sm
python -m nltk.downloader stopwords
# Optional richer advice:
# Install Ollama → https://ollama.com  then:  ollama pull llama3.2
```
""")