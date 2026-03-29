"""
audit_logger.py  —  Centralized audit trail for the agentic workflow.

Every agent decision, routing choice, self-correction, and human override
is logged with full context. The audit trail is the backbone of the
hackathon's "auditability" requirement.

Outputs:
  - Structured list of AuditEntry objects (queryable in-memory)
  - JSON export for persistence
  - Human-readable summary for UI display
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class DecisionType(str, Enum):
    AGENT_START       = "agent_start"
    AGENT_COMPLETE    = "agent_complete"
    AGENT_FAIL        = "agent_fail"
    ROUTING_DECISION  = "routing_decision"
    SELF_CORRECTION   = "self_correction"
    RETRY             = "retry"
    FALLBACK          = "fallback"
    HUMAN_GATE        = "human_gate"
    HUMAN_APPROVED    = "human_approved"
    HUMAN_REJECTED    = "human_rejected"
    SLA_WARNING       = "sla_warning"
    SLA_BREACH        = "sla_breach"
    SKIP              = "skip"
    ESCALATION        = "escalation"


@dataclass
class AuditEntry:
    """Single auditable event in the workflow."""
    entry_id:       str
    timestamp:      float
    agent_name:     str
    decision_type:  str
    summary:        str
    confidence:     float              = 0.0
    input_snapshot: Optional[str]      = None
    output_snapshot: Optional[str]     = None
    reasoning:      Optional[str]      = None
    alternatives:   Optional[List[str]] = None
    duration_ms:    Optional[float]    = None
    metadata:       Dict[str, Any]     = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


class AuditLogger:
    """
    Append-only audit log for a single workflow session.

    Usage:
        logger = AuditLogger()
        logger.log_agent_start("IngestionAgent", input_snapshot="resume.pdf (42KB)")
        logger.log_agent_complete("IngestionAgent", output_snapshot="3200 chars extracted", confidence=0.95)
        logger.log_routing("Orchestrator", "Text quality OK (3200 chars) → route to ExtractionAgent",
                          alternatives=["Retry OCR", "Reject PDF"])
    """

    def __init__(self, session_id: Optional[str] = None):
        self.session_id: str       = session_id or str(uuid.uuid4())[:8]
        self.entries: List[AuditEntry] = []
        self._start_time: float    = time.time()

    # ── Core logging ───────────────────────────────────────────────────────

    def _add(self, agent: str, dtype: DecisionType, summary: str, **kwargs) -> AuditEntry:
        entry = AuditEntry(
            entry_id=f"{self.session_id}-{len(self.entries):03d}",
            timestamp=time.time(),
            agent_name=agent,
            decision_type=dtype.value,
            summary=summary,
            **kwargs,
        )
        self.entries.append(entry)
        return entry

    # ── Convenience methods ────────────────────────────────────────────────

    def log_agent_start(self, agent: str, input_snapshot: str = "") -> AuditEntry:
        return self._add(agent, DecisionType.AGENT_START,
                         f"{agent} started processing",
                         input_snapshot=input_snapshot)

    def log_agent_complete(self, agent: str, output_snapshot: str = "",
                           confidence: float = 1.0, duration_ms: float = 0.0) -> AuditEntry:
        return self._add(agent, DecisionType.AGENT_COMPLETE,
                         f"{agent} completed successfully",
                         output_snapshot=output_snapshot,
                         confidence=confidence,
                         duration_ms=duration_ms)

    def log_agent_fail(self, agent: str, error: str, duration_ms: float = 0.0) -> AuditEntry:
        return self._add(agent, DecisionType.AGENT_FAIL,
                         f"{agent} failed: {error}",
                         duration_ms=duration_ms)

    def log_routing(self, agent: str, summary: str,
                    reasoning: str = "", alternatives: list = None,
                    confidence: float = 1.0) -> AuditEntry:
        return self._add(agent, DecisionType.ROUTING_DECISION,
                         summary, reasoning=reasoning,
                         alternatives=alternatives or [],
                         confidence=confidence)

    def log_self_correction(self, agent: str, summary: str,
                            reasoning: str = "") -> AuditEntry:
        return self._add(agent, DecisionType.SELF_CORRECTION,
                         summary, reasoning=reasoning)

    def log_retry(self, agent: str, attempt: int, reason: str) -> AuditEntry:
        return self._add(agent, DecisionType.RETRY,
                         f"{agent} retry #{attempt}: {reason}")

    def log_fallback(self, agent: str, summary: str, reasoning: str = "") -> AuditEntry:
        return self._add(agent, DecisionType.FALLBACK,
                         summary, reasoning=reasoning)

    def log_human_gate(self, agent: str, summary: str) -> AuditEntry:
        return self._add(agent, DecisionType.HUMAN_GATE, summary)

    def log_human_decision(self, agent: str, approved: bool, notes: str = "") -> AuditEntry:
        dtype = DecisionType.HUMAN_APPROVED if approved else DecisionType.HUMAN_REJECTED
        return self._add(agent, dtype,
                         f"Human {'approved' if approved else 'rejected'}: {notes}")

    def log_skip(self, agent: str, reason: str) -> AuditEntry:
        return self._add(agent, DecisionType.SKIP,
                         f"{agent} skipped: {reason}")

    def log_sla_warning(self, agent: str, elapsed_ms: float, budget_ms: float) -> AuditEntry:
        return self._add(agent, DecisionType.SLA_WARNING,
                         f"{agent} approaching SLA: {elapsed_ms:.0f}ms / {budget_ms:.0f}ms budget",
                         duration_ms=elapsed_ms)

    def log_sla_breach(self, agent: str, elapsed_ms: float, budget_ms: float) -> AuditEntry:
        return self._add(agent, DecisionType.SLA_BREACH,
                         f"{agent} SLA breach: {elapsed_ms:.0f}ms exceeded {budget_ms:.0f}ms budget",
                         duration_ms=elapsed_ms)

    def log_escalation(self, agent: str, reason: str) -> AuditEntry:
        return self._add(agent, DecisionType.ESCALATION,
                         f"Escalated to human: {reason}")

    # ── Export ─────────────────────────────────────────────────────────────

    def to_json(self) -> str:
        return json.dumps({
            "session_id": self.session_id,
            "total_entries": len(self.entries),
            "total_duration_ms": (time.time() - self._start_time) * 1000,
            "entries": [e.to_dict() for e in self.entries],
        }, indent=2, default=str)

    def to_summary(self) -> str:
        """Human-readable summary for UI display."""
        lines = [f"═══ Audit Trail ═══  Session: {self.session_id}\n"]
        for e in self.entries:
            ts = time.strftime("%H:%M:%S", time.localtime(e.timestamp))
            icon = {
                "agent_start": "▶",  "agent_complete": "✓",  "agent_fail": "✗",
                "routing_decision": "⇒", "self_correction": "↺", "retry": "↻",
                "fallback": "⤵", "human_gate": "⏸", "human_approved": "👍",
                "human_rejected": "👎", "sla_warning": "⚠", "sla_breach": "🚨",
                "skip": "⏭", "escalation": "⬆",
            }.get(e.decision_type, "·")

            line = f"  {ts}  {icon} [{e.agent_name:20s}] {e.summary}"
            if e.reasoning:
                line += f"\n{'':>30}Reason: {e.reasoning}"
            if e.alternatives:
                line += f"\n{'':>30}Alternatives: {', '.join(e.alternatives)}"
            if e.confidence and e.decision_type == "routing_decision":
                line += f"  (confidence: {e.confidence:.0%})"
            if e.duration_ms and e.duration_ms > 0:
                line += f"  [{e.duration_ms:.0f}ms]"
            lines.append(line)

        total_ms = (time.time() - self._start_time) * 1000
        lines.append(f"\n  Total: {len(self.entries)} decisions  |  {total_ms:.0f}ms elapsed")
        return "\n".join(lines)

    def get_agent_stats(self) -> Dict[str, dict]:
        """Per-agent statistics for the dashboard."""
        stats: Dict[str, dict] = {}
        for e in self.entries:
            name = e.agent_name
            if name not in stats:
                stats[name] = {"status": "pending", "decisions": 0, "duration_ms": 0, "errors": 0}
            stats[name]["decisions"] += 1
            if e.duration_ms:
                stats[name]["duration_ms"] += e.duration_ms
            if e.decision_type == "agent_complete":
                stats[name]["status"] = "complete"
            elif e.decision_type == "agent_fail":
                stats[name]["status"] = "failed"
                stats[name]["errors"] += 1
            elif e.decision_type == "agent_start":
                stats[name]["status"] = "running"
        return stats
