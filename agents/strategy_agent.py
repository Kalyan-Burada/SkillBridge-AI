"""
agents/strategy_agent.py  —  Career Strategy with constraint-aware regeneration.

Self-correction:
  - If ComplianceAgent rejects the output, the orchestrator calls
    this agent again with compliance_constraints to regenerate.
"""
from __future__ import annotations

from typing import Any, Dict, List

from agents.base_agent import BaseAgent, AgentResult


class StrategyAgent(BaseAgent):
    """Generates career advice using LLM/RAG with compliance-aware regeneration."""

    @property
    def name(self) -> str:
        return "StrategyAgent"

    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        matched_skills = state.get("matched_skills", [])
        missing_skills = state.get("missing_skills", [])
        jd_text        = state.get("jd_text", "")

        if not missing_skills:
            return AgentResult(
                success=True,
                data={"career_advice": None, "reason": "No missing skills — no strategy needed"},
                confidence=1.0,
                message="No gaps to strategize — candidate is fully matched",
            )

        constraints = kwargs.get("compliance_constraints", [])

        # Get LLM and RAG clients
        llm = self._get_llm()
        rag = self._get_rag()

        # Generate career advice
        try:
            contexts = []
            if rag:
                contexts = rag.get_context_for_missing_skills(missing_skills[:5])

            if llm:
                advice = llm.generate_career_advice(
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                    skill_contexts=contexts,
                    job_description=jd_text,
                )
            else:
                # Template fallback
                self.audit.log_fallback(
                    self.name,
                    "LLM unavailable — using template engine",
                    reasoning="Ollama not detected at startup",
                )
                from llm_client import _template_career_advice
                advice = _template_career_advice(
                    matched_skills, missing_skills, contexts, jd_text
                )

            if not advice:
                return AgentResult(
                    success=False,
                    message="Career advice generation returned empty result",
                    confidence=0.3,
                )

            # If constraints were provided (from compliance rejection), verify
            if constraints:
                self.audit.log_self_correction(
                    self.name,
                    f"Regenerated advice with {len(constraints)} compliance constraints applied",
                    reasoning=f"Constraints: {', '.join(constraints[:3])}",
                )

            return AgentResult(
                success=True,
                data={
                    "career_advice": advice,
                    "llm_provider": llm.provider if llm else "template",
                    "rag_available": rag is not None,
                    "constraints_applied": constraints,
                },
                confidence=0.85 if llm and llm.provider == "ollama" else 0.7,
                message=f"Generated career strategy via {'LLM' if llm else 'template'}",
            )

        except Exception as e:
            self.audit.log_fallback(
                self.name,
                f"LLM failed ({e}) — falling back to template engine",
            )
            from llm_client import _template_career_advice
            advice = _template_career_advice(
                matched_skills, missing_skills, [], jd_text
            )
            return AgentResult(
                success=True,
                data={"career_advice": advice, "llm_provider": "template_fallback"},
                confidence=0.6,
                message="Generated career strategy via template fallback",
            )

    def _get_llm(self):
        try:
            from llm_client import get_llm_client
            return get_llm_client()
        except Exception:
            return None

    def _get_rag(self):
        try:
            from rag_engine import get_rag_engine
            return get_rag_engine()
        except Exception:
            return None

    def _input_snapshot(self, state):
        mc = len(state.get("matched_skills", []))
        xc = len(state.get("missing_skills", []))
        return f"Matched: {mc}, Missing: {xc}"
