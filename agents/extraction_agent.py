"""
agents/extraction_agent.py  —  Skill Extraction with relaxed-gate retry.

Self-correction:
  - Primary: extract with default semantic gate margin (-0.05)
  - On 0 skills: retry with relaxed margin (-0.15) — broader acceptance
  - If still 0: report failure for orchestrator to escalate
"""
from __future__ import annotations

from typing import Any, Dict

from agents.base_agent import BaseAgent, AgentResult


class ExtractionAgent(BaseAgent):
    """Extracts skills from text using the pipeline's NLP + semantic gate."""

    @property
    def name(self) -> str:
        return "ExtractionAgent"

    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        resume_text = state.get("resume_text", "")
        jd_text     = state.get("jd_text", "")
        relaxed     = kwargs.get("relaxed_gate", False)

        if not jd_text.strip():
            return AgentResult(success=False, message="No job description provided")

        from pipeline import extract_skills, _GATE_MARGIN
        import pipeline

        # Self-correction: relax the semantic gate on retry
        original_margin = pipeline._GATE_MARGIN
        if relaxed:
            pipeline._GATE_MARGIN = -0.15
            self.audit.log_self_correction(
                self.name,
                f"Relaxing semantic gate margin from {original_margin} to -0.15",
                reasoning="First extraction returned 0 skills — broadening acceptance threshold",
            )

        try:
            jd_skills     = extract_skills(jd_text)
            resume_skills = extract_skills(resume_text) if resume_text else []
        finally:
            # Always restore original margin
            pipeline._GATE_MARGIN = original_margin

        # Validate
        if not jd_skills:
            if not relaxed:
                return AgentResult(
                    success=False,
                    message="No skills extracted from job description",
                    confidence=0.2,
                    data={"jd_skills": [], "resume_skills": resume_skills, "needs_relaxed_gate": True},
                )
            else:
                return AgentResult(
                    success=False,
                    message="No skills found in JD even with relaxed gate — JD may not contain extractable skills",
                    confidence=0.0,
                    data={"jd_skills": [], "resume_skills": resume_skills},
                )

        if not resume_skills and resume_text:
            return AgentResult(
                success=False,
                message="No skills extracted from resume — document may need re-ingestion",
                confidence=0.2,
                data={
                    "jd_skills": jd_skills,
                    "resume_skills": [],
                    "needs_re_ingestion": True,
                },
            )

        confidence = 0.9
        if relaxed:
            confidence = 0.7  # lower confidence with relaxed gate
        if len(jd_skills) < 3:
            confidence -= 0.1
        if len(resume_skills) < 3:
            confidence -= 0.1

        return AgentResult(
            success=True,
            data={
                "jd_skills": sorted(jd_skills),
                "resume_skills": sorted(resume_skills),
                "jd_count": len(jd_skills),
                "resume_count": len(resume_skills),
                "gate_mode": "relaxed" if relaxed else "standard",
            },
            confidence=max(confidence, 0.3),
            message=f"Extracted {len(jd_skills)} JD skills, {len(resume_skills)} resume skills",
        )

    def _retry_kwargs(self, attempt, last_result, current_kwargs):
        """On retry, relax the semantic gate."""
        if last_result and last_result.data.get("needs_relaxed_gate"):
            return {**current_kwargs, "relaxed_gate": True}
        return {**current_kwargs, "relaxed_gate": True}

    def _input_snapshot(self, state):
        jd_len  = len(state.get("jd_text", ""))
        res_len = len(state.get("resume_text", ""))
        return f"JD: {jd_len} chars, Resume: {res_len} chars"

    def _output_snapshot(self, result):
        jc = result.data.get("jd_count", 0)
        rc = result.data.get("resume_count", 0)
        gm = result.data.get("gate_mode", "standard")
        return f"JD: {jc} skills, Resume: {rc} skills [{gm} gate]"
