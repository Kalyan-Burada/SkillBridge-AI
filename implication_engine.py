"""
implication_engine.py  —  Dynamic Skill Implication Engine for Career Copilot

PROBLEM SOLVED
══════════════
A Data Science JD requires "Python". The resume never writes "Python" but lists
"built ML pipelines with scikit-learn, TensorFlow, and pandas." The old system
marks Python as MISSING. This is wrong — scikit-learn/TF/pandas are Python
libraries; Python is strongly implied.

The reverse also matters:
A JD asks for "machine learning." The resume writes "Python, scikit-learn,
cross-validation, gradient boosting." Machine learning is implied.

APPROACH — ZERO HARDCODING, FULLY DYNAMIC
══════════════════════════════════════════
Three complementary passes, all using semantic similarity with no lookup tables:

  PASS A │ KB-description implication
  ────────┼──────────────────────────────────────────────────────────────────
          │ For each (jd_skill, resume_skill) pair:
          │   • Embed the JD skill phrase
          │   • Embed the resume skill's KB description
          │   • If cosine ≥ IMPL_DESC_THRESHOLD → jd_skill is implied
          │ Rationale: "scikit-learn"'s KB description says "Python machine
          │ learning library" → Python embedding is close → Python implied.

  PASS B │ Reverse KB-description implication
  ────────┼──────────────────────────────────────────────────────────────────
          │ For each (jd_skill, resume_skill) pair:
          │   • Embed the resume skill phrase
          │   • Embed the JD skill's KB description
          │   • If cosine ≥ IMPL_DESC_THRESHOLD → jd_skill is implied
          │ Rationale: JD asks "machine learning." Its KB description says
          │ "algorithms that learn from data... scikit-learn, TensorFlow."
          │ Resume has "scikit-learn" → close to that description → implied.

  PASS C │ Raw-text semantic sliding window
  ────────┼──────────────────────────────────────────────────────────────────
          │ Splits resume text into overlapping sentence-groups, embeds them,
          │ and checks if any window is semantically close to the JD skill.
          │ Catches implications buried in prose that extraction missed entirely.
          │ Uses a stricter threshold to avoid false positives.

WHY THIS IS BETTER THAN THE OLD _knowledge_implied_match()
════════════════════════════════════════════════════════════
Old approach: token overlap of JD phrase against KB description string.
  • "python" vs "Python machine learning library" → partial match on "python" ✓
  • "data analysis" vs "examining datasets" → NO match (different words) ✗

New approach: semantic embeddings
  • "data analysis" ↔ "examining datasets to draw conclusions" → HIGH cosine ✓
  • "sql" ↔ "data manipulation and querying using structured language" → HIGH ✓
  • "agile" ↔ "sprint planning and iterative delivery methodology" → HIGH ✓

THRESHOLDS (tuned conservatively to avoid false positives)
══════════════════════════════════════════════════════════
  IMPL_DESC_THRESHOLD  = 0.52   (KB description similarity)
  IMPL_TEXT_THRESHOLD  = 0.60   (raw text window — stricter)
  WINDOW_SENTENCES     = 3      (sentences per sliding window)

Fully offline — uses the same all-MiniLM-L6-v2 model already loaded
by pipeline.py. No extra dependencies.
"""
from __future__ import annotations

import re
import numpy as np
from typing import List, Dict, Optional, Tuple

# ── Thresholds ─────────────────────────────────────────────────────────────
IMPL_DESC_THRESHOLD:  float = 0.42  # KB description → JD skill (lowered from 0.52)
IMPL_TEXT_THRESHOLD:  float = 0.45  # Raw text window (lowered from 0.60)
IMPL_TOKEN_THRESHOLD: float = 0.60  # Pass D: token overlap in KB description
WINDOW_SENTENCES:     int   = 4     # Wider window for more context

# ── Lazy model ref (shares the singleton from pipeline.py) ─────────────────
_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embed(texts: List[str]) -> np.ndarray:
    if not texts:
        return np.zeros((0, 384), dtype=np.float32)
    return _get_model().encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=64,
    ).astype(np.float32)


# ── Sentence splitter ──────────────────────────────────────────────────────
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n{1,2}")

def _split_sentences(text: str) -> List[str]:
    """Split text into sentences; filter noise."""
    raw = _SENT_SPLIT.split(text.strip())
    return [s.strip() for s in raw if len(s.strip()) > 15]


def _sliding_windows(sentences: List[str], size: int = WINDOW_SENTENCES) -> List[str]:
    """Generate overlapping sentence-group windows."""
    if not sentences:
        return []
    if len(sentences) <= size:
        return [" ".join(sentences)]
    return [
        " ".join(sentences[i : i + size])
        for i in range(0, len(sentences) - size + 1)
    ]


