"""
debug_crash.py  —  Hardcoded test, no arguments needed.

Run:
    python debug_crash.py
"""
import sys
import traceback
import io

# ── Synthetic test inputs ─────────────────────────────────────────────────────
JD_TEXT = """
We are looking for a Data Scientist to join our team.

Requirements:
- Python programming
- Machine learning algorithms (regression, classification, clustering)
- Data analysis and statistical modelling
- SQL for data querying
- Pandas and NumPy for data manipulation
- Scikit-learn or TensorFlow for model building
- Data visualisation (Matplotlib, Seaborn, or Tableau)
- Git version control
- Communication and presentation skills
- Experience with cloud platforms (AWS or GCP)
"""

RESUME_TEXT = """
John Doe
john.doe@email.com

EXPERIENCE
----------
Data Analyst, Acme Corp (2021-2024)
- Built and deployed machine learning models using scikit-learn and TensorFlow
- Performed exploratory data analysis with pandas and NumPy on large datasets
- Designed and optimised SQL queries for reporting and business intelligence
- Created interactive dashboards using Matplotlib and Seaborn
- Collaborated with cross-functional teams using Git for version control
- Presented findings to senior stakeholders using clear visualisations

EDUCATION
---------
B.Sc. Computer Science, University of Kerala (2021)

SKILLS
------
scikit-learn, TensorFlow, pandas, NumPy, SQL, Matplotlib, Seaborn, Git
"""


