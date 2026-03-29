"""
agent_orchestrator.py  —  Decision-graph orchestrator for the agentic workflow.

This is NOT a linear pipeline. The orchestrator makes routing decisions
at every stage based on the output of the previous agent:

  IngestionAgent → Decision(text quality?) → ExtractionAgent / OCR retry
  ExtractionAgent → Decision(skills found?) → AnalysisAgent / relaxed retry / escalate
  AnalysisAgent → Decision(match score?) → FastTrack / Strategy / Redirect
  StrategyAgent → ComplianceAgent → Decision(pass?) → Done / regenerate with constraints
  FastTrackAgent → ComplianceAgent → Done
  RedirectAgent → ComplianceAgent → Done

Every routing decision is logged to the audit trail with reasoning,
confidence, and alternatives considered — ensuring full auditability.
"""
from __future__ import annotations

import time
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass, field

from audit_logger import AuditLogger
from agents.base_agent import AgentResult
from agents.ingestion_agent import IngestionAgent
from agents.extraction_agent import ExtractionAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.compliance_agent import ComplianceAgent
from agents.fast_track_agent import FastTrackAgent
from agents.redirect_agent import RedirectAgent


@dataclass
class WorkflowState:
    """Mutable state that accumulates results as it flows through agents."""
    # Inputs
    pdf_bytes:      bytes  = b""
    jd_text:        str    = ""

    # Ingestion output
    resume_text:    str    = ""

    # Extraction output
    jd_skills:      list   = field(default_factory=list)
    resume_skills:  list   = field(default_factory=list)

    # Analysis output
    matched_skills:  list  = field(default_factory=list)
    missing_skills:  list  = field(default_factory=list)
    match_score:     float = 0.0
    per_skill_scores: dict = field(default_factory=dict)
    sim_matrix:      Any   = None

    # Strategy / FastTrack / Redirect output
    career_advice:   Optional[dict] = None
    fast_tracked:    bool  = False
    redirected:      bool  = False

    # Meta
    route_taken:     str   = ""
    compliance_pass: bool  = False

    def to_dict(self) -> dict:
        """Convert to dict for agent consumption (excludes binary data)."""
        d = {
            "jd_text":          self.jd_text,
            "resume_text":      self.resume_text,
            "jd_skills":        self.jd_skills,
            "resume_skills":    self.resume_skills,
            "matched_skills":   self.matched_skills,
            "missing_skills":   self.missing_skills,
            "match_score":      self.match_score,
            "per_skill_scores": self.per_skill_scores,
            "career_advice":    self.career_advice,
            "pdf_bytes":        self.pdf_bytes,
        }
        return d

    def to_result_dict(self) -> dict:
        """Final result compatible with the existing app.py/api_server.py format."""
        return {
            "resume_text":      self.resume_text,
            "jd_skills":        sorted(self.jd_skills),
            "resume_skills":    sorted(self.resume_skills),
            "matched_skills":   sorted(self.matched_skills),
            "missing_skills":   sorted(self.missing_skills),
            "match_score":      self.match_score,
            "per_skill_scores": self.per_skill_scores,
            "sim_matrix":       self.sim_matrix,
            "career_advice":    self.career_advice,
            "route_taken":      self.route_taken,
            "fast_tracked":     self.fast_tracked,
            "redirected":       self.redirected,
        }


# ── Threshold configuration ────────────────────────────────────────────────
# These control routing decisions. Loaded from config if available.

_DEFAULT_ROUTING_CONFIG = {
    "fast_track_threshold":  90.0,   # match score >= this → FastTrackAgent
    "redirect_threshold":    40.0,   # match score < this → RedirectAgent
    "max_compliance_retries": 2,     # max re-generations on compliance failure
    "agent_sla_budget_ms":   30000,  # per-agent time budget
}


def _load_routing_config() -> dict:
    """Load routing config from file if available, else use defaults."""
    import json
    import os
    config_path = os.path.join(os.path.dirname(__file__), "config", "thresholds.json")
    config = dict(_DEFAULT_ROUTING_CONFIG)
    if os.path.exists(config_path):
        try:
            with open(config_path, "r") as f:
                file_config = json.load(f)
            # Merge routing-specific keys
            for key in _DEFAULT_ROUTING_CONFIG:
                if key in file_config:
                    config[key] = file_config[key]
        except Exception:
            pass
    return config


