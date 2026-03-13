"""
skill_gap_analyzer.py  —  Career Copilot Core Engine (self-contained, offline)
══════════════════════════════════════════════════════════════════════════════
Dependencies (minimal):
    pip install pdfplumber numpy

Zero API keys. Zero internet. Works completely offline.

ALL BUGS FIXED
──────────────
Bug 1 — _token_overlap() ALWAYS returned 1.0 for single-word JD skills   [CRITICAL]
         Root cause: len(shorter & (ta | tb))
           When shorter == ta, shorter ⊆ (ta ∪ tb) by definition → always 1.0
           Every single-word JD skill ("css", "git", "angular") was matching
           any resume skill regardless of content.
         Fix: len(shorter & longer)  — intersect with the OTHER set only.

Bug 2 — Possessives broke token matching
         "bachelor's degree" tokenises to {"bachelor's", "degree"}.
         "bachelor" tokenises to {"bachelor"}.
         These share zero tokens despite being the same concept.
         Fix: strip possessive "'s" and hyphens before tokenising.

Bug 3 — "frontend" vs "front-end" treated as unrelated skills
         Fix: normalise hyphens/spaces before deduplication.

Bug 4 — is_abbreviation() matched every 2-4 letter lowercase word
         ("rest", "data", "git") producing false abbreviation matches.
         Fix: only ALL-CAPS tokens and digit/special-char tokens are abbreviations.

Bug 5 — api_server.py returned Pydantic SkillScore objects in JSON dict
         Fix: call .model_dump() before building the response.
"""

from __future__ import annotations
import re, io, math
from collections import Counter
from typing import List, Tuple, Dict, Set


# ══════════════════════════════════════════════════════════════════════════════
# SKILL DICTIONARY
# ══════════════════════════════════════════════════════════════════════════════
_RAW_SKILLS: List[str] = [
    # ── Frontend ──────────────────────────────────────────────────────────
    "html", "html5", "css", "css3", "javascript", "typescript",
    "react", "react.js", "reactjs", "redux", "next.js",
    "vue", "vue.js", "angular", "angularjs",
    "svelte", "jquery", "bootstrap", "tailwind",
    "sass", "scss", "webpack", "vite", "babel",
    "responsive design", "mobile-first", "mobile first",
    "cross-browser", "cross browser compatibility",
    "ui/ux", "user interface", "ux design", "ui design",
    "design systems", "wireframes", "figma", "adobe xd",
    "front-end", "frontend", "front end",
    "accessibility", "wcag", "progressive web app",
    # ── Backend ───────────────────────────────────────────────────────────
    "node.js", "nodejs", "express", "fastapi", "django",
    "flask", "spring boot", "asp.net", ".net", "laravel",
    "rest api", "restful api", "restful", "graphql",
    "websocket", "microservices", "api design",
    # ── Languages ─────────────────────────────────────────────────────────
    "python", "java", "c++", "c#", "go", "golang", "rust",
    "swift", "kotlin", "php", "ruby", "scala", "matlab",
    "bash", "shell", "powershell", "embedded c", "embedded c++",
    # ── Databases ─────────────────────────────────────────────────────────
    "sql", "mysql", "postgresql", "postgres", "sqlite",
    "nosql", "mongodb", "redis", "elasticsearch", "firebase",
    # ── Cloud / DevOps ────────────────────────────────────────────────────
    "aws", "amazon web services", "azure", "microsoft azure",
    "google cloud", "gcp", "docker", "kubernetes", "terraform",
    "ansible", "jenkins", "github actions", "gitlab ci", "ci/cd",
    "continuous integration", "continuous deployment", "devops",
    "linux", "unix", "nginx",
    # ── Version Control ───────────────────────────────────────────────────
    "git", "github", "gitlab", "bitbucket", "version control",
    # ── Testing ───────────────────────────────────────────────────────────
    "unit testing", "integration testing", "e2e testing",
    "jest", "mocha", "cypress", "playwright", "selenium", "pytest",
    "testing", "a/b testing", "ab testing",
    # ── Methodologies ─────────────────────────────────────────────────────
    "agile", "scrum", "kanban", "jira", "sprint", "product backlog",
    # ── Data / ML ─────────────────────────────────────────────────────────
    "machine learning", "deep learning", "artificial intelligence",
    "natural language processing", "computer vision",
    "data analysis", "data analytics", "data science",
    "tensorflow", "pytorch", "keras", "scikit-learn",
    "pandas", "numpy", "tableau", "power bi",
    "etl", "data pipeline", "data warehouse",
    # ── Embedded / Hardware ───────────────────────────────────────────────
    "embedded systems", "embedded system", "firmware", "rtos",
    "microcontroller", "microcontrollers", "arduino", "raspberry pi",
    "fpga", "can bus", "i2c", "spi", "uart",
    "plc", "programmable logic controller", "iot",
    "hardware integration", "hardware design", "pcb design",
    # ── Mobile ────────────────────────────────────────────────────────────
    "ios", "android", "react native", "flutter",
    # ── Security ──────────────────────────────────────────────────────────
    "cybersecurity", "oauth", "jwt", "ssl", "tls", "encryption",
    # ── Soft / Domain ─────────────────────────────────────────────────────
    "problem solving", "problem-solving",
    "communication", "teamwork", "collaboration", "leadership",
    "project management", "attention to detail",
    "code review", "debugging", "troubleshooting", "scalability",
    "performance optimization",
    # ── Education ─────────────────────────────────────────────────────────
    "bachelor", "bachelor's degree", "computer science",
    "electrical engineering", "software engineering",
    # ── Short tokens ──────────────────────────────────────────────────────
    "ui", "ux", "api", "sdk", "redux",
]

