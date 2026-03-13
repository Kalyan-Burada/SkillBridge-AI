"""
abbreviation_matcher.py  –  Detect and match abbreviations / initialisms.

BUG FIXED
─────────
Old code contained this fallback in is_abbreviation():
    if re.match(r'^[a-z]{2,4}$', word):
        return True
This made every 2-4 letter lowercase word count as an abbreviation,
producing floods of false positives ("rest", "data", "plan", "goal", …).

Fix: removed the lowercase fallback entirely.
ALL-CAPS is the reliable signal for abbreviations, not lowercase length.

What is recognised as an abbreviation
───────────────────────────────────────
1. ALL-CAPS words, 2-8 letters     →  REST, HTML, API, SQL, CSS, NLP, BERT
2. Tokens with embedded digits     →  i2c, b2b, h2o, es6, oauth2
3. Tokens with / + . #             →  ci/cd, a/b, c++, c#, .net, asp.net
4. Patterns like "a/b testing"     →  single-char / single-char in full phrase
"""
from __future__ import annotations

import re


def extract_initials(phrase: str) -> str:
    """
    Extract initials from a multi-word phrase.

    Examples:
        "key performance indicators"                         → "kpi"
        "artificial intelligence"                            → "ai"
        "continuous integration continuous deployment"       → "cicd"
        "return on investment"                               → "roi"
        "bidirectional encoder representations transformers" → "bert"
        "structured query language"                          → "sql"
        "representational state transfer"                    → "rst"  (not "rest")
        "rest"                                               → "r"    (too short)
    """
    stop_words = {"the", "a", "an", "and", "or", "for", "to", "at", "of", "in"}
    words = phrase.lower().split()

    if len(words) > 3:
        filtered = [w for w in words if w not in stop_words]
        if filtered:
            initials = "".join(w[0] for w in filtered if w and w[0].isalpha())
            if len(initials) >= 2:
                return initials

    return "".join(w[0] for w in words if w and w[0].isalpha())


def is_abbreviation(text: str) -> bool:
    """
    Detect whether a phrase looks like an abbreviation or initialism.

    Recognised patterns:
    ─────────────────────
    • ALL-CAPS word, 2-8 chars          REST, HTML, API, BERT, LSTM, YAML, NLP
    • Digit-embedded token              i2c, b2b, es6, oauth2, h2o, gpt4
    • Special-char token (+#/.)         c++, c#, .net, ci/cd, asp.net, http/2
    • Single-char / single-char         a/b (as in "a/b testing")

    NOT recognised (intentional — avoids false positives):
    ───────────────────────────────────────────────────────
    • Short lowercase words (rest, data, plan, yaml, html in lowercase)
    • CamelCase alone (GraphQL, TypeScript) — these are product names
    """
    text = text.strip()
    if not text:
        return False

    original_words = text.split()
    words          = text.lower().split()

    if len(words) == 1:
        word = words[0]
        orig = original_words[0]

        # Signal 1: digit-embedded token (i2c, b2b, oauth2, es6, gpt4)
        if re.search(r"[0-9]", word):
            return True

        # Signal 2: special technical characters (+, #, /, .)
        if re.search(r"[+#/.]", word):
            return True

        # Signal 3: ALL-CAPS word, 2-8 chars
        if re.match(r"^[A-Z]{2,8}$", orig):
            return True

    # Multi-word: "a/b testing", "ci/cd pipeline"
    if re.search(r"\b[a-z]/[a-z]\b", text.lower()):
        return True

    return False


def matches_initials(abbr_phrase: str, full_phrase: str) -> bool:
    """
    Check whether an abbreviation matches a full phrase by initials.

    Examples:
        matches_initials("kpi",   "key performance indicators")              → True
        matches_initials("ai",    "artificial intelligence")                 → True
        matches_initials("ci/cd", "continuous integration continuous deployment") → True
        matches_initials("roi",   "return on investment")                    → True
        matches_initials("bert",  "bidirectional encoder representations transformers") → True
        matches_initials("sql",   "structured query language")               → True
        matches_initials("plc",   "programmable logic controller")           → True
    """
    abbr_lower = abbr_phrase.lower().strip()
    full_lower = full_phrase.lower().strip()

    # Check 1: exact or whole-word containment
    if abbr_lower == full_lower:
        return True
    if re.search(rf"(^|\s){re.escape(abbr_lower)}(\s|$)", full_lower):
        return True
    if re.search(rf"(^|\s){re.escape(full_lower)}(\s|$)", abbr_lower):
        return True

    # Check 2: initials match
    for word in abbr_phrase.lower().split():
        clean_abbr = re.sub(r"[/.]", "", word)
        if len(clean_abbr) >= 2 and clean_abbr.isalpha():
            full_initials = extract_initials(full_phrase)
            if clean_abbr == full_initials:
                return True

    return False


def get_abbreviation_boost(jd_skill: str, resume_skill: str) -> float:
    """
    Return 1.0 if one skill is clearly an abbreviation of the other, else 0.0.

    Args:
        jd_skill:     skill phrase from the job description
        resume_skill: skill phrase from the resume

    Returns:
        1.0 if abbreviation match confirmed, 0.0 otherwise.
    """
    if is_abbreviation(jd_skill) and matches_initials(jd_skill, resume_skill):
        return 1.0
    if is_abbreviation(resume_skill) and matches_initials(resume_skill, jd_skill):
        return 1.0
    return 0.0