"""
phrase_extracter.py  –  Skill-phrase extraction via pretrained transformer model.

Architecture (2-stage pipeline, ZERO hardcoded skill names)
────────────────────────────────────────────────────────────
Stage 1 │ Candidate mining (spaCy en_core_web_sm)
         │ • Harvest PROPN tokens, NER spans, and short noun-chunks.
         │ • Hard-signal tokens (ALL-CAPS, digits, special chars, CamelCase)
         │   are always kept regardless of classifier score.
─────────┼──────────────────────────────────────────────────────────────────────
Stage 2  │ Skill classification (all-MiniLM-L6-v2 sentence-transformer)
         │
         │ Uses ZERO-SHOT descriptive anchors — natural-language phrases that
         │ describe *what kind of thing* a skill is, without naming any specific
         │ skill, tool, technology, or domain.  This makes the extractor work
         │ for any resume or JD regardless of domain (software, finance,
         │ healthcare, supply-chain, marketing, legal, manufacturing, …).
         │
         │ _SKILL_ANCHORS      describe semantic neighbourhood of skill-like content
         │ _NON_SKILL_ANCHORS  describe semantic neighbourhood of noise
         │
         │ A candidate is kept when:
         │   cosine-sim to SKILL anchors ≥ _SKILL_SIM_THRESHOLD
         │   AND > cosine-sim to NON-SKILL anchors − _GENERIC_PENALTY_DELTA
─────────┴──────────────────────────────────────────────────────────────────────

Fully offline — requires only:
  • spaCy   en_core_web_sm   (python -m spacy download en_core_web_sm)
  • sentence-transformers    (pip install sentence-transformers)
  • nltk stopwords           (python -m nltk.downloader stopwords)
"""
from __future__ import annotations

import re
import spacy
from nltk.corpus import stopwords

# ── Model singletons (loaded once on first call) ──────────────────────────────
_nlp:            object | None = None
_st_model:       object | None = None
_skill_embs:     object | None = None
_non_skill_embs: object | None = None
_np:             object | None = None

# ── Zero-shot anchor phrases ──────────────────────────────────────────────────
# These describe the SEMANTIC CHARACTER of skills without naming any specific
# skill, tool, technology, or domain — making the extractor domain-agnostic.
#
# Rule: never add named skills/technologies/products here. Only descriptions.
_SKILL_ANCHORS: list[str] = [
    # What a skill IS conceptually
    "professional technical skill competency qualification",
    "industry-specific knowledge domain expertise specialization",
    "software tool platform technology methodology framework",
    "certification credential license standard protocol specification",
    "analytical quantitative data-driven computational capability",
    "engineering scientific technical discipline subject matter",
    # HOW skills appear in job postings and resumes
    "required proficiency hands-on working knowledge experience",
    "technical implementation deployment operation administration",
    "ability to design build develop architect engineer implement",
    "programming scripting automation orchestration integration",
    "management planning strategy execution governance leadership",
    "clinical medical pharmaceutical regulatory compliance procedure",
    "financial accounting legal contractual operational process",
    "creative design artistic production editorial publishing",
]

_NON_SKILL_ANCHORS: list[str] = [
    # Pure positive adjectives (modify skills but are not skills)
    "strong excellent great outstanding superior high-quality",
    "good solid proven demonstrated required preferred desirable",
    # Generic gerunds / action verbs used as filler
    "working leading managing building creating seeking looking",
    "responsible passionate driven collaborative motivated enthusiastic",
    # Quantity / duration markers
    "years months experience background history track record tenure",
    # Pure relationship / communication nouns (too generic on their own)
    "team communication interpersonal stakeholder reporting structure",
    # Pure role titles (not skills in isolation)
    "engineer developer analyst manager specialist consultant director",
    # Generic company / org words
    "company organization team department group division",
]

# ── Classification thresholds ─────────────────────────────────────────────────
_SKILL_SIM_THRESHOLD:   float = 0.22
_GENERIC_PENALTY_DELTA: float = 0.06