# ── KB description cache ───────────────────────────────────────────────────
_kb_desc_cache: Dict[str, str] = {}

def _get_kb_description(skill: str) -> str:
    """Return KB description for skill; cache for speed."""
    if skill not in _kb_desc_cache:
        from knowledge_base import get_skill_knowledge
        kb = get_skill_knowledge(skill)
        _kb_desc_cache[skill] = kb.get("description", "")
    return _kb_desc_cache[skill]


# ── Core implication check ─────────────────────────────────────────────────

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two 1-D normalised vectors."""
    return float(np.dot(a, b))


class ImplicationEngine:
    """
    Stateful engine that caches embeddings across calls for speed.

    Usage:
        engine = ImplicationEngine(resume_text)
        implied = engine.find_implied_skills(jd_skills, resume_skills)
    """

    def __init__(self, resume_text: str = ""):
        self._resume_text    = resume_text
        self._skill_emb_cache: Dict[str, np.ndarray] = {}
        self._desc_emb_cache:  Dict[str, np.ndarray] = {}
        self._windows:          List[str]             = []
        self._window_embs_cache: Optional[np.ndarray] = None

        if resume_text:
            sentences      = _split_sentences(resume_text)
            self._windows  = _sliding_windows(sentences, WINDOW_SENTENCES)

    # ── embedding helpers ──────────────────────────────────────────────────

    def _skill_emb(self, skill: str) -> np.ndarray:
        if skill not in self._skill_emb_cache:
            self._skill_emb_cache[skill] = _embed([skill])[0]
        return self._skill_emb_cache[skill]

    def _desc_emb(self, skill: str) -> np.ndarray:
        if skill not in self._desc_emb_cache:
            desc = _get_kb_description(skill)
            if desc:
                self._desc_emb_cache[skill] = _embed([desc])[0]
            else:
                self._desc_emb_cache[skill] = self._skill_emb(skill)
        return self._desc_emb_cache[skill]

    def _window_embs(self) -> Optional[np.ndarray]:
        if self._window_embs_cache is None and self._windows:
            self._window_embs_cache = _embed(self._windows)
        return self._window_embs_cache

    # ── PASS A: resume_skill KB description ↔ jd_skill phrase ────────────

    def _pass_a(self, jd_skill: str, resume_skills: List[str]) -> Optional[str]:
        """
        Check if any resume skill's KB description is semantically close
        to the JD skill phrase.

        Example: JD="python", resume has "scikit-learn"
          → "scikit-learn" KB desc: "Python machine learning library..."
          → embedding of desc is close to embedding of "python"
          → IMPLIED
        """
        jd_emb = self._skill_emb(jd_skill)
        best_score  = 0.0
        best_match: Optional[str] = None

        for rs in resume_skills:
            desc_emb = self._desc_emb(rs)
            score    = _cosine(jd_emb, desc_emb)
            if score > best_score:
                best_score = score
                best_match = rs

        if best_score >= IMPL_DESC_THRESHOLD:
            return best_match
        return None

    # ── PASS B: jd_skill KB description ↔ resume_skill phrase ────────────

    def _pass_b(self, jd_skill: str, resume_skills: List[str]) -> Optional[str]:
        """
        Check if any resume skill phrase is semantically close to the
        JD skill's own KB description.

        Example: JD="machine learning"
          → its KB desc: "...algorithms... scikit-learn, gradient boosting..."
          → resume has "scikit-learn" → close to that description
          → IMPLIED
        """
        jd_desc_emb = self._desc_emb(jd_skill)
        best_score  = 0.0
        best_match: Optional[str] = None

        for rs in resume_skills:
            rs_emb = self._skill_emb(rs)
            score  = _cosine(jd_desc_emb, rs_emb)
            if score > best_score:
                best_score = score
                best_match = rs

        if best_score >= IMPL_DESC_THRESHOLD:
            return best_match
        return None

    # ── PASS C: raw resume text windows ↔ jd_skill phrase ────────────────

    def _pass_c(self, jd_skill: str) -> bool:
        """
        Check if any sliding window of the resume text is semantically
        close to the JD skill phrase.

        Catches cases where the skill is strongly implied by context
        even if the extractor never pulled it out as a phrase.

        Example: JD="python". Resume window: "Implemented gradient descent
        from scratch, built custom neural networks, automated ETL scripts."
        → High semantic similarity to "python" (programming context)
        → IMPLIED
        """
        w_embs = self._window_embs()
        if w_embs is None or w_embs.shape[0] == 0:
            return False

        jd_emb = self._skill_emb(jd_skill)
        sims   = (w_embs @ jd_emb).astype(float)
        return float(sims.max()) >= IMPL_TEXT_THRESHOLD

    # ── PASS D: token co-occurrence in KB descriptions ───────────────────
    # This is the reliable fallback when semantic similarity scores land just
    # below threshold. If the JD skill's name appears as a token inside any
    # resume skill's KB description, or vice versa, treat it as implied.
    #
    # Example: JD="python"
    #   resume has "scikit-learn" → KB desc: "...Python machine learning..."
    #   "python" is a token in that description → IMPLIED
    #
    # Example: JD="machine learning"
    #   resume has "tensorflow" → KB desc: "...deep learning and machine learning..."
    #   "machine" and "learning" both appear → token overlap ≥ 0.60 → IMPLIED

    def _pass_d(self, jd_skill: str, resume_skills: List[str]) -> Optional[str]:
        jd_tokens = set(re.findall(r"[a-z0-9]+", jd_skill.lower()))
        jd_tokens -= {"a", "an", "the", "and", "or", "for", "to", "of", "in", "with"}
        if not jd_tokens:
            return None

        for rs in resume_skills:
            desc = _get_kb_description(rs).lower()
            if not desc:
                continue
            desc_tokens = set(re.findall(r"[a-z0-9]+", desc))
            overlap = len(jd_tokens & desc_tokens) / len(jd_tokens)
            if overlap >= IMPL_TOKEN_THRESHOLD:
                return rs

        # Reverse: resume skill tokens inside JD's KB description
        jd_desc = _get_kb_description(jd_skill).lower()
        if jd_desc:
            jd_desc_tokens = set(re.findall(r"[a-z0-9]+", jd_desc))
            for rs in resume_skills:
                rs_tokens = set(re.findall(r"[a-z0-9]+", rs.lower()))
                rs_tokens -= {"a", "an", "the", "and", "or", "for", "to", "of", "in"}
                if not rs_tokens:
                    continue
                overlap = len(rs_tokens & jd_desc_tokens) / len(rs_tokens)
                if overlap >= IMPL_TOKEN_THRESHOLD:
                    return rs

        return None

    # ── Public interface ───────────────────────────────────────────────────

    def check_implied(
        self,
        jd_skill:      str,
        resume_skills: List[str],
    ) -> Tuple[bool, Optional[str], str]:
        """
        Check if a missing JD skill is implied by the resume.

        Returns:
            (is_implied, best_resume_match, pass_label)
        """
        # Pass A: resume skill KB desc ↔ JD skill phrase (semantic)
        match_a = self._pass_a(jd_skill, resume_skills)
        if match_a:
            return True, match_a, "implied-A"

        # Pass B: JD skill KB desc ↔ resume skill phrase (semantic)
        match_b = self._pass_b(jd_skill, resume_skills)
        if match_b:
            return True, match_b, "implied-B"

        # Pass C: raw text sliding window ↔ JD skill phrase
        if self._pass_c(jd_skill):
            return True, None, "implied-C"

        # Pass D: token co-occurrence in KB descriptions (reliable fallback)
        match_d = self._pass_d(jd_skill, resume_skills)
        if match_d:
            return True, match_d, "implied-D"

        return False, None, ""

    def find_implied_skills(
        self,
        jd_skills:     List[str],
        resume_skills: List[str],
        missing_skills: List[str],
    ) -> Dict[str, dict]:
        """
        For each missing JD skill, check if it is implied by the resume.

        Returns:
            Dict mapping implied jd_skill → {
                "best_match": resume skill that implies it (or None for text-based),
                "pass": "implied-A" | "implied-B" | "implied-C",
            }
        """
        implied: Dict[str, dict] = {}
        for jd_skill in missing_skills:
            is_implied, best_match, pass_label = self.check_implied(
                jd_skill, resume_skills
            )
            if is_implied:
                implied[jd_skill] = {
                    "best_match": best_match,
                    "pass":       pass_label,
                }
        return implied


# ── Module-level convenience function ─────────────────────────────────────

def find_implied_skills(
    jd_skills:      List[str],
    resume_skills:  List[str],
    missing_skills: List[str],
    resume_text:    str = "",
) -> Dict[str, dict]:
    """
    Convenience wrapper — creates a one-shot ImplicationEngine.

    Args:
        jd_skills:      All JD skills (for context)
        resume_skills:  Extracted resume skills
        missing_skills: JD skills not yet matched (subset of jd_skills)
        resume_text:    Raw resume text for Pass C

    Returns:
        Dict of implied skills (see ImplicationEngine.find_implied_skills)
    """
    engine = ImplicationEngine(resume_text)
    return engine.find_implied_skills(jd_skills, resume_skills, missing_skills)