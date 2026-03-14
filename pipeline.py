"""
pipeline.py  —  Career Copilot core analysis pipeline  (v6.0)

CHANGES FROM v5.0
═════════════════
BUG-6  Implied skills marked as MISSING (the "Python problem")
       A Data Science JD requires "Python". The resume never writes "Python"
       but lists scikit-learn, TensorFlow, pandas — all Python libraries.
       The old system marked Python as MISSING. Same issue in reverse:
       JD asks "machine learning", resume has "scikit-learn + gradient
       boosting + cross-validation" — clearly ML, but flagged missing.

       FIX: New Pass 5 — ImplicationEngine (implication_engine.py)
         Pass A: resume skill's KB description ↔ JD skill phrase (cosine)
                 "scikit-learn" KB desc says "Python library" → Python implied
         Pass B: JD skill's KB description ↔ resume skill phrase (cosine)
                 "machine learning" KB desc mentions scikit-learn → implied
         Pass C: Sliding-window semantic scan of raw resume text
                 Catches implications buried in prose that extraction missed
       Zero hardcoding — fully driven by sentence-transformer embeddings
       and the existing knowledge base descriptions.

ARCHITECTURE
════════════
  STAGE 1 — EXTRACTION  (spaCy + SentenceTransformer, zero hardcoded skills)
    a) spaCy mines: hard-signal tokens, PROPN-in-entity, noun-chunks ≤5 tokens
    b) Semantic gate scores every candidate vs SKILL / GENERIC anchors
    c) Hard-signal tokens (ALL-CAPS/CamelCase/digit/+#/.) bypass the gate

  STAGE 2 — COMPARISON  (SentenceTransformer cosine similarity)
    7-pass classification per JD skill:
      Pass 0   Literal text scan
      Pass 1   Exact string match
      Pass 1b  Whole-word containment
      Pass 1c  KB description token overlap
      Pass 2   Token / stem-5 overlap >= 0.70
      Pass 3   Cosine similarity >= 0.65 + blocklist
      Pass 4   Abbreviation / initialism match
      Pass 5   Semantic implication (NEW — ImplicationEngine)  ← v6.0

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
COSINE_THRESHOLD:  float = 0.65
OVERLAP_THRESHOLD: float = 0.70

# ─────────────────────────────────────────────────────────────────────────────
# SEMANTIC GATE ANCHORS
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
_GATE_MARGIN: float = -0.05

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
    "strong","excellent","good","great","solid","proven","required",
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
})

# ─────────────────────────────────────────────────────────────────────────────
# LAZY LOADERS
# ─────────────────────────────────────────────────────────────────────────────
def _get_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            try:
                import en_core_web_sm
                _nlp = en_core_web_sm.load()
            except ImportError:
                try:
                    from spacy.cli import download
                    download("en_core_web_sm")
                    _nlp = spacy.load("en_core_web_sm")
                except Exception as exc:
                    raise RuntimeError(
                        "spaCy model 'en_core_web_sm' is required. "
                        "Install it with: python -m spacy download en_core_web_sm"
                    ) from exc
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
    return _is_hard_signal(word)

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — CANDIDATE MINING (spaCy)
# ─────────────────────────────────────────────────────────────────────────────
def _trim_chunk(tokens: list):
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
                candidates.add(t)
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
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT", "WORK_OF_ART", "NORP"):
                t = ent.text.strip()
                if 2 <= len(t) <= 60:
                    candidates.add(t)
    return candidates

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 1 — SEMANTIC GATE
# ─────────────────────────────────────────────────────────────────────────────
def _semantic_gate(candidates: set) -> set:
    if not candidates:
        return set()
    _load_gate()
    m = _get_model()
    bypass   = {c for c in candidates if _is_hard_bypass(c) or _is_hard_signal(c)}
    to_score = [c for c in candidates if c not in bypass]
    passed   = set(bypass)
    if to_score:
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
    raw    = _mine_candidates(text)
    passed = _semantic_gate(raw)
    normalised: set = set()
    for c in passed:
        n = _normalize(c)
        if not n or len(n) < 2:
            continue
        if n in _STOPWORDS:
            continue
        if len(n.split()) == 1 and n in _GENERIC_SINGLE_NOUNS:
            continue
        normalised.add(n)
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
    word = re.sub(
        r"(tion|sion|ment|ness|ity|ing|ics|ies|ion|ed|er|al|ic|ive|ous)$",
        "", word.lower()
    )
    return word[:5] if len(word) >= 5 else word

def _tokenize(s: str) -> List[str]:
    s = re.sub(r"'s\b", "", s.lower())
    s = re.sub(r"[-/]", " ", s)
    tokens = re.findall(r"[a-z0-9+#.]+", s)
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]

def _token_overlap(a: str, b: str) -> float:
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

def _phrase_coverage_in_text(phrase: str, text: str) -> float:
    phrase_tokens = _tokenize(phrase)
    text_tokens   = _tokenize(text)
    if not phrase_tokens or not text_tokens:
        return 0.0
    exact         = len(set(phrase_tokens) & set(text_tokens)) / len(phrase_tokens)
    phrase_stems  = {_stem5(token) for token in phrase_tokens}
    text_stems    = {_stem5(token) for token in text_tokens}
    stemmed       = len(phrase_stems & text_stems) / len(phrase_stems)
    return max(exact, stemmed)

def _whole_word_contains(needle: str, haystack: str) -> bool:
    if not needle or not haystack:
        return False
    return bool(
        re.search(
            r"(?:^|[\s,;/])" + re.escape(needle.lower()) + r"(?:[\s,;/]|$)",
            haystack.lower(),
        )
    )

def _knowledge_implied_match(jd_skill: str, resume_skills: List[str]) -> str | None:
    """
    Legacy token-overlap KB pass (Pass 1c).
    Kept for backward compatibility — Pass 5 (ImplicationEngine) supersedes
    this for semantic implication, but this still catches token-overlap cases.
    """
    jd_lower  = jd_skill.lower().strip()
    jd_tokens = _tokenize(jd_lower)
    if len(jd_tokens) < 2:
        return None
    from knowledge_base import get_skill_knowledge
    best_match = None
    best_score = 0.0
    for resume_skill in resume_skills:
        knowledge   = get_skill_knowledge(resume_skill)
        description = knowledge.get("description", "").lower().strip()
        if not description:
            continue
        overlap = _phrase_coverage_in_text(jd_lower, description)
        if overlap > best_score:
            best_score = overlap
            best_match = resume_skill
    return best_match if best_score >= 0.66 else None

# ─────────────────────────────────────────────────────────────────────────────
# STAGE 2 — CLASSIFY GAPS (7-pass)
# ─────────────────────────────────────────────────────────────────────────────
def classify_gaps(
    jd_skills:     List[str],
    resume_skills: List[str],
    sim_matrix:    np.ndarray,
    resume_text:   str = "",
) -> Tuple[List[str], List[str], Dict[str, dict]]:
    """
    7-pass classification:
      Pass 0   Literal text scan
      Pass 1   Exact string match
      Pass 1b  Whole-word containment
      Pass 1c  KB description token overlap
      Pass 2   Token / stem-5 overlap >= 0.70
      Pass 3   Cosine >= 0.65, not in blocklist
      Pass 4   Abbreviation / initialism match
      Pass 5   Semantic implication  [NEW v6.0]
                 A: resume skill KB desc ↔ JD skill phrase
                 B: JD skill KB desc ↔ resume skill phrase
                 C: Raw resume text sliding-window ↔ JD skill phrase
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

    # ── Passes 0-4 (first sweep) ─────────────────────────────────────────────
    # We collect truly unmatched skills into `candidates_for_implication`
    # so Pass 5 only runs on the residual set (efficiency).
    candidates_for_implication: List[str] = []

    for i, jd_skill in enumerate(jd_skills):
        jd_lower   = jd_skill.lower().strip()
        best_score = float(sim[i].max()) if sim.shape[1] > 0 else 0.0
        best_idx   = int(sim[i].argmax()) if sim.shape[1] > 0 else -1
        best_match = resume_skills[best_idx] if best_idx >= 0 else None

        # Pass 0: Literal text scan
        if resume_text_lower and re.search(
            r"(?<![a-z0-9])" + re.escape(jd_lower) + r"(?![a-z0-9])",
            resume_text_lower,
        ):
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": 1.0, "best_match": jd_skill, "pass": 0}
            continue

        # Pass 1: Exact match
        if jd_lower in res_lower_set:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": 1.0, "best_match": jd_skill, "pass": 1}
            continue

        # Pass 1b: Whole-word containment
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

        # Pass 1c: KB description token overlap
        knowledge_match = _knowledge_implied_match(jd_lower, resume_skills)
        if knowledge_match:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": 1.0, "best_match": knowledge_match, "pass": 2}
            continue

        # Pass 2: Token / stem overlap
        overlap_match = next(
            (resume_skills[j] for j, r in enumerate(res_lower)
             if _token_overlap(jd_lower, r) >= OVERLAP_THRESHOLD),
            None,
        )
        if overlap_match:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": best_score, "best_match": overlap_match, "pass": 2}
            continue

        # Pass 3: Cosine + blocklist
        if (
            best_score >= COSINE_THRESHOLD
            and best_match
            and not _is_blocked(jd_lower, best_match.lower())
        ):
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": best_score, "best_match": best_match, "pass": 3}
            continue

        # Pass 4: Abbreviation
        abbr_match = next(
            (r_orig for r_orig in resume_skills
             if get_abbreviation_boost(jd_skill, r_orig) > 0),
            None,
        )
        if abbr_match:
            matched.append(jd_skill)
            scores[jd_skill] = {"best_score": best_score, "best_match": abbr_match, "pass": 4}
            continue

        # Not yet matched → defer to Pass 5
        candidates_for_implication.append(jd_skill)

    # ── Pass 5: Semantic Implication (ImplicationEngine) ─────────────────────
    if candidates_for_implication:
        from implication_engine import ImplicationEngine

        engine  = ImplicationEngine(resume_text)
        implied = engine.find_implied_skills(
            jd_skills, resume_skills, candidates_for_implication
        )

        for jd_skill in candidates_for_implication:
            if jd_skill in implied:
                info       = implied[jd_skill]
                best_match = info.get("best_match") or jd_skill
                pass_label = info.get("pass", "implied")
                matched.append(jd_skill)
                scores[jd_skill] = {
                    "best_score": 0.85,        # Proxy score for implied match
                    "best_match": best_match,
                    "pass":       pass_label,
                }
            else:
                missing.append(jd_skill)
                best_idx   = jd_skills.index(jd_skill)
                best_score = float(sim[best_idx].max()) if sim.shape[1] > 0 else 0.0
                best_match_r = resume_skills[int(sim[best_idx].argmax())] if sim.shape[1] > 0 else None
                scores[jd_skill] = {
                    "best_score": best_score,
                    "best_match": best_match_r,
                    "pass": 0,
                }

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
      6. 7-pass gap classification       (incl. implication engine)
    Returns dict with: resume_text, jd_skills, resume_skills,
      matched_skills, missing_skills, match_score, per_skill_scores, sim_matrix
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
# DEBUG UTILITY
# ─────────────────────────────────────────────────────────────────────────────
def debug_analysis(resume_pdf_bytes: bytes, job_description: str) -> None:
    import pdfplumber
    SEP = "─" * 70

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

    print(f"\n{SEP}")
    print("JD SKILLS NOT FOUND IN RESUME EXTRACTION  (extraction misses)")
    print(SEP)
    res_lower_set = {s.lower() for s in resume_skills}
    for jd_s in sorted(jd_skills):
        jd_l    = jd_s.lower()
        in_text = bool(
            re.search(r"(?:^|[\s,;/(])" + re.escape(jd_l) + r"(?:[\s,;/)]|$)",
                      resume_text.lower())
        )
        in_extracted = jd_l in res_lower_set or any(
            jd_l in r or r in jd_l for r in res_lower_set
        )
        if in_text and not in_extracted:
            print(f"  EXTRACTION MISS: '{jd_s}'")

    print(f"\n{SEP}")
    print("FULL MATCH TRACE  (per JD skill)")
    print(SEP)
    sim_matrix, _, __ = build_similarity_matrix(jd_skills, resume_skills)
    matched, missing, scores = classify_gaps(
        jd_skills, resume_skills, sim_matrix, resume_text
    )

    pass_labels = {
        0:           "MISSING",
        1:           "exact",
        2:           "token/stem",
        3:           "cosine",
        4:           "abbrev",
        "implied-A": "implied-A",   # resume KB desc ↔ JD skill
        "implied-B": "implied-B",   # JD KB desc ↔ resume skill
        "implied-C": "implied-C",   # raw text window ↔ JD skill
    }

    for jd_s in sorted(jd_skills):
        info       = scores.get(jd_s, {})
        pass_num   = info.get("pass", 0)
        best_score = info.get("best_score", 0.0)
        best_match = info.get("best_match", "-")
        verdict    = "✓ MATCHED" if jd_s in matched else "✗ MISSING"
        pass_name  = pass_labels.get(pass_num, f"pass{pass_num}")
        print(f"  {verdict:12s}  [{pass_name:12s}  score={best_score:.3f}]  "
              f"'{jd_s}'  →  '{best_match}'")

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
        sys.exit(1)
    pdf_path = sys.argv[1]
    jd_arg   = sys.argv[2]
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    if jd_arg.endswith(".txt") and len(jd_arg) < 200:
        try:
            with open(jd_arg) as f:
                jd_text = f.read()
        except FileNotFoundError:
            jd_text = jd_arg
    else:
        jd_text = jd_arg
    debug_analysis(pdf_bytes, jd_text)