class AgentOrchestrator:
    """
    Decision-graph orchestrator for the SkillBridge agentic workflow.

    Usage:
        orchestrator = AgentOrchestrator()
        result = orchestrator.run(pdf_bytes, jd_text)
        audit_trail = orchestrator.get_audit_trail()
    """

    def __init__(self, config: dict = None,
                 human_approval_callback: Optional[Callable] = None):
        """
        Args:
            config: Optional config dict overriding routing thresholds.
            human_approval_callback: Optional callable that receives
                (agent_name, state_summary) and returns True/False.
                If None, all gates auto-approve.
        """
        self.config = config or _load_routing_config()
        self.audit  = AuditLogger()
        self.human_callback = human_approval_callback

        # Agent config
        agent_cfg = {"sla_budget_ms": self.config.get("agent_sla_budget_ms", 30000)}

        # Initialize agents
        self._ingestion   = IngestionAgent(self.audit, agent_cfg)
        self._extraction  = ExtractionAgent(self.audit, agent_cfg)
        self._analysis    = AnalysisAgent(self.audit, agent_cfg)
        self._strategy    = StrategyAgent(self.audit, agent_cfg)
        self._compliance  = ComplianceAgent(self.audit, agent_cfg)
        self._fast_track  = FastTrackAgent(self.audit, agent_cfg)
        self._redirect    = RedirectAgent(self.audit, agent_cfg)

    # ── Main entry point ───────────────────────────────────────────────────

    def run(self, pdf_bytes: bytes, jd_text: str) -> dict:
        """
        Execute the full agentic workflow with conditional routing.

        Returns:
            Result dict compatible with the existing UI/API format,
            plus additional fields: route_taken, fast_tracked, redirected.
        """
        import time
        start_time = time.time()
        self.audit.log_agent_start("Orchestrator", input_snapshot=f"PDF {len(pdf_bytes)}b, JD {len(jd_text)} chars")

        state = WorkflowState(pdf_bytes=pdf_bytes, jd_text=jd_text)

        # ═══ STAGE 1: INGESTION ════════════════════════════════════════════
        result = self._run_ingestion(state)
        if not result.success:
            return self._error_result(state, "ingestion", result.message, start_time)

        state.resume_text = result.data["resume_text"]

        # ═══ STAGE 2: EXTRACTION ═══════════════════════════════════════════
        result = self._run_extraction(state)
        if not result.success:
            # Decision: can we recover?
            if result.data.get("needs_re_ingestion"):
                self.audit.log_routing(
                    "Orchestrator",
                    "Extraction failed for resume skills — routing back to Ingestion with alt parser",
                    reasoning="ExtractionAgent found 0 resume skills, may need re-ingestion",
                    alternatives=["Escalate to human", "Continue with JD skills only"],
                    confidence=0.6,
                )
                # Try re-ingestion with OCR
                re_result = self._ingestion.run(state.to_dict(), use_ocr=True)
                if re_result.success:
                    state.resume_text = re_result.data["resume_text"]
                    result = self._run_extraction(state)

            if not result.success:
                self.audit.log_escalation(
                    "Orchestrator",
                    f"Extraction failed after retries: {result.message}",
                )
                return self._error_result(state, "extraction", result.message, start_time)

        state.jd_skills     = result.data["jd_skills"]
        state.resume_skills = result.data["resume_skills"]

        # ═══ STAGE 3: ANALYSIS ═════════════════════════════════════════════
        result = self._run_analysis(state)
        if not result.success:
            return self._error_result(state, "analysis", result.message, start_time)

        state.matched_skills   = result.data["matched_skills"]
        state.missing_skills   = result.data["missing_skills"]
        state.match_score      = result.data["match_score"]
        state.per_skill_scores = result.data["per_skill_scores"]
        state.sim_matrix       = result.data.get("sim_matrix")

        # ═══ ROUTING DECISION: What happens next? ══════════════════════════
        route = self._decide_route(state, result.data.get("route_hint", "strategy"))
        state.route_taken = route

        # ═══ STAGE 4: ROUTE-SPECIFIC AGENT ═════════════════════════════════
        if route == "fast_track":
            advice_result = self._run_fast_track(state)
            state.fast_tracked = True
        elif route == "redirect":
            advice_result = self._run_redirect(state)
            state.redirected = True
        else:  # "strategy"
            # Human gate before strategy generation
            if not self._human_gate("strategy",
                                    f"Match score: {state.match_score}%. Generate upskilling plan?"):
                return self._error_result(state, "human_rejected",
                                          "Human rejected strategy generation", start_time)
            advice_result = self._run_strategy(state)

        if advice_result.success:
            state.career_advice = advice_result.data.get("career_advice")

        # ═══ STAGE 5: COMPLIANCE ═══════════════════════════════════════════
        compliance_result = self._run_compliance(state)

        if not compliance_result.success and route == "strategy":
            # Self-correction loop: regenerate with constraints
            constraints = compliance_result.data.get("constraints", [])
            for attempt in range(self.config.get("max_compliance_retries", 2)):
                self.audit.log_routing(
                    "Orchestrator",
                    f"Compliance failed — re-routing to StrategyAgent with {len(constraints)} constraints (attempt {attempt + 1})",
                    reasoning=f"Violations: {', '.join(compliance_result.data.get('violations', [])[:2])}",
                    alternatives=["Accept with warnings", "Escalate to human"],
                    confidence=0.7,
                )
                advice_result = self._strategy.run(
                    state.to_dict(),
                    compliance_constraints=constraints,
                )
                if advice_result.success:
                    state.career_advice = advice_result.data.get("career_advice")
                    compliance_result = self._run_compliance(state)
                    if compliance_result.success:
                        break

        state.compliance_pass = compliance_result.success

        self.audit.log_routing(
            "Orchestrator",
            f"Workflow complete — route: {route}, compliance: {'PASS' if state.compliance_pass else 'FAIL'}",
            confidence=0.95,
        )
        
        duration_ms = (time.time() - start_time) * 1000
        self.audit.log_agent_complete("Orchestrator", output_snapshot=f"Final decision: {route}", duration_ms=duration_ms)

        return state.to_result_dict()

    # ── Stage runners ──────────────────────────────────────────────────────

    def _run_ingestion(self, state: WorkflowState) -> AgentResult:
        return self._ingestion.run(state.to_dict())

    def _run_extraction(self, state: WorkflowState) -> AgentResult:
        return self._extraction.run(state.to_dict())

    def _run_analysis(self, state: WorkflowState) -> AgentResult:
        return self._analysis.run(state.to_dict())

    def _run_strategy(self, state: WorkflowState) -> AgentResult:
        return self._strategy.run(state.to_dict())

    def _run_compliance(self, state: WorkflowState) -> AgentResult:
        return self._compliance.run(state.to_dict())

    def _run_fast_track(self, state: WorkflowState) -> AgentResult:
        return self._fast_track.run(state.to_dict())

    def _run_redirect(self, state: WorkflowState) -> AgentResult:
        return self._redirect.run(state.to_dict())

    # ── Routing decisions ──────────────────────────────────────────────────

    def _decide_route(self, state: WorkflowState, hint: str) -> str:
        """
        CORE AGENTIC DECISION: determine which agent handles the candidate.

        This is where the system behaves as an agent, not a pipeline.
        The decision is based on the match score and logged with full reasoning.
        """
        score = state.match_score
        ft_thresh = self.config.get("fast_track_threshold", 90.0)
        rd_thresh = self.config.get("redirect_threshold", 40.0)

        if score >= ft_thresh:
            self.audit.log_routing(
                "Orchestrator",
                f"FAST TRACK: {score}% ≥ {ft_thresh}% threshold → skip StrategyAgent, route to FastTrackAgent",
                reasoning=(
                    f"Candidate matched {len(state.matched_skills)}/{len(state.jd_skills)} skills. "
                    f"An upskilling plan is unnecessary — generate interview readiness report instead."
                ),
                alternatives=[
                    f"Route to StrategyAgent (standard path)",
                    f"Route to RedirectAgent (threshold: <{rd_thresh}%)",
                ],
                confidence=0.95,
            )
            return "fast_track"

        elif score < rd_thresh:
            # Check if the candidate has enough matched skills to be salvageable
            salvageable = len(state.matched_skills) >= 3

            if salvageable:
                self.audit.log_routing(
                    "Orchestrator",
                    f"LOW MATCH but SALVAGEABLE: {score}% < {rd_thresh}% but {len(state.matched_skills)} "
                    f"skills matched → route to StrategyAgent with intensive plan",
                    reasoning=(
                        f"Despite low overall score, candidate has {len(state.matched_skills)} "
                        f"relevant skills. A focused upskilling plan could bridge the gap."
                    ),
                    alternatives=[
                        f"Route to RedirectAgent (suggest alternative roles)",
                        f"Escalate to human for decision",
                    ],
                    confidence=0.7,
                )
                return "strategy"
            else:
                self.audit.log_routing(
                    "Orchestrator",
                    f"REDIRECT: {score}% < {rd_thresh}% with only {len(state.matched_skills)} "
                    f"matched skills → route to RedirectAgent",
                    reasoning=(
                        f"Candidate fundamentally misaligned with target role. "
                        f"Only {len(state.matched_skills)} of {len(state.jd_skills)} skills match. "
                        f"Better to suggest alternative career paths."
                    ),
                    alternatives=[
                        f"Route to StrategyAgent (force upskilling plan)",
                        f"Escalate to human",
                    ],
                    confidence=0.85,
                )
                return "redirect"

        else:
            self.audit.log_routing(
                "Orchestrator",
                f"STANDARD: {score}% is in [{rd_thresh}%–{ft_thresh}%) → route to StrategyAgent",
                reasoning=(
                    f"Candidate has {len(state.matched_skills)} matched and "
                    f"{len(state.missing_skills)} missing skills. "
                    f"Standard upskilling and career strategy is appropriate."
                ),
                alternatives=[
                    f"Route to FastTrackAgent (threshold: ≥{ft_thresh}%)",
                    f"Route to RedirectAgent (threshold: <{rd_thresh}%)",
                ],
                confidence=0.9,
            )
            return "strategy"

    # ── Human-in-the-loop ──────────────────────────────────────────────────

    def _human_gate(self, gate_name: str, summary: str) -> bool:
        """
        Check with human (if callback is set) before proceeding.
        If no callback, auto-approve.
        """
        self.audit.log_human_gate(
            "Orchestrator",
            f"Human gate '{gate_name}': {summary}",
        )

        if self.human_callback:
            approved = self.human_callback(gate_name, summary)
            self.audit.log_human_decision("Orchestrator", approved)
            return approved

        # Auto-approve if no callback
        self.audit.log_human_decision("Orchestrator", True, "Auto-approved (no callback)")
        return True

    # ── Error handling ─────────────────────────────────────────────────────

    def _error_result(self, state: WorkflowState, stage: str, message: str, start_time: float = None) -> dict:
        """Build a result dict for error cases and log orchestrator failure."""
        if start_time is not None:
            import time
            duration_ms = (time.time() - start_time) * 1000
            self.audit.log_agent_fail("Orchestrator", error=f"Failed at {stage}: {message}", duration_ms=duration_ms)
            
        result = state.to_result_dict()
        result["error"]       = True
        result["error_stage"] = stage
        result["error_message"] = message
        return result

    # ── Audit access ───────────────────────────────────────────────────────

    def get_audit_trail(self) -> str:
        """Human-readable audit trail."""
        return self.audit.to_summary()

    def get_audit_json(self) -> str:
        """Machine-readable audit trail."""
        return self.audit.to_json()

    def get_agent_stats(self) -> dict:
        """Per-agent status for dashboard."""
        return self.audit.get_agent_stats()


# ── Convenience function (drop-in replacement for pipeline.run_analysis) ───

def run_agentic_analysis(pdf_bytes: bytes, jd_text: str,
                         config: dict = None) -> dict:
    """
    Drop-in replacement for pipeline.run_analysis() that uses the
    agentic orchestrator with conditional routing.

    Returns the same result format, plus:
      - route_taken: "strategy" | "fast_track" | "redirect"
      - fast_tracked: bool
      - redirected: bool
      - career_advice: dict (if applicable)
    """
    orchestrator = AgentOrchestrator(config=config)
    result = orchestrator.run(pdf_bytes, jd_text)
    result["audit_trail"]  = orchestrator.get_audit_trail()
    result["audit_json"]   = orchestrator.get_audit_json()
    result["agent_stats"]  = orchestrator.get_agent_stats()
    return result
