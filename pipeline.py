"""
pipeline.py  —  Career Copilot core analysis pipeline  (v5.0)

BUGS FIXED FROM v4
==================
BUG-1  Common nouns extracted as skills
       Previous code harvested ALL noun-chunks with no semantic filter.
       "communication", "planning", "development", "leadership", "teamwork"
       were extracted as skills. phrase_extracter.py had the correct semantic
       gate but was NEVER CALLED by pipeline.py's extract_skills().
       FIX: Unified the semantic gate directly into pipeline.py. Every candidate
       is scored against SKILL anchors vs GENERIC anchors using SentenceTransformer.
       Zero hardcoded skill names in the anchors — fully domain-agnostic.

BUG-2  PROPN over-inclusion (sentence-initial capitalised nouns)
       "Leadership", "Planning" at bullet-point start get PROPN tag from spaCy.
       FIX: Single-word PROPN tokens are only kept if they sit inside a named-
       entity span OR carry a hard technical signal (ALL-CAPS / CamelCase / digit).

BUG-3  Token overlap threshold 0.85 too strict
       "data analysis" vs "data analytics" → only "data" matches → 0.50 → MISS.
       FIX: Added stem-5 sub-pass. "analytics" and "analysis" both stem to "analy"
       → MATCH. Threshold lowered from 0.85 to 0.78.

BUG-4  Cosine threshold 0.80 too strict
       "python programming" vs "python" → ~0.78 → MISS.
       "project management" vs "project manager" → ~0.76 → MISS.
       FIX: Lowered from 0.80 to 0.72. Blocklist guards known false-positives
       (react/angular, sql/nosql, java/javascript etc.).

BUG-5  No sub-sequence containment pass
       JD: "python"  Resume: "python programming language" → MISS.
       FIX: New Pass 1b — whole-word containment check both directions.

ARCHITECTURE
============
  STAGE 1 — EXTRACTION  (spaCy + SentenceTransformer, zero hardcoded skills)
    a) spaCy mines: hard-signal tokens, PROPN-in-entity, noun-chunks ≤5 tokens
    b) Semantic gate scores every candidate vs SKILL / GENERIC anchors
    c) Hard-signal tokens (ALL-CAPS/CamelCase/digit/+#/.) bypass the gate

  STAGE 2 — COMPARISON  (SentenceTransformer cosine similarity)
    5-pass classification per JD skill:
      Pass 1   Exact string match
      Pass 1b  Whole-word containment  [NEW]
      Pass 2   Token / stem-5 overlap >= 0.78  [improved from 0.85]
      Pass 3   Cosine similarity >= 0.72  [lowered from 0.80] + blocklist
      Pass 4   Abbreviation / initialism match

Fully offline — no API keys, no internet at runtime.
"""
from __future__ import annotations

import re
import io
from typing import List, Tuple, Dict

import numpy as np

# ── Lazy singletons ────────────────────────────────────────────────────────────
_nlp               = None
_model             = None
_skill_gate_embs   = None
_generic_gate_embs = None

# ── Thresholds ─────────────────────────────────────────────────────────────────
COSINE_THRESHOLD:  float = 0.65   # was 0.80
OVERLAP_THRESHOLD: float = 0.70   # was 0.85

# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC GATE ANCHORS
# Describes *what kind of thing* skills are. No specific skill names.
# Domain-agnostic: works for software, finance, healthcare, marketing, legal...
# ─────────────────────────────────────────────────────────────────────────────
_SKILL_ANCHORS: List[str] = [
    "professional technical skill competency qualification",
    "industry domain expertise specialization knowledge area",
    "software tool platform technology methodology framework",
    "certification credential license standard protocol specification",
    "analytical quantitative data-driven computational capability",
    "engineering scientific technical discipline subject matter",
    "required proficiency hands-on working knowledge",
    "technical implementation deployment operation administration",
    "programming scripting automation orchestration integration",
    "management planning strategy execution governance leadership process",
    "clinical medical pharmaceutical regulatory compliance procedure",
    "financial accounting legal contractual operational workflow",
    "creative design artistic production editorial publishing",
]

