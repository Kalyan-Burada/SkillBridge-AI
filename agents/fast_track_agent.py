"""
agents/fast_track_agent.py  —  High-match candidate handler.

When match score > 90%, the orchestrator routes here INSTEAD of StrategyAgent.
Generates an interview-readiness report rather than an upskilling plan.
"""
from __future__ import annotations

from typing import Any, Dict

from agents.base_agent import BaseAgent, AgentResult


class FastTrackAgent(BaseAgent):
    """Generates interview-readiness report for high-match candidates (>90%)."""

    @property
    def name(self) -> str:
        return "FastTrackAgent"

    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        matched_skills = state.get("matched_skills", [])
        missing_skills = state.get("missing_skills", [])
        match_score    = state.get("match_score", 0.0)
        jd_skills      = state.get("jd_skills", [])

        # Build interview readiness report
        strengths = []
        for skill in matched_skills[:8]:
            strengths.append(f"Demonstrated proficiency in {skill}")

        if len(matched_skills) >= len(jd_skills) * 0.9:
            strengths.append(
                f"Exceptional coverage: {len(matched_skills)}/{len(jd_skills)} required skills matched"
            )

        # Minor gaps (if any)
        minor_gaps = []
        if missing_skills:
            minor_gaps = [
                f"Minor gap: {skill} — can likely be learned on the job"
                for skill in missing_skills[:3]
            ]

        # Interview prep recommendations (dynamically based on matched skills)
        interview_prep = []
        if matched_skills:
            top_skills = matched_skills[:5]
            interview_prep.append(
                f"Prepare STAR stories demonstrating expertise in: {', '.join(top_skills)}"
            )
        interview_prep.append("Review the company's recent projects and align your experience")
        interview_prep.append("Prepare questions showing depth in your matched skill areas")
        if missing_skills:
            interview_prep.append(
                f"Be ready to discuss your plan for: {', '.join(missing_skills[:2])}"
            )

        report = {
            "report_type": "fast_track_interview_readiness",
            "match_score": match_score,
            "verdict": "STRONG FIT — Recommend for immediate interview",
            "strengths": strengths,
            "minor_gaps": minor_gaps,
            "interview_prep": interview_prep,
            "recommendation": (
                f"Candidate matches {match_score}% of required skills. "
                f"Recommend proceeding to interview stage without requiring "
                f"additional upskilling. "
                + (f"Minor gaps in {', '.join(missing_skills[:2])} are learnable on the job."
                   if missing_skills else "No skill gaps identified.")
            ),
        }

        return AgentResult(
            success=True,
            data={"career_advice": report, "fast_tracked": True},
            confidence=0.95,
            message=f"Fast-tracked: {match_score}% match — interview readiness report generated",
        )

    def _input_snapshot(self, state):
        ms = state.get("match_score", 0)
        return f"Match score: {ms}%"