_DICT_SORTED: List[str] = sorted(
    {s.strip().lower() for s in _RAW_SKILLS}, key=len, reverse=True
)

_STOPWORDS: Set[str] = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "used", "using", "including", "via",
    "into", "as", "if", "that", "this", "these", "those", "it", "its",
    "years", "year", "months", "experience", "knowledge", "skills",
    "skill", "ability", "proficiency", "strong", "excellent", "good",
    "great", "proven", "demonstrated", "required", "preferred",
    "senior", "junior",
}

_GEO_SKIP: Set[str] = {
    "NY", "CA", "US", "UK", "EU", "SF", "LA", "DC",
    "OK", "OR", "FL", "TX", "PA", "OH", "IL", "WA",
}


# ══════════════════════════════════════════════════════════════════════════════
# NORMALISATION
# ══════════════════════════════════════════════════════════════════════════════
def _norm(text: str) -> str:
    """Lowercase, strip, collapse spaces around punctuation."""
    text = re.sub(r"\s+", " ", text.lower().strip())
    text = re.sub(r"\s*([/\-+#.])\s*", r"\1", text)
    return text


def _norm_dedup(s: str) -> str:
    """For dedup bucketing: collapse hyphens and spaces."""
    return re.sub(r"[-\s]", "", s.lower())


def _tokenize(s: str) -> Set[str]:
    """
    Split a skill phrase into tokens with normalisation:
    - strip possessive "'s"
    - treat hyphens as spaces
    - lowercase
    """
    s = re.sub(r"'s\b", "", s.lower())
    s = re.sub(r"['\"`]", "", s)
    s = re.sub(r"[-]", " ", s)
    return set(s.split())