# ── Stop-words ────────────────────────────────────────────────────────────────
stop_words: set[str] = set(stopwords.words("english"))
stop_words.update({
    # Skill noise
    "skills", "skill", "experience", "experienced", "knowledge", "background",
    "understanding", "ability", "abilities", "proficiency", "expertise",
    "familiarity", "grasp", "awareness", "competency", "competencies",
    "qualifications", "requirements", "responsibilities", "duties", "tasks",
    # Quantity / frequency
    "years", "year", "months", "month",
    # Generic modifiers
    "strong", "excellent", "good", "great", "deep", "solid", "high",
    "proven", "demonstrated", "required", "preferred", "related",
    "relevant", "various", "including", "using", "within", "across",
    "through", "following", "multiple", "key", "core", "primary",
    # Role titles
    "engineer", "engineers", "developer", "developers",
    "programmer", "programmers", "architect", "architects",
    "analyst", "analysts", "manager", "managers",
    "specialist", "specialists", "consultant", "consultants",
    "candidate", "candidates", "professional", "professionals",
    "lead", "leads", "owner", "owners", "member", "members",
    "director", "directors", "officer", "executive",
    # Split tokens of known compounds (kept as compound only)
    "ci", "cd",
})

# ── Noun-chunk trimming sets ───────────────────────────────────────────────────
_CHUNK_TRIM_START: frozenset[str] = frozenset({
    "strong", "excellent", "good", "great", "solid", "deep",
    "proven", "required", "preferred", "senior", "junior",
    "much", "specific", "minimum", "basic", "advanced", "clear",
    "high", "key", "core", "primary", "general", "overall",
})

_CHUNK_TRIM_END: frozenset[str] = frozenset({
    "experience", "knowledge", "skills", "skill",
    "developer", "developers", "engineer", "engineers",
    "specialist", "analysts", "analyst", "architect", "architects",
    "programmer", "programmers", "candidate", "candidates",
    "methodology", "methodologies", "practices", "principles",
    "concepts", "team", "role", "position", "job",
    "requirement", "requirements", "background", "understanding",
    "ability",
    # "environment", "tools", "solutions", "systems" removed —
    # these form valid compound skills: "debugging tools",
    # "embedded systems", "version control systems", etc.
})


# ── Lazy-load ─────────────────────────────────────────────────────────────────
def _load() -> None:
    """Initialise spaCy + SentenceTransformer and pre-compute anchor embeddings."""
    global _nlp, _st_model, _skill_embs, _non_skill_embs, _np
    if _st_model is not None:
        return

    import numpy as np
    _np = np
    _nlp = spacy.load("en_core_web_sm")

    from sentence_transformers import SentenceTransformer
    _st_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    _skill_embs = _st_model.encode(
        _SKILL_ANCHORS, convert_to_numpy=True, normalize_embeddings=True
    )
    _non_skill_embs = _st_model.encode(
        _NON_SKILL_ANCHORS, convert_to_numpy=True, normalize_embeddings=True
    )


# ── Hard-signal helpers ───────────────────────────────────────────────────────
def _hard_bypass(word: str) -> bool:
    """
    Returns True for single tokens that must be kept regardless of cosine score.

    Signals recognised:
    • Digit embedded   → OAuth2, i2c, ES6, GPT4, HTML5
    • Special chars    → C++, C#, .NET, CI/CD, Node.js, ASP.NET
    • ALL-CAPS acronym → REST, HTML, API, SQL, AWS, NLP (2–8 chars)

    Multi-word phrases are excluded so full phrases go through the classifier.
    """
    if not word or " " in word:
        return False
    has_digit   = any(c.isdigit() for c in word)
    has_special = any(c in ("+", "#", "/", ".") for c in word)
    is_acronym  = word.isupper() and 2 <= len(word.replace(" ", "")) <= 8
    return has_digit or has_special or is_acronym


def _hard_signal(word: str) -> bool:
    """Broader signal for mining (includes CamelCase)."""
    if _hard_bypass(word):
        return True
    return any(c.isupper() for c in word) and any(c.islower() for c in word)