# ── Build a minimal valid PDF pdfplumber can read ────────────────────────────
def _make_pdf(text: str) -> bytes:
    # Try reportlab first
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        y = 750
        for line in text.strip().splitlines():
            c.drawString(40, y, line[:110])
            y -= 14
            if y < 50:
                c.showPage(); y = 750
        c.save()
        return buf.getvalue()
    except ImportError:
        pass

    # Try fpdf2
    try:
        from fpdf import FPDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=11)
        for line in text.strip().splitlines():
            pdf.cell(0, 6, line[:110], ln=True)
        return pdf.output(dest="S").encode("latin-1")
    except ImportError:
        pass

    # Hand-craft a minimal PDF (no external deps)
    safe = text.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")
    lines = safe.strip().splitlines()
    ops, y = [], 750
    for ln in lines:
        ops.append(f"BT /F1 10 Tf 40 {y} Td ({ln[:120]}) Tj ET")
        y -= 13
        if y < 50: y = 750
    stream = "\n".join(ops).encode("latin-1")
    slen   = len(stream)

    parts  = [b"%PDF-1.4\n"]
    o = [0]*6
    o[1] = len(b"".join(parts)); parts.append(b"1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n")
    o[2] = len(b"".join(parts)); parts.append(b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n")
    o[3] = len(b"".join(parts)); parts.append(b"3 0 obj\n<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>\nendobj\n")
    o[4] = len(b"".join(parts)); parts.append(f"4 0 obj\n<</Length {slen}>>\nstream\n".encode() + stream + b"\nendstream\nendobj\n")
    o[5] = len(b"".join(parts)); parts.append(b"5 0 obj\n<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>\nendobj\n")
    xoff = len(b"".join(parts))
    parts.append((
        f"xref\n0 6\n0000000000 65535 f \n"
        + "".join(f"{o[i]:010d} 00000 n \n" for i in range(1,6))
        + f"trailer\n<</Size 6/Root 1 0 R>>\nstartxref\n{xoff}\n%%EOF\n"
    ).encode())
    return b"".join(parts)


# ── Helpers ───────────────────────────────────────────────────────────────────
SEP = "=" * 65

def step(n, label):
    print(f"\n{SEP}")
    print(f"  STEP {n}: {label}")
    print(SEP)

def ok(msg):   print(f"  ✓  {msg}")
def warn(msg): print(f"  ⚠  {msg}")

def fail(label):
    print(f"  ✗  CRASHED in: {label}")
    print()
    traceback.print_exc()
    print(f"\n{'='*65}")
    print("  ^^^ THIS IS THE REAL ERROR ^^^")
    print(f"{'='*65}")
    sys.exit(1)


# ── Steps ─────────────────────────────────────────────────────────────────────

step(1, "Build fake PDF")
try:
    pdf_bytes = _make_pdf(RESUME_TEXT)
    ok(f"PDF ready ({len(pdf_bytes)} bytes)")
except Exception:
    fail("_make_pdf")

step(2, "Import pipeline")
try:
    from pipeline import (
        run_analysis, extract_skills,
        classify_gaps, build_similarity_matrix,
        _get_nlp, _get_model,
    )
    ok("pipeline imported")
except Exception:
    fail("import pipeline")

step(3, "Import implication_engine")
try:
    from implication_engine import ImplicationEngine
    ok("implication_engine imported")
except Exception:
    fail("import implication_engine")

step(4, "Load spaCy model")
try:
    nlp = _get_nlp()
    ok(f"spaCy: {nlp.meta['name']}")
except Exception:
    fail("_get_nlp()")

step(5, "Load SentenceTransformer")
try:
    model = _get_model()
    ok(f"SentenceTransformer: {type(model).__name__}")
except Exception:
    fail("_get_model()")

step(6, "extract_skills — JD")
try:
    jd_skills = extract_skills(JD_TEXT)
    ok(f"{len(jd_skills)} skills extracted")
    for s in jd_skills: print(f"     {s}")
except Exception:
    fail("extract_skills(JD_TEXT)")

step(7, "extract_skills — Resume")
try:
    resume_skills = extract_skills(RESUME_TEXT)
    ok(f"{len(resume_skills)} skills extracted")
    for s in resume_skills: print(f"     {s}")
except Exception:
    fail("extract_skills(RESUME_TEXT)")

step(8, "build_similarity_matrix")
try:
    sim_matrix, _, __ = build_similarity_matrix(jd_skills, resume_skills)
    ok(f"shape: {sim_matrix.shape}")
except Exception:
    fail("build_similarity_matrix")

step(9, "classify_gaps — all 7 passes")
try:
    matched, missing, scores = classify_gaps(
        jd_skills, resume_skills, sim_matrix, RESUME_TEXT
    )
    ok(f"matched={len(matched)}  missing={len(missing)}")
    print()
    print("  Per-skill results:")
    for skill in sorted(jd_skills):
        info    = scores.get(skill, {})
        p       = info.get("pass", "?")
        sc      = info.get("best_score", 0.0)
        bm      = info.get("best_match", "-")
        verdict = "MATCHED" if skill in matched else "MISSING"
        print(f"    [{verdict:7s}]  pass={str(p):12s}  score={sc:.3f}  '{skill}' -> '{bm}'")
except Exception:
    fail("classify_gaps")

step(10, "ImplicationEngine — standalone")
try:
    engine = ImplicationEngine(RESUME_TEXT)
    ok(f"created — {len(engine._windows)} text windows")
    implied = engine.find_implied_skills(jd_skills, resume_skills, missing)
    ok(f"implied: {list(implied.keys())}")
    if "python" in [s.lower() for s in missing]:
        if any("python" in k.lower() for k in implied):
            ok("'python' correctly implied ✓")
        else:
            warn("'python' not flagged as implied — threshold may need tuning")
except Exception:
    fail("ImplicationEngine")

step(11, "run_analysis — full end-to-end with real PDF bytes")
try:
    result = run_analysis(pdf_bytes, JD_TEXT)
    ok(f"match_score : {result['match_score']}%")
    ok(f"matched     : {sorted(result['matched_skills'])}")
    ok(f"missing     : {sorted(result['missing_skills'])}")
    print()
    print("  pass-value types (must never be non-str/int):")
    for skill, info in sorted(result["per_skill_scores"].items()):
        p = info.get("pass")
        print(f"    {skill!r:40s}  pass={p!r:15}  type={type(p).__name__}")
except Exception:
    fail("run_analysis")

print(f"\n{SEP}")
print("  ALL 11 STEPS PASSED ✓")
print(f"{SEP}")
print("  Pipeline is working. If the app still crashes:")
print("  1. Make sure app.py + api_server.py are the latest fixed versions")
print("  2. Run:  streamlit cache clear")
print("  3. Restart the app completely (Ctrl+C then re-run)")
print(SEP)