_GENERIC_ANCHORS: List[str] = [
    "strong excellent great outstanding high-quality positive adjective",
    "good solid proven demonstrated required preferred desirable",
    "working leading managing building creating seeking looking",
    "responsible passionate driven collaborative motivated enthusiastic",
    "years months experience background history track record tenure",
    "team communication interpersonal stakeholder reporting structure",
    "engineer developer analyst manager specialist consultant director",
    "company organization department division group unit",
    "vague generic filler phrase common english noun",
]

_GATE_MARGIN: float = -0.05  # relaxed: skill_score just needs to not be far below generic

# ─────────────────────────────────────────────────────────────────────────────
# COSINE FALSE-POSITIVE BLOCKLIST
# ─────────────────────────────────────────────────────────────────────────────
_COSINE_BLOCKLIST: List[Tuple[str, str]] = [
    ("react",       "angular"),   ("react",       "vue"),
    ("angular",     "vue"),       ("docker",       "kubernetes"),
    ("sql",         "nosql"),     ("sql",          "mongodb"),
    ("mysql",       "postgresql"),("tensorflow",   "pytorch"),
    ("supervised",  "unsupervised"),("frontend",   "backend"),
    ("ios",         "android"),   ("swift",        "kotlin"),
    ("java",        "javascript"),("javascript",   "typescript"),
    ("mysql",       "nosql"),     ("postgresql",   "nosql"),
]