# ══════════════════════════════════════════════════════════════════════════════
# SKILL EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════
def extract_skills(text: str) -> List[str]:
    """
    Extract skill phrases from raw text using 5 complementary passes.

    Pass 1 — Dictionary scan  (longest match wins, word-boundary aware)
    Pass 2 — ALL-CAPS acronyms (CSS, HTML, REST, API, PLC, CAN)
    Pass 3 — CamelCase tokens  (React, GraphQL, MongoDB, VectorCAST)
    Pass 4 — Digit-embedded    (OAuth2, ES6, HTML5, MC-DC)
    Pass 5 — Slash tokens      (ci/cd, a/b, i/o)

    Returns sorted, deduplicated list of lowercase skill strings.
    """
    found: Set[str] = set()
    text_lower = _norm(text)

    # Pass 1: dictionary (longest first, word-boundary aware)
    for skill in _DICT_SORTED:
        pat = r"(?<![a-z0-9])" + re.escape(skill) + r"(?![a-z0-9])"
        if re.search(pat, text_lower):
            found.add(skill)

    # Pass 2: ALL-CAPS acronyms 2-8 chars
    for m in re.finditer(r"\b([A-Z][A-Z0-9]{1,7})\b", text):
        tok = m.group(1)
        if not tok.isdigit() and tok not in _GEO_SKIP:
            found.add(tok.lower())

    # Pass 3: CamelCase tokens
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b", text):
        tok = m.group(1).lower()
        if tok not in _STOPWORDS and len(tok) >= 4:
            found.add(tok)

    # Pass 4: digit-embedded tokens
    for m in re.finditer(r"\b([a-zA-Z]+[0-9]+[a-zA-Z0-9]*)\b", text):
        tok = m.group(1).lower()
        if 2 <= len(tok) <= 10:
            found.add(tok)

    # Pass 5: slash tokens
    for m in re.finditer(r"\b([a-zA-Z0-9]{1,8}/[a-zA-Z0-9]{1,8})\b", text):
        tok = m.group(1).lower()
        if 3 <= len(tok) <= 12:
            found.add(tok)

    # ── Cleanup ───────────────────────────────────────────────────────────
    cleaned: Set[str] = set()
    for s in found:
        if len(s) < 2:
            continue
        if len(s.split()) == 1 and s in _STOPWORDS:
            continue
        cleaned.add(s)

    # ── Hyphen/space dedup: "frontend" and "front-end" → keep longest ─────
    by_key: Dict[str, str] = {}
    for s in sorted(cleaned, key=len, reverse=True):
        key = _norm_dedup(s)
        if key not in by_key:
            by_key[key] = s
    deduped: Set[str] = set(by_key.values())

    # ── Substring dedup: drop if a longer skill already covers it ─────────
    result: Set[str] = set()
    for s in sorted(deduped, key=len, reverse=True):
        if not any(s in longer and s != longer for longer in result):
            result.add(s)

    return sorted(result)


# ══════════════════════════════════════════════════════════════════════════════
# SIMILARITY HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def _ngrams(text: str, n: int = 3) -> Counter:
    padded = f" {text} "
    return Counter(padded[i:i + n] for i in range(len(padded) - n + 1))


def _cosine(a: str, b: str) -> float:
    """Character trigram cosine similarity."""
    va, vb = _ngrams(a), _ngrams(b)
    keys = set(va) | set(vb)
    dot = sum(va[k] * vb[k] for k in keys)
    ma = math.sqrt(sum(v * v for v in va.values()))
    mb = math.sqrt(sum(v * v for v in vb.values()))
    return (dot / (ma * mb)) if ma and mb else 0.0


def _token_overlap(a: str, b: str) -> float:
    """
    Fraction of shorter skill's tokens found in the longer skill.

    FIXED (Bug 1): old formula used (ta | tb) which always returns 1.0
    for single-word inputs because shorter ⊆ (ta ∪ tb) by definition.
    Correct formula: intersect shorter with the OTHER (longer) set only.

    FIXED (Bug 2): tokeniser strips possessive "'s" and hyphens so that
    "bachelor's degree" matches "bachelor" and "problem-solving" matches
    "problem solving".
    """
    ta = _tokenize(a)
    tb = _tokenize(b)
    if abs(len(ta) - len(tb)) > 2:
        return 0.0
    shorter = ta if len(ta) <= len(tb) else tb
    longer  = tb if len(ta) <= len(tb) else ta
    if not shorter:
        return 0.0
    return len(shorter & longer) / len(shorter)   # ← FIXED


def _extract_initials(phrase: str) -> str:
    """'programmable logic controller' → 'plc'"""
    stop = {"the", "a", "an", "and", "or", "for", "to", "at", "of"}
    words = _norm(phrase).split()
    filtered = [w for w in words if w not in stop] or words
    return "".join(w[0] for w in filtered if w and w[0].isalpha())