# ── Stage 1 — candidate mining ────────────────────────────────────────────────
def _mine_candidates(text_list: list[str]) -> set[str]:
    """
    Extract coarse candidate phrases via spaCy.

    Three harvest strategies:
    a) PROPN tokens (non-GPE) and hard-signal tokens
    b) NER spans: ORG, PRODUCT, NORP, WORK_OF_ART
    c) Noun chunks ≤ 4 meaningful tokens (stripped of generic edges)
    """
    candidates: set[str] = set()

    for sentence in text_list:
        sentence = sentence.strip()
        if not sentence:
            continue

        doc = _nlp(sentence)

        gpe_tok_idx: set[int] = {
            tok.i for ent in doc.ents if ent.label_ == "GPE" for tok in ent
        }

        # (a) Token-level
        for token in doc:
            if token.pos_ in (
                "PUNCT", "SPACE", "SYM", "CCONJ", "ADP", "DET",
                "PRON", "VERB", "AUX",
            ):
                continue
            t = token.text.strip()
            if len(t) < 2 or t.lower() in stop_words:
                continue
            not_gpe   = token.i not in gpe_tok_idx
            hard_bp   = _hard_bypass(t)
            camel     = _hard_signal(t) and not hard_bp
            is_propn  = token.pos_ == "PROPN" and not_gpe
            if hard_bp or is_propn or (camel and not_gpe):
                candidates.add(t)

        # (b) Named-entity
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT", "NORP", "WORK_OF_ART"):
                t = ent.text.strip()
                if 2 <= len(t) <= 60:
                    candidates.add(t)

        # (c) Noun chunks
        skip_spans: set[str] = {
            ent.text for ent in doc.ents if ent.label_ in ("GPE", "PERSON")
        }
        for chunk in doc.noun_chunks:
            tokens = [tk for tk in chunk if tk.pos_ not in ("DET", "PRON", "PUNCT")]
            if not tokens:
                continue
            while len(tokens) > 1 and tokens[0].text.lower() in _CHUNK_TRIM_START:
                tokens = tokens[1:]
            while len(tokens) > 1 and tokens[-1].text.lower() in _CHUNK_TRIM_END:
                tokens = tokens[:-1]
            if 1 <= len(tokens) <= 4:
                t = " ".join(tk.text for tk in tokens).strip()
                if (
                    t
                    and len(t) >= 2
                    and t.lower() not in stop_words
                    and t not in skip_spans
                ):
                    candidates.add(t)

    return candidates


# ── Stage 2 — skill classification ───────────────────────────────────────────
def _classify(raw_candidates: set[str]) -> set[str]:
    """
    Score candidates against zero-shot anchor embeddings.

    Kept if:
      • Hard-bypass signal (digit / +#/. / ALL-CAPS), OR
      • max cosine-sim to _SKILL_ANCHORS ≥ _SKILL_SIM_THRESHOLD
        AND > max cosine-sim to _NON_SKILL_ANCHORS − _GENERIC_PENALTY_DELTA
    """
    if not raw_candidates:
        return set()

    candidates  = list(raw_candidates)
    bypass      = {c for c in candidates if _hard_bypass(c)}
    to_score    = [c for c in candidates if c not in bypass]
    kept        = set(bypass)

    if to_score:
        embs             = _st_model.encode(
            to_score, convert_to_numpy=True, normalize_embeddings=True
        )
        skill_scores     = (embs @ _skill_embs.T).max(axis=1)
        non_skill_scores = (embs @ _non_skill_embs.T).max(axis=1)

        for cand, ss, ns in zip(to_score, skill_scores, non_skill_scores):
            if ss >= _SKILL_SIM_THRESHOLD and ss > ns - _GENERIC_PENALTY_DELTA:
                kept.add(cand)

    return kept


# ── Post-processing ───────────────────────────────────────────────────────────
def _normalize(text: str) -> str:
    text = text.lower().strip().strip(",;")
    text = re.sub(r"\s*([/\-.+#])\s*", r"\1", text)
    return re.sub(r"\s+", " ", text)


def _dedup(skills: set[str]) -> set[str]:
    """Remove strict substrings of longer skills already in result set."""
    result: set[str] = set()
    for x in sorted(skills, key=len, reverse=True):
        if not any(x in y and x != y for y in result):
            result.add(x)
    return result


# ── Public interface ──────────────────────────────────────────────────────────
def extract_candidate_phrases(text_list: list[str]) -> list[str]:
    """
    Extract skill / technology phrases from a list of text segments.

    Two-stage pipeline:
      Stage 1 (spaCy)               – mine coarse candidates
      Stage 2 (SentenceTransformer) – classify via zero-shot anchors

    No hardcoded skill names. Works for software, finance, healthcare,
    supply-chain, marketing, legal, manufacturing, and any other domain.

    Args:
        text_list: pre-cleaned, split text segments

    Returns:
        Sorted, deduplicated list of lowercase skill strings.
    """
    _load()
    raw        = _mine_candidates(text_list)
    if not raw:
        return []
    skills     = _classify(raw)
    normalized = {_normalize(s) for s in skills if len(s.strip()) >= 2}
    normalized = {s for s in normalized if s not in stop_words}
    return sorted(_dedup(normalized))


# Legacy symbol
_SKILL_ENT_LABELS = {"ORG", "PRODUCT", "NORP", "WORK_OF_ART"}