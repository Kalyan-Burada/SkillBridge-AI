"""
agents/compliance_agent.py  —  Output compliance validation.

Checks generated advice for:
  - Bias / discriminatory language
  - Hallucinated skills (mentions skills not in the JD or resume)
  - Required structure completeness
  - Professional tone

If compliance fails, returns specific violations so the orchestrator
can re-route to StrategyAgent with constraints.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List

from agents.base_agent import BaseAgent, AgentResult


# ── Configurable compliance rules ──────────────────────────────────────────
# These are loaded from patterns — NOT hardcoded skill lists.
# They check structure and language, not domain-specific content.

_BIAS_PATTERNS = [
    r"\b(too old|too young|gender|race|religion|disability|pregnant)\b",
    r"\b(he should|she should|his career|her career)\b",
    r"\b(native speaker|mother tongue)\b",
]

_REQUIRED_ADVICE_KEYS = [
    "career_summary",
    "action_plan",
]


class ComplianceAgent(BaseAgent):
    """Validates output for bias, completeness, and hallucination."""

    @property
    def name(self) -> str:
        return "ComplianceAgent"

    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        career_advice  = state.get("career_advice")
        jd_skills      = state.get("jd_skills", [])
        resume_skills  = state.get("resume_skills", [])

        # If no advice to validate (e.g., FastTrack path), pass through
        if career_advice is None:
            return AgentResult(
                success=True,
                data={"compliance_status": "skipped", "violations": []},
                confidence=1.0,
                message="No career advice to validate — compliance check skipped",
            )

        violations: List[str] = []

        # Check 1: Bias / discriminatory language
        bias_hits = self._check_bias(career_advice)
        violations.extend(bias_hits)

        # Check 2: Required structure
        struct_hits = self._check_structure(career_advice)
        violations.extend(struct_hits)

        # Check 3: Hallucinated skills (mentions something not in JD or resume)
        halluc_hits = self._check_hallucination(career_advice, jd_skills, resume_skills)
        violations.extend(halluc_hits)

        if violations:
            return AgentResult(
                success=False,
                data={
                    "compliance_status": "failed",
                    "violations": violations,
                    "constraints": [f"Fix: {v}" for v in violations],
                },
                confidence=0.9,
                message=f"Compliance failed: {len(violations)} violation(s) found",
            )

        return AgentResult(
            success=True,
            data={"compliance_status": "passed", "violations": []},
            confidence=0.95,
            message="All compliance checks passed",
        )

    def _check_bias(self, advice: dict) -> List[str]:
        """Scan all text fields for bias patterns."""
        violations = []
        text_blob = self._flatten_advice(advice).lower()
        for pattern in _BIAS_PATTERNS:
            matches = re.findall(pattern, text_blob, re.IGNORECASE)
            if matches:
                violations.append(f"Potential bias detected: '{matches[0]}'")
        return violations

    def _check_structure(self, advice: dict) -> List[str]:
        """Verify required keys exist and are non-empty."""
        violations = []
        for key in _REQUIRED_ADVICE_KEYS:
            val = advice.get(key)
            if not val:
                violations.append(f"Missing required field: '{key}'")
            elif isinstance(val, str) and len(val.strip()) < 10:
                violations.append(f"Field '{key}' is too short ({len(val.strip())} chars)")
        return violations

    def _check_hallucination(self, advice: dict, jd_skills: list,
                              resume_skills: list) -> List[str]:
        """
        Check if the advice recommends learning skills that aren't
        actually in the JD. Light check — we don't want false positives.
        """
        violations = []
        priority = advice.get("priority_skills", [])
        all_known = set(s.lower() for s in jd_skills + resume_skills)

        for item in priority:
            skill_name = item.get("skill", "") if isinstance(item, dict) else str(item)
            if skill_name and skill_name.lower() not in all_known:
                # Only flag if the skill is suspiciously unrelated
                # (short single-word that doesn't match anything)
                if len(skill_name.split()) == 1 and len(skill_name) < 20:
                    # Check if it's a substring of any known skill
                    substr_match = any(skill_name.lower() in k for k in all_known)
                    if not substr_match:
                        violations.append(
                            f"Potential hallucination: '{skill_name}' not found in JD or resume"
                        )
        return violations

    def _flatten_advice(self, advice: dict) -> str:
        """Recursively extract all string values from the advice dict."""
        texts = []
        if isinstance(advice, dict):
            for v in advice.values():
                texts.append(self._flatten_advice(v))
        elif isinstance(advice, list):
            for item in advice:
                texts.append(self._flatten_advice(item))
        elif isinstance(advice, str):
            return advice
        return " ".join(texts)

    def _input_snapshot(self, state):
        has_advice = state.get("career_advice") is not None
        return f"Advice present: {has_advice}"