def _is_abbreviation(token: str) -> bool:
    """
    FIXED (Bug 4): old code flagged every 2-4 letter lowercase word.
    Only ALL-CAPS tokens and tokens with digits/special chars qualify.
    """
    if re.match(r"^[A-Z]{2,8}$", token):
        return True
    if re.search(r"[0-9+#/.]", token):
        return True
    return False


def _abbreviation_match(jd: str, res: str) -> bool:
    """True if one is an abbreviation/initialism of the other."""
    j, r = _norm(jd), _norm(res)
    if j == r:
        return True
    clean_j = re.sub(r"[^a-z]", "", j)
    clean_r = re.sub(r"[^a-z]", "", r)
    if _is_abbreviation(jd) and _extract_initials(r) == clean_j:
        return True
    if _is_abbreviation(res) and _extract_initials(j) == clean_r:
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# MATCHING ENGINE
# ══════════════════════════════════════════════════════════════════════════════
OVERLAP_THRESHOLD: float = 0.80
COSINE_THRESHOLD:  float = 0.75

def _stem5(word: str) -> str:
    return re.sub(r"(tion|sion|ment|ness|ity|ing|ics|ies|ion|ed|er|al|ic|ive|ous)$", "", word.lower())[:5]


def classify_skills(
    jd_skills: List[str],
    resume_skills: List[str],
    resume_text: str = ""
) -> Tuple[List[str], List[str], Dict[str, dict]]:
    """
    4-pass matching per JD skill:
      Pass 1 — exact string match
      Pass 2 — token overlap ≥ 0.80  (possessives + hyphens normalised)
      Pass 3 — character trigram cosine similarity ≥ 0.75
      Pass 4 — abbreviation / initialism  (PLC ↔ programmable logic controller)

    Returns (matched, missing, details_dict).
    """
    if not resume_skills and not resume_text:
        return [], list(jd_skills), {}

    res_lower     = [s.lower().strip() for s in resume_skills]
    res_lower_set = set(res_lower)
    matched, missing, details = [], [], {}
    
    resume_text_lower = resume_text.lower() if resume_text else ""
    # Transform (stem) to catch e.g. "microcontrollers" vs "microcontroller"
    stem_map = {}
    if resume_text_lower:
        words = re.findall(r'[a-z]+', resume_text_lower)
        for w in words:
            if len(w) > 4:
                stem_map[_stem5(w)] = w

    for jd_skill in jd_skills:
        jd_lower = jd_skill.lower().strip()
        
        # —— Pass 0: Exact Literal Text & Transformed Literal Text ——
        hit_exact = False
        if resume_text_lower and jd_lower in resume_text_lower:
            hit_exact = True
            
        if not hit_exact and resume_text_lower and " " not in jd_lower and len(jd_lower) > 4:
            jd_stem = _stem5(jd_lower)
            if jd_stem in stem_map:
                hit_exact = True

        if hit_exact:
            matched.append(jd_skill)
            details[jd_skill] = {"pass": 0, "matched_with": jd_skill + " [Text/Stem]"}
            continue

        # ── Pass 1: exact ─────────────────────────────────────────────────
        if jd_lower in res_lower_set:
            matched.append(jd_skill)
            details[jd_skill] = {"pass": 1, "matched_with": jd_skill}
            continue

        # ── Pass 2: token overlap ─────────────────────────────────────────
        best_ov, best_ov_m = 0.0, None
        for r in res_lower:
            ov = _token_overlap(jd_lower, r)
            if ov > best_ov:
                best_ov, best_ov_m = ov, r
        if best_ov >= OVERLAP_THRESHOLD:
            matched.append(jd_skill)
            details[jd_skill] = {"pass": 2, "matched_with": best_ov_m,
                                  "overlap": round(best_ov, 3)}
            continue

        # ── Pass 3: cosine similarity ─────────────────────────────────────
        best_cos, best_cos_m = 0.0, None
        for r in res_lower:
            c = _cosine(jd_lower, r)
            if c > best_cos:
                best_cos, best_cos_m = c, r
        if best_cos >= COSINE_THRESHOLD:
            matched.append(jd_skill)
            details[jd_skill] = {"pass": 3, "matched_with": best_cos_m,
                                  "cosine": round(best_cos, 3)}
            continue

        # ── Pass 4: abbreviation ──────────────────────────────────────────
        abbr_hit = next(
            (r for r in resume_skills if _abbreviation_match(jd_skill, r)),
            None,
        )
        if abbr_hit:
            matched.append(jd_skill)
            details[jd_skill] = {"pass": 4, "matched_with": abbr_hit}
            continue

        # ── Missing ───────────────────────────────────────────────────────
        missing.append(jd_skill)
        details[jd_skill] = {"pass": 0, "best_cosine": round(best_cos, 3),
                              "best_cosine_match": best_cos_m}

    return matched, missing, details