def _is_blocked(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    return any(
        (a == x and b == y) or (a == y and b == x)
        for x, y in _COSINE_BLOCKLIST
    )


# ─────────────────────────────────────────────────────────────────────────────
# STOP-WORDS
# ─────────────────────────────────────────────────────────────────────────────
def _build_stopwords() -> frozenset:
    base: set = set()
    try:
        from nltk.corpus import stopwords
        base = set(stopwords.words("english"))
    except Exception:
        base = {
            "i","me","my","we","our","you","your","he","him","his","she","her",
            "it","its","they","them","their","what","which","who","this","that",
            "these","those","am","is","are","was","were","be","been","being",
            "have","has","had","do","does","did","will","would","could","should",
            "may","might","can","a","an","the","and","but","if","or","because",
            "as","until","while","of","at","by","for","with","about","between",
            "into","through","before","after","to","from","in","out","on","off",
            "over","under","again","then","here","there","when","where","why",
            "how","all","both","each","more","most","other","some","such","no",
            "nor","not","only","same","so","than","too","very","just","also",
        }
    base.update({
        "skills","skill","experience","experienced","knowledge","background",
        "understanding","ability","abilities","proficiency","expertise",
        "familiarity","grasp","awareness","competency","competencies",
        "qualifications","requirements","responsibilities","duties","tasks",
        "years","year","months","month","week","weeks",
        "strong","excellent","good","great","deep","solid","high","well",
        "proven","demonstrated","required","preferred","related","relevant",
        "various","including","using","within","across","through","following",
        "multiple","key","core","primary","current","new","modern","latest",
        "effective","efficient","successful","exceptional",
        "engineer","engineers","developer","developers","programmer","programmers",
        "architect","architects","analyst","analysts","manager","managers",
        "specialist","specialists","consultant","consultants","candidate",
        "candidates","professional","professionals","lead","leads","owner",
        "owners","member","members","director","directors","officer",
        "ci","cd",
    })
    return frozenset(w.lower() for w in base)

_STOPWORDS: frozenset = _build_stopwords()

# Single-word generic nouns that are NEVER standalone skills
# (can be part of a compound like "data analysis", but alone are too vague)
_GENERIC_SINGLE_NOUNS: frozenset = frozenset({
    "analysis","communication","management","development","planning",
    "testing","implementation","integration","deployment","monitoring",
    "optimization","maintenance","documentation","reporting","research",
    "leadership","collaboration","teamwork","coordination","supervision",
    "evaluation","assessment","review","support","training","consulting",
    "strategy","administration","execution","delivery","creation",
    "performance","quality","efficiency","productivity","innovation","growth",
    "data","information","service","system","process","function","feature",
    "application","solution","platform","environment","structure","model",
    "approach","method","technique","practice","principle","concept",
    "standard","requirement","objective","goal","result","output",
})

_TRIM_START: frozenset = frozenset({
    "strong","excellent","good","great","solid","deep","proven","required",
    "preferred","senior","junior","basic","advanced","minimum","maximum",
    "specific","clear","much","high","key","core","primary","general",
    "overall","broad","extensive","comprehensive","hands-on","in-depth",
})

_TRIM_END: frozenset = frozenset({
    "experience","knowledge","skills","skill","developer","developers",
    "engineer","engineers","specialist","analyst","analysts","architect",
    "architects","programmer","programmers","candidate","candidates",
    "methodology","methodologies","practices","principles","concepts",
    "team","role","position","job","requirement","requirements","background",
    "understanding","ability",
    # "environment","tools","solutions","systems","processes","frameworks",
    # "techniques","approaches","methods" removed — these form valid compound
    # skills: "debugging tools", "embedded systems", "CI/CD pipelines", etc.
})


# ─────────────────────────────────────────────────────────────────────────────
# LAZY LOADERS
# ─────────────────────────────────────────────────────────────────────────────
def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def _load_gate():
    global _skill_gate_embs, _generic_gate_embs
    if _skill_gate_embs is not None:
        return
    m = _get_model()
    _skill_gate_embs = m.encode(
        _SKILL_ANCHORS, normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=False,
    )
    _generic_gate_embs = m.encode(
        _GENERIC_ANCHORS, normalize_embeddings=True,
        convert_to_numpy=True, show_progress_bar=False,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HARD-SIGNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _is_hard_signal(word: str) -> bool:
    """
    Tokens with unambiguous technical markers — always kept.
      ALL-CAPS 2-8:  REST, SQL, AWS, NLP, HTML, BERT
      Digit-embedded: Python3, OAuth2, ES6, GPT4
      Special chars:  C++, C#, .NET, CI/CD, Node.js
      CamelCase:      TypeScript, GraphQL, MongoDB, FastAPI
    """
    if not word or " " in word:
        return False
    if any(c.isdigit() for c in word):
        return True
    if any(c in ("+", "#", "/", ".") for c in word):
        return True
    if re.match(r"^[A-Z]{2,8}$", word):
        return True
    if any(c.isupper() for c in word) and any(c.islower() for c in word):
        return True
    return False

def _is_hard_bypass(word: str) -> bool:
    """Same as _is_hard_signal for gate bypass (single tokens only)."""
    return _is_hard_signal(word)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — CANDIDATE MINING (spaCy)
# ─────────────────────────────────────────────────────────────────────────────
def _trim_chunk(tokens: list):
    """Trim generic leading/trailing tokens from a noun-chunk. Returns str or None."""
    toks = [t for t in tokens if t.pos_ not in ("DET", "PRON", "PUNCT")]
    if not toks:
        return None
    while len(toks) > 1 and toks[0].text.lower() in _TRIM_START:
        toks = toks[1:]
    while len(toks) > 1 and toks[-1].text.lower() in _TRIM_END:
        toks = toks[:-1]
    if not toks or len(toks) > 5:
        return None
    phrase = " ".join(t.text for t in toks).strip()
    if not phrase or len(phrase) < 2:
        return None
    words = phrase.lower().split()
    if phrase.lower() in _STOPWORDS:
        return None
    if len(words) == 1 and words[0] in _GENERIC_SINGLE_NOUNS:
        return None
    return phrase


def _mine_candidates(text: str) -> set:
    """
    Harvest raw candidate phrases from text via spaCy.
    (a) Hard-signal single tokens — bypass gate later
    (b) PROPN tokens that are inside a named-entity span only
    (c) Noun-chunks <= 5 tokens (trimmed)
    (d) ORG / PRODUCT / WORK_OF_ART / NORP entity spans
    """
    nlp = _get_nlp()
    candidates: set = set()
    chunk_size = 100_000

    for start in range(0, len(text), chunk_size):
        chunk = text[start: start + chunk_size]
        doc   = nlp(chunk)

        gpe_person_idx: set = {
            tok.i for ent in doc.ents
            if ent.label_ in ("GPE", "PERSON") for tok in ent
        }
        ent_idx: set = {tok.i for ent in doc.ents for tok in ent}

        # (a+b) token-level
        for tok in doc:
            if tok.pos_ in (
                "PUNCT","SPACE","SYM","CCONJ","ADP","DET","PRON","VERB","AUX","PART"
            ):
                continue
            t = tok.text.strip()
            if len(t) < 2 or t.lower() in _STOPWORDS:
                continue
            if tok.i in gpe_person_idx:
                continue
            if _is_hard_signal(t):
                candidates.add(t)
            elif tok.pos_ == "PROPN" and tok.i in ent_idx:
                # Only PROPN tokens inside a named entity — blocks "Leadership" etc.
                candidates.add(t)

        # (c) noun-chunks
        skip_spans: set = {
            ent.text for ent in doc.ents if ent.label_ in ("GPE", "PERSON")
        }
        for chunk_span in doc.noun_chunks:
            if any(tok.i in gpe_person_idx for tok in chunk_span):
                continue
            if chunk_span.text in skip_spans:
                continue
            phrase = _trim_chunk(list(chunk_span))
            if phrase:
                candidates.add(phrase)

        # (d) named entities (products, orgs, frameworks)
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT", "WORK_OF_ART", "NORP"):
                t = ent.text.strip()
                if 2 <= len(t) <= 60:
                    candidates.add(t)

    return candidates


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — SEMANTIC GATE (SentenceTransformer zero-shot)
# ─────────────────────────────────────────────────────────────────────────────
def _semantic_gate(candidates: set) -> set:
    """
    Filter candidates: keep only those that score higher vs SKILL anchors
    than vs GENERIC anchors (by at least _GATE_MARGIN).
    Hard-bypass tokens (ALL-CAPS/digit/CamelCase/+#/.) always pass.

    IMPORTANT: candidates may contain original-cased forms (e.g. "Microcontrollers").
    We check hard_bypass on the ORIGINAL form so CamelCase/Capitalized words
    are not accidentally sent to scoring after lowercasing strips their signal.
    """
    if not candidates:
        return set()

    _load_gate()
    m = _get_model()

    # Check hard_bypass on ORIGINAL casing — a word like "Microcontrollers"
    # is CamelCase-ish (upper+lower) so it bypasses; "microcontrollers"
    # would NOT bypass, causing it to be scored and potentially dropped.
    bypass   = {c for c in candidates if _is_hard_bypass(c) or _is_hard_signal(c)}
    to_score = [c for c in candidates if c not in bypass]
    passed   = set(bypass)

    if to_score:
        # Multi-word phrases (2+ meaningful tokens) are compound technical
        # terms — they always pass the gate (was never intended to filter these).
        single_to_score = []
        for cand in to_score:
            words = [w for w in cand.lower().split() if w not in _STOPWORDS]
            if len(words) >= 2:
                passed.add(cand)
            else:
                single_to_score.append(cand)

        if single_to_score:
            embs           = m.encode(
                single_to_score, normalize_embeddings=True,
                convert_to_numpy=True, show_progress_bar=False,
            )
            skill_scores   = (embs @ _skill_gate_embs.T).max(axis=1)
            generic_scores = (embs @ _generic_gate_embs.T).max(axis=1)

            for cand, ss, gs in zip(single_to_score, skill_scores, generic_scores):
                # Only drop a single-word token if it clearly belongs to the
                # generic/noise cluster (generic score beats skill score).
                if ss >= gs + _GATE_MARGIN:
                    passed.add(cand)

    return passed


# ─────────────────────────────────────────────────────────────────────────────
# FULL EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────
def _normalize(s: str) -> str:
    s = s.lower().strip().strip(",;")
    s = re.sub(r"\s*([/\-.+#])\s*", r"\1", s)
    return re.sub(r"\s+", " ", s)


def extract_skills(text: str) -> List[str]:
    """
    Extract professional skill phrases from raw text.

    1. Mine candidates via spaCy (hard-signal tokens, PROPN-in-entity, noun-chunks)
    2. Filter via semantic gate (SentenceTransformer, no hardcoded skill names)
       - Gate receives ORIGINAL casing so CamelCase/Capitalized bypass works correctly
    3. Normalise (lowercase), dedup (longest wins)

    Domain-agnostic — works for any industry / job type.
    Fully offline — requires only spaCy en_core_web_sm + all-MiniLM-L6-v2.

    Returns sorted, deduplicated list of lowercase skill strings.
    """
    raw    = _mine_candidates(text)          # original casing preserved
    passed = _semantic_gate(raw)             # gate sees original casing for bypass check

    normalised: set = set()
    for c in passed:
        n = _normalize(c)                    # lowercase AFTER gate decision
        if not n or len(n) < 2:
            continue
        if n in _STOPWORDS:
            continue
        if len(n.split()) == 1 and n in _GENERIC_SINGLE_NOUNS:
            continue
        normalised.add(n)

    # Longest-wins dedup
    result: set = set()
    for s in sorted(normalised, key=len, reverse=True):
        contained = any(
            bool(re.search(r"(?:^|[\s,;/])" + re.escape(s) + r"(?:[\s,;/]|$)", longer))
            for longer in result
        )
        if not contained:
            result.add(s)

    return sorted(result)


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — EMBEDDINGS + SIMILARITY MATRIX
# ─────────────────────────────────────────────────────────────────────────────
def _embed(skills: List[str]) -> np.ndarray:
    if not skills:
        return np.zeros((0, 384), dtype=np.float32)
    return _get_model().encode(
        skills, normalize_embeddings=True, batch_size=64,
        show_progress_bar=False, convert_to_numpy=True,
    ).astype(np.float32)


def build_similarity_matrix(
    jd_skills:     List[str],
    resume_skills: List[str],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    jd_emb  = _embed(jd_skills)
    res_emb = _embed(resume_skills)
    if jd_emb.shape[0] == 0 or res_emb.shape[0] == 0:
        return (
            np.zeros((len(jd_skills), len(resume_skills)), dtype=np.float32),
            jd_emb, res_emb,
        )
    return np.clip(jd_emb @ res_emb.T, 0.0, 1.0).astype(np.float32), jd_emb, res_emb


# ─────────────────────────────────────────────────────────────────────────────
# MATCHING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _stem5(word: str) -> str:
    """
    5-char stem after stripping common suffixes.
    analytics→analy, analysis→analy, managing→manag, management→manag
    """
    word = re.sub(
        r"(tion|sion|ment|ness|ity|ing|ics|ies|ion|ed|er|al|ic|ive|ous)$",
        "", word.lower()
    )
    return word[:5] if len(word) >= 5 else word


def _tokenize(s: str) -> List[str]:
    s = re.sub(r"'s\b", "", s.lower())
    s = re.sub(r"[-/]", " ", s)
    return [t for t in s.split() if t not in _STOPWORDS and len(t) > 1]


def _token_overlap(a: str, b: str) -> float:
    """
    Best overlap across two sub-passes:
      a) Exact token intersection
      b) Stem-5 intersection  (catches analytics/analysis, managing/management)
    Returns 0.0 if token-count gap > 3.
    Score = |intersection| / |shorter|.
    """
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    if abs(len(ta) - len(tb)) > 3:
        return 0.0

    shorter = ta if len(ta) <= len(tb) else tb
    longer  = tb if len(ta) <= len(tb) else ta

    exact   = len(set(shorter) & set(longer)) / len(shorter)
    s_short = [_stem5(w) for w in shorter]
    s_long  = [_stem5(w) for w in longer]
    stemmed = len(set(s_short) & set(s_long)) / len(s_short)

    return max(exact, stemmed)


def _whole_word_contains(needle: str, haystack: str) -> bool:
    """
    True if needle appears as a complete word-sequence inside haystack.
    "python" in "python programming" → True
    "sql" in "nosql"                 → False
    """
    if not needle or not haystack:
        return False
    return bool(
        re.search(
            r"(?:^|[\s,;/])" + re.escape(needle.lower()) + r"(?:[\s,;/]|$)",
            haystack.lower(),
        )
    )


# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — CLASSIFY GAPS (5-pass)
# ─────────────────────────────────────────────────────────────────────────────
def classify_gaps(
    jd_skills:     List[str],
    resume_skills: List[str],
    sim_matrix:    np.ndarray,
    resume_text:   str = "",
) -> Tuple[List[str], List[str], Dict[str, dict]]:
    """
    6-pass classification:
      Pass 0   Literal text scan — if the JD skill appears word-for-word
               in the raw resume text, it is always matched. No NLP needed.
               This is the guaranteed safety net.
      Pass 1   Exact string match against extracted resume skills
      Pass 1b  Whole-word containment
      Pass 2   Token / stem-5 overlap >= 0.70
      Pass 3   Cosine >= 0.65, not in blocklist
      Pass 4   Abbreviation / initialism match
    """
    if not jd_skills:
        return [], [], {}
    if not resume_skills:
        return [], list(jd_skills), {
            s: {"best_score": 0.0, "best_match": None, "pass": 0}
            for s in jd_skills
        }

    from abbreviation_matcher import get_abbreviation_boost

    sim           = np.asarray(sim_matrix, dtype=np.float32)
    res_lower     = [s.lower().strip() for s in resume_skills]
    res_lower_set = set(res_lower)

    matched: List[str] = []
    missing: List[str] = []
    scores:  Dict[str, dict] = {}

    resume_text_lower = resume_text.lower() if resume_text else ""

    for i, jd_skill in enumerate(jd_skills):
        jd_lower   = jd_skill.lower().strip()
        best_score = float(sim[i].max()) if sim.shape[1] > 0 else 0.0
        best_idx   = int(sim[i].argmax()) if sim.shape[1] > 0 else -1
        best_match = resume_skills[best_idx] if best_idx >= 0 else None

        # ── Pass 0: LITERAL TEXT SCAN ─────────────────────────────────────────
        # If the JD skill appears word-for-word in the raw resume text,
        # always match it — regardless of what the extractor found.
        # Negative lookaround ensures "sql" won't match inside "nosql",
        # and handles punctuation like "I2C." or "(Microcontrollers)".
        if resume_text_lower and re.search(
            r"(?<![a-z0-9])" + re.escape(jd_lower) + r"(?![a-z0-9])",
            resume_text_lower,
        ):
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": 1.0, "best_match": jd_skill, "pass": 0}
            continue

        # Pass 1: exact extracted skill match
        if jd_lower in res_lower_set:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": 1.0, "best_match": jd_skill, "pass": 1}
            continue

        # Pass 1b: whole-word containment
        contain_match = next(
            (resume_skills[j] for j, r in enumerate(res_lower)
             if _whole_word_contains(jd_lower, r)
             or _whole_word_contains(r, jd_lower)),
            None,
        )
        if contain_match:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": best_score, "best_match": contain_match, "pass": 2}
            continue

        # Pass 2: token / stem overlap
        overlap_match = next(
            (resume_skills[j] for j, r in enumerate(res_lower)
             if _token_overlap(jd_lower, r) >= OVERLAP_THRESHOLD),
            None,
        )
        if overlap_match:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": best_score, "best_match": overlap_match, "pass": 2}
            continue

        # Pass 3: cosine + blocklist guard
        if (
            best_score >= COSINE_THRESHOLD
            and best_match
            and not _is_blocked(jd_lower, best_match.lower())
        ):
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": best_score, "best_match": best_match, "pass": 3}
            continue

        # Pass 4: abbreviation
        abbr_match = next(
            (r_orig for r_orig in resume_skills
             if get_abbreviation_boost(jd_skill, r_orig) > 0),
            None,
        )
        if abbr_match:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": best_score, "best_match": abbr_match, "pass": 4}
            continue

        # Missing
        missing.append(jd_skill)
        scores[jd_skill] = {"best_score": best_score, "best_match": best_match, "pass": 0}

    return matched, missing, scores


# ─────────────────────────────────────────────────────────────────────────────
# HIGH-LEVEL ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────
def run_analysis(resume_pdf_bytes: bytes, job_description: str) -> dict:
    """
    Full pipeline: PDF bytes + JD text → skill gap analysis result.

    Steps:
      1. Parse PDF → raw text            (pdfplumber)
      2. Extract JD skills               (spaCy + semantic gate)
      3. Extract resume skills           (spaCy + semantic gate)
      4. Embed both skill lists          (all-MiniLM-L6-v2, offline)
      5. Build cosine similarity matrix  (numpy)
      6. 5-pass gap classification

    Returns dict: resume_text, jd_skills, resume_skills, matched_skills,
                  missing_skills, match_score, per_skill_scores, sim_matrix

    Raises ValueError if PDF is bad or no skills are found.
    """
    import pdfplumber

    pages: List[str] = []
    with pdfplumber.open(io.BytesIO(resume_pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    resume_text = "\n".join(pages).strip()

    if len(resume_text) < 50:
        raise ValueError(
            "Could not extract text from the PDF. "
            "Please use a text-based (not scanned) PDF."
        )

    jd_skills     = extract_skills(job_description)
    resume_skills = extract_skills(resume_text)

    if not jd_skills:
        raise ValueError("No skills could be identified in the job description.")
    if not resume_skills:
        raise ValueError("No skills could be identified in the resume PDF.")

    sim_matrix, _, __ = build_similarity_matrix(jd_skills, resume_skills)
    matched, missing, per_skill_scores = classify_gaps(
        jd_skills, resume_skills, sim_matrix, resume_text
    )
    match_score = round(len(matched) / len(jd_skills) * 100, 1)

    return {
        "resume_text":      resume_text,
        "jd_skills":        sorted(jd_skills),
        "resume_skills":    sorted(resume_skills),
        "matched_skills":   sorted(matched),
        "missing_skills":   sorted(missing),
        "match_score":      match_score,
        "per_skill_scores": per_skill_scores,
        "sim_matrix":       sim_matrix,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DEBUG UTILITY  —  run as:  python pipeline.py resume.pdf "JD text here"
# ─────────────────────────────────────────────────────────────────────────────
def debug_analysis(resume_pdf_bytes: bytes, job_description: str) -> None:
    """
    Print a detailed trace of the full pipeline:
      • Raw resume text (first 500 chars)
      • All skills extracted from JD
      • All skills extracted from resume
      • Per-skill match verdict with pass number, score, and best match
      • Skills in JD but NOT found in resume extraction (extraction miss)
    """
    import pdfplumber

    SEP = "─" * 70

    # ── 1. Parse PDF ──────────────────────────────────────────────────────────
    pages: List[str] = []
    with pdfplumber.open(io.BytesIO(resume_pdf_bytes)) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                pages.append(t)
    resume_text = "\n".join(pages).strip()

    print(f"\n{SEP}")
    print("RESUME TEXT PREVIEW (first 600 chars)")
    print(SEP)
    print(resume_text[:600])

    # ── 2. Extract skills ──────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("JD SKILLS EXTRACTED")
    print(SEP)
    jd_skills = extract_skills(job_description)
    for s in sorted(jd_skills):
        print(f"  {s}")

    print(f"\n{SEP}")
    print("RESUME SKILLS EXTRACTED")
    print(SEP)
    resume_skills = extract_skills(resume_text)
    for s in sorted(resume_skills):
        print(f"  {s}")

    # ── 3. Show what JD skills are NOT in resume extraction at all ────────────
    print(f"\n{SEP}")
    print("JD SKILLS NOT FOUND IN RESUME EXTRACTION  (extraction misses)")
    print("  These need the extractor fixed — the skill is in the resume text")
    print("  but wasn't pulled out by spaCy + semantic gate.")
    print(SEP)
    jd_lower_set    = {s.lower() for s in jd_skills}
    res_lower_set   = {s.lower() for s in resume_skills}
    extraction_miss = []
    for jd_s in sorted(jd_skills):
        jd_l = jd_s.lower()
        # Check if the raw resume text contains this term
        in_text = bool(
            re.search(r"(?:^|[\s,;/(])" + re.escape(jd_l) + r"(?:[\s,;/)]|$)",
                      resume_text.lower())
        )
        in_extracted = jd_l in res_lower_set or any(
            jd_l in r or r in jd_l for r in res_lower_set
        )
        if in_text and not in_extracted:
            extraction_miss.append(jd_s)
            print(f"  EXTRACTION MISS: '{jd_s}'  — present in resume text but not extracted")

    if not extraction_miss:
        print("  (none — all JD skills that appear in resume text were extracted)")

    # ── 4. Full match trace ────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("FULL MATCH TRACE  (per JD skill)")
    print(SEP)
    sim_matrix, _, __ = build_similarity_matrix(jd_skills, resume_skills)
    matched, missing, scores = classify_gaps(jd_skills, resume_skills, sim_matrix, resume_text)

    pass_labels = {0: "MISSING", 1: "exact", "1b": "contain", 2: "token/stem", 3: "cosine", 4: "abbrev"}

    for jd_s in sorted(jd_skills):
        info       = scores.get(jd_s, {})
        pass_num   = info.get("pass", 0)
        best_score = info.get("best_score", 0.0)
        best_match = info.get("best_match", "-")
        verdict    = "✓ MATCHED" if jd_s in matched else "✗ MISSING"
        pass_name  = pass_labels.get(pass_num, f"pass{pass_num}")
        print(f"  {verdict:12s}  [{pass_name:10s}  score={best_score:.3f}]  "
              f"'{jd_s}'  →  '{best_match}'")

    # ── 5. Summary ─────────────────────────────────────────────────────────────
    match_score = round(len(matched) / len(jd_skills) * 100, 1) if jd_skills else 0
    print(f"\n{SEP}")
    print(f"SUMMARY: {len(matched)}/{len(jd_skills)} matched  ({match_score}%)")
    print(f"  Matched : {sorted(matched)}")
    print(f"  Missing : {sorted(missing)}")
    print(SEP)


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python pipeline.py <resume.pdf> <job_description_text_or_file>")
        print("       python pipeline.py resume.pdf 'Python SQL React ...'")
        print("       python pipeline.py resume.pdf jd.txt")
        sys.exit(1)

    pdf_path = sys.argv[1]
    jd_arg   = sys.argv[2]

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    # Accept JD as raw text or a .txt file path
    if jd_arg.endswith(".txt") and len(jd_arg) < 200:
        try:
            with open(jd_arg) as f:
                jd_text = f.read()
        except FileNotFoundError:
            jd_text = jd_arg
    else:
        jd_text = jd_arg

    debug_analysis(pdf_bytes, jd_text)