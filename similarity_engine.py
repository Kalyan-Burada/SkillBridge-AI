"""
similarity_engine.py  –  Semantic similarity computation for skill gap analysis.

Multi-pass matching strategy
─────────────────────────────
Pass 1 │ Exact string match (case-insensitive)
Pass 2 │ High-token-overlap match (handles minor wording differences)
Pass 3 │ Cosine semantic similarity ≥ MATCH_THRESHOLD (0.80)
Pass 4 │ Abbreviation / initialism match (see abbreviation_matcher.py)

Threshold choice (all-MiniLM-L6-v2, normalized embeddings)
────────────────────────────────────────────────────────────
• "python" vs "python programming"      → ~0.88  ✓ above 0.80 → match
• "rest api" vs "restful api"           → ~0.91  ✓ above 0.80 → match
• "react" vs "angular"                  → ~0.72  ✗ below 0.80 → no match
• "python" vs "java"                    → ~0.67  ✗ below 0.80 → no match
• "machine learning" vs "deep learning" → ~0.78  ✗ below 0.80 → no match
• "docker" vs "containerisation"        → ~0.68  ✗ below 0.80 → no match
"""
from __future__ import annotations

import re
import numpy as np
from typing import List, Tuple

from abbreviation_matcher import get_abbreviation_boost

# ── Thresholds ────────────────────────────────────────────────────────────────
MATCH_THRESHOLD: float = 0.80
TOKEN_OVERLAP_MIN: float = 0.85


# ── Helpers ───────────────────────────────────────────────────────────────────
def _token_overlap(a: str, b: str) -> float:
    """
    Fraction of tokens in the *shorter* string found in the *longer* one.
    Only applied when strings differ by ≤ 2 tokens.

    Examples:
        "machine learning"   vs "machine learning engineer"  → 1.0
        "rest api design"    vs "rest api"                   → 1.0
        "python"             vs "python programming language" → 1.0
        "ci/cd"              vs "kubernetes"                 → 0.0
    """
    ta = set(a.lower().split())
    tb = set(b.lower().split())
    shorter, longer = (ta, tb) if len(ta) <= len(tb) else (tb, ta)
    if not shorter:
        return 0.0
    if abs(len(ta) - len(tb)) > 2:
        return 0.0
    return len(shorter & longer) / len(shorter)


def _word_boundary_contains(needle: str, haystack: str) -> bool:
    """
    True if `needle` appears as a whole-word token sequence inside `haystack`.
    Prevents 'uart' matching 'quarter', 'sql' matching 'nosql', etc.
    """
    if not needle or not haystack:
        return False
    pattern = r'(?:^|[\s,;])' + re.escape(needle.lower()) + r'(?:[\s,;]|$)'
    return bool(re.search(pattern, haystack.lower()))


# ── Public API ────────────────────────────────────────────────────────────────
def compute_similarity_matrix(
    jd_embeddings,
    resume_embeddings,
) -> np.ndarray:
    """
    Compute cosine similarity between JD skill embeddings and resume skill
    embeddings.

    Args:
        jd_embeddings:     array-like of shape (n_jd, dim)
        resume_embeddings: array-like of shape (n_resume, dim)

    Returns:
        np.ndarray of shape (n_jd, n_resume) — cosine similarity scores in [0, 1]
    """
    jd = np.asarray(jd_embeddings, dtype=float)
    res = np.asarray(resume_embeddings, dtype=float)

    if jd.ndim == 1:
        jd = jd[np.newaxis, :]
    if res.ndim == 1:
        res = res[np.newaxis, :]

    if jd.shape[0] == 0 or res.shape[0] == 0:
        return np.zeros((jd.shape[0], res.shape[0]), dtype=float)

    # Safe L2-normalisation
    jd_norms = np.linalg.norm(jd, axis=1, keepdims=True)
    res_norms = np.linalg.norm(res, axis=1, keepdims=True)
    jd = jd / np.where(jd_norms > 1e-9, jd_norms, 1.0)
    res = res / np.where(res_norms > 1e-9, res_norms, 1.0)

    sim = jd @ res.T
    return np.clip(sim, 0.0, 1.0).astype(float)


def classify_gaps(
    jd_skills: List[str],
    resume_skills: List[str],
    similarity_matrix: np.ndarray,
    threshold: float = MATCH_THRESHOLD,
) -> Tuple[List[str], List[str]]:
    """
    Classify each JD skill as *matched* (found in resume) or *missing*.

    Four passes — each successively broader:
      1. Exact string match (case-insensitive, stripped)
      2. High token-overlap (handles "machine learning" ↔ "machine learning model")
      3. Cosine semantic similarity ≥ threshold
      4. Abbreviation / initialism matching (AI↔artificial intelligence, etc.)

    Args:
        jd_skills:         skills extracted from the job description
        resume_skills:     skills extracted from the resume
        similarity_matrix: cosine similarity matrix from compute_similarity_matrix()
        threshold:         minimum cosine similarity to count as a match (default 0.80)

    Returns:
        (matched, missing) — two lists of JD skill strings
    """
    if not jd_skills:
        return [], []
    if not resume_skills:
        return [], list(jd_skills)

    sim = np.asarray(similarity_matrix, dtype=float)
    resume_lower = [s.lower().strip() for s in resume_skills]
    resume_lower_set = set(resume_lower)

    matched: List[str] = []
    missing: List[str] = []

    for i, jd_skill in enumerate(jd_skills):
        jd_lower = jd_skill.lower().strip()

        # Pass 1: Exact string match
        if jd_lower in resume_lower_set:
            matched.append(jd_skill)
            continue

        # Pass 2: Token overlap
        overlap_hit = any(
            _token_overlap(jd_lower, r_lower) >= TOKEN_OVERLAP_MIN
            for r_lower in resume_lower
        )
        if overlap_hit:
            matched.append(jd_skill)
            continue

        # Pass 3: Semantic similarity
        sem_hit = (
            sim.ndim == 2
            and i < sim.shape[0]
            and sim.shape[1] > 0
            and float(sim[i].max()) >= threshold
        )
        if sem_hit:
            matched.append(jd_skill)
            continue

        # Pass 4: Abbreviation / initialism
        abbr_hit = any(
            get_abbreviation_boost(jd_skill, r_skill) > 0.0
            for r_skill in resume_skills
        )
        (matched if abbr_hit else missing).append(jd_skill)

    return matched, missing