# ══════════════════════════════════════════════════════════════════════════════
# PDF PARSING
# ══════════════════════════════════════════════════════════════════════════════
def _pdf_to_text(source) -> str:
    """Accept file path (str) or raw PDF bytes. Returns extracted text."""
    import pdfplumber
    ctx = pdfplumber.open(
        io.BytesIO(source) if isinstance(source, bytes) else source
    )
    with ctx as pdf:
        pages = [p.extract_text() for p in pdf.pages if p.extract_text()]
    text = "\n".join(pages).strip()
    if len(text) < 50:
        raise ValueError(
            "Cannot extract text from PDF. "
            "Use a text-based (not scanned) PDF."
        )
    return text


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════
def analyze(resume_pdf, job_description: str, verbose: bool = True) -> dict:
    """
    Full skill gap analysis.

    Args:
        resume_pdf:      file path (str) OR raw PDF bytes
        job_description: full text of the job description
        verbose:         print formatted results to terminal (default True)

    Returns:
        {
          "jd_skills":     List[str],   skills found in JD
          "resume_skills": List[str],   skills found in resume
          "matched":       List[str],   JD skills present in resume
          "missing":       List[str],   JD skills absent from resume
          "match_score":   float,       matched / total * 100
          "details":       dict,        per-skill match info
        }
    """
    resume_text   = _pdf_to_text(resume_pdf)
    jd_skills     = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)

    if not jd_skills:
        raise ValueError("No skills found in the job description.")
    if not resume_skills:
        raise ValueError("No skills found in the resume.")

    matched, missing, details = classify_skills(jd_skills, resume_skills, resume_text)
    match_score = round(len(matched) / len(jd_skills) * 100, 1)

    result = {
        "jd_skills":     sorted(jd_skills),
        "resume_skills": sorted(resume_skills),
        "matched":       sorted(matched),
        "missing":       sorted(missing),
        "match_score":   match_score,
        "details":       details,
    }
    if verbose:
        _print_results(result)
    return result


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE.PY DROP-IN REPLACEMENTS
# ══════════════════════════════════════════════════════════════════════════════
# In pipeline.py, api_server.py and app.py replace:
#   from pipeline import run_analysis, extract_skills, classify_gaps
# with:
#   from skill_gap_analyzer import run_analysis, extract_skills, classify_gaps

def build_similarity_matrix(jd_skills, resume_skills):
    """Shim matching pipeline.py's call signature."""
    import numpy as np
    dummy = np.zeros((len(jd_skills), len(resume_skills)), dtype=np.float32)
    return dummy, None, None


def classify_gaps(jd_skills, resume_skills, sim_matrix=None):
    """Drop-in for pipeline.classify_gaps() — same return schema."""
    matched, missing, details = classify_skills(jd_skills, resume_skills)
    per_skill_scores = {
        skill: {
            "best_score": details[skill].get(
                "cosine", details[skill].get(
                    "overlap", 1.0 if details[skill].get("pass", 0) > 0 else 0.0
                )
            ),
            "best_match": details[skill].get("matched_with"),
            "pass":       details[skill].get("pass", 0),
        }
        for skill in details
    }
    return matched, missing, per_skill_scores


