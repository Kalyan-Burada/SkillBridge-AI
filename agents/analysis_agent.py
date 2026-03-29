"""
agents/analysis_agent.py  —  Gap Analysis (7-pass classifier + implication engine).

Reports match score and skill breakdown so the orchestrator can
route to the correct downstream agent (Strategy / FastTrack / Redirect).
"""
from __future__ import annotations

from typing import Any, Dict

from agents.base_agent import BaseAgent, AgentResult


class AnalysisAgent(BaseAgent):
    """Runs the 7-pass gap classification and reports match score."""

    @property
    def name(self) -> str:
        return "AnalysisAgent"

    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        jd_skills     = state.get("jd_skills", [])
        resume_skills = state.get("resume_skills", [])
        resume_text   = state.get("resume_text", "")

        if not jd_skills:
            return AgentResult(success=False, message="No JD skills available for analysis")

        from pipeline import build_similarity_matrix, classify_gaps

        sim_matrix, _, __ = build_similarity_matrix(jd_skills, resume_skills)
        matched, missing, per_skill_scores = classify_gaps(
            jd_skills, resume_skills, sim_matrix, resume_text
        )

        match_score = round(len(matched) / len(jd_skills) * 100, 1) if jd_skills else 0.0

        # Determine routing hint for the orchestrator
        if match_score >= 90:
            route_hint = "fast_track"
        elif match_score >= 40:
            route_hint = "strategy"
        else:
            route_hint = "redirect"

        # Confidence based on how many skills we had to work with
        confidence = 0.95
        if len(jd_skills) < 3:
            confidence -= 0.1
        if len(resume_skills) < 3:
            confidence -= 0.1

        return AgentResult(
            success=True,
            data={
                "matched_skills":   sorted(matched),
                "missing_skills":   sorted(missing),
                "match_score":      match_score,
                "per_skill_scores": per_skill_scores,
                "sim_matrix":       sim_matrix,
                "matched_count":    len(matched),
                "missing_count":    len(missing),
                "total_jd_skills":  len(jd_skills),
                "route_hint":       route_hint,
            },
            confidence=max(confidence, 0.5),
            message=f"Match score: {match_score}% ({len(matched)}/{len(jd_skills)} matched) → route: {route_hint}",
        )

    def _input_snapshot(self, state):
        jc = len(state.get("jd_skills", []))
        rc = len(state.get("resume_skills", []))
        return f"JD: {jc} skills, Resume: {rc} skills"

    def _output_snapshot(self, result):
        ms = result.data.get("match_score", 0)
        rh = result.data.get("route_hint", "unknown")
        return f"Match: {ms}% → {rh}"