def run_analysis(resume_pdf_bytes: bytes, job_description: str) -> dict:
    """Drop-in for pipeline.run_analysis() — identical return schema."""
    import numpy as np
    result = analyze(resume_pdf_bytes, job_description, verbose=False)
    n, m = len(result["jd_skills"]), len(result["resume_skills"])
    return {
        "resume_text":      "",
        "jd_skills":        result["jd_skills"],
        "resume_skills":    result["resume_skills"],
        "matched_skills":   result["matched"],
        "missing_skills":   result["missing"],
        "match_score":      result["match_score"],
        "per_skill_scores": {
            skill: {
                "best_score": d.get("cosine", d.get("overlap",
                              1.0 if d.get("pass", 0) > 0 else 0.0)),
                "best_match": d.get("matched_with"),
                "pass":       d.get("pass", 0),
            }
            for skill, d in result["details"].items()
        },
        "sim_matrix": np.zeros((n, m), dtype=np.float32),
    }


# ══════════════════════════════════════════════════════════════════════════════
# FORMATTED TERMINAL OUTPUT
# ══════════════════════════════════════════════════════════════════════════════
def _print_results(r: dict) -> None:
    W     = 64
    score = r["match_score"]
    bar_n = int(score / 100 * 40)
    bar   = "█" * bar_n + "░" * (40 - bar_n)

    def row(s: str = "") -> str:
        return "║" + s.ljust(W) + "║"

    print()
    print("╔" + "═" * W + "╗")
    print(row("  SKILL GAP ANALYSIS — RESULTS".center(W)))
    print("╠" + "═" * W + "╣")
    print(row(f"  Match Score  :  {score:.1f}%  [{bar}]"))
    print(row(f"  JD Skills    :  {len(r['jd_skills'])}  skills in job description"))
    print(row(f"  Resume Skills:  {len(r['resume_skills'])}  skills in resume"))
    print(row(f"  Matched ✅   :  {len(r['matched'])}     |     Missing ❌  :  {len(r['missing'])}"))
    print("╠" + "═" * W + "╣")

    # ── MATCHED ───────────────────────────────────────────────────────────
    print(row("  ✅  MATCHED  (JD skills found in resume)"))
    print("║" + "─" * W + "║")
    if r["matched"]:
        for skill in sorted(r["matched"]):
            d    = r["details"].get(skill, {})
            p    = d.get("pass", 0)
            how  = {1: "exact", 2: "overlap", 3: "similar",
                    4: "abbreviation"}.get(p, "")
            mw   = d.get("matched_with", "")
            line = f"     ✓  {skill}"
            if mw and _norm(mw) != _norm(skill):
                line += f"  →  resume has '{mw}'"
            if how:
                line += f"  [{how}]"
            print(row(line))
    else:
        print(row("     (none)"))

    print("╠" + "═" * W + "╣")

    # ── MISSING ───────────────────────────────────────────────────────────
    print(row("  ❌  MISSING  (JD skills not found in resume)"))
    print("║" + "─" * W + "║")
    if r["missing"]:
        for skill in sorted(r["missing"]):
            print(row(f"     ✗  {skill}"))
    else:
        print(row("     🎉  All JD skills are present in the resume!"))

    print("╚" + "═" * W + "╝")
    print()


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT  —  built-in test case
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    PDF_PATH = "mnt/embedded-system-engineer - Template 14.pdf"

    JD = """
    Job Title: Frontend Developer

    Key Responsibilities:
    - Develop new user-facing features using HTML, CSS, and modern JavaScript
      frameworks (e.g., React, Vue, or Angular).
    - Translate UI/UX design wireframes into high-quality, interactive code.
    - Optimize applications for maximum speed, scalability, and responsiveness.
    - Collaborate with backend developers to integrate user-facing elements.
    - Debug and troubleshoot front-end issues, including cross-browser compatibility.

    Required Skills & Qualifications:
    - Strong proficiency in HTML, CSS, JavaScript, and modern front-end frameworks
      (React, Angular, etc.).
    - Experience with responsive design, design systems, and mobile-first development.
    - Familiarity with version control systems (Git).
    - Excellent problem-solving skills and attention to detail.
    - Bachelor's degree in Computer Science or equivalent experience.
    """

    analyze(PDF_PATH, JD, verbose=True)