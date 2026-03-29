"""
agents/base_agent.py  —  Abstract base for all agents in the agentic workflow.

Every agent:
  - Reports results with confidence scores
  - Has built-in retry logic with configurable max attempts
  - Logs every decision to the audit trail
  - Tracks execution time for SLA monitoring
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from audit_logger import AuditLogger


@dataclass
class AgentResult:
    """Standardized result from any agent execution."""
    success:     bool
    data:        Dict[str, Any]      = field(default_factory=dict)
    confidence:  float               = 1.0
    message:     str                 = ""
    duration_ms: float               = 0.0
    retries:     int                 = 0
    agent_name:  str                 = ""


class BaseAgent(ABC):
    """
    Abstract base agent with audit logging, retry logic, and SLA tracking.

    Subclasses must implement:
      - `name` property
      - `_execute(state, **kwargs) -> AgentResult`

    The base class handles:
      - Automatic audit logging (start, complete, fail)
      - Retry with configurable max_retries
      - SLA time tracking and breach logging
    """

    def __init__(self, audit: AuditLogger, config: Dict[str, Any] = None):
        self.audit  = audit
        self.config = config or {}
        self.max_retries:  int   = self.config.get("max_retries", 2)
        self.sla_budget_ms: float = self.config.get("sla_budget_ms", 30000)

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent display name for audit trail."""
        ...

    @abstractmethod
    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        """
        Core execution logic. Subclasses implement this.

        Args:
            state: Shared workflow state dict, accumulated by previous agents.
            **kwargs: Agent-specific parameters (e.g., retry mode flags).

        Returns:
            AgentResult with success status, output data, and confidence.
        """
        ...

    def run(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        """
        Execute the agent with retry logic, SLA tracking, and audit logging.

        This is the public interface — callers always use `agent.run(state)`.
        """
        input_snap = self._input_snapshot(state)
        self.audit.log_agent_start(self.name, input_snapshot=input_snap)

        last_error = ""
        for attempt in range(1, self.max_retries + 2):  # +1 for initial + retries
            t0 = time.time()
            try:
                result = self._execute(state, **kwargs)
                elapsed = (time.time() - t0) * 1000
                result.duration_ms = elapsed
                result.agent_name  = self.name
                result.retries     = attempt - 1

                # SLA check
                if elapsed > self.sla_budget_ms:
                    self.audit.log_sla_breach(self.name, elapsed, self.sla_budget_ms)
                elif elapsed > self.sla_budget_ms * 0.8:
                    self.audit.log_sla_warning(self.name, elapsed, self.sla_budget_ms)

                if result.success:
                    output_snap = self._output_snapshot(result)
                    self.audit.log_agent_complete(
                        self.name,
                        output_snapshot=output_snap,
                        confidence=result.confidence,
                        duration_ms=elapsed,
                    )
                    return result
                else:
                    last_error = result.message
                    if attempt <= self.max_retries:
                        self.audit.log_retry(self.name, attempt, result.message)
                        # Allow subclass to adjust kwargs for retry
                        kwargs = self._retry_kwargs(attempt, result, kwargs)
                    else:
                        break

            except Exception as e:
                elapsed = (time.time() - t0) * 1000
                last_error = str(e)
                if attempt <= self.max_retries:
                    self.audit.log_retry(self.name, attempt, str(e))
                    kwargs = self._retry_kwargs(attempt, None, kwargs)
                else:
                    self.audit.log_agent_fail(self.name, str(e), duration_ms=elapsed)
                    return AgentResult(
                        success=False, message=str(e),
                        duration_ms=elapsed, agent_name=self.name,
                        retries=attempt - 1,
                    )

        # All retries exhausted
        self.audit.log_agent_fail(self.name, f"All retries exhausted: {last_error}")
        return AgentResult(
            success=False, message=last_error,
            agent_name=self.name, retries=self.max_retries,
        )

    def _retry_kwargs(self, attempt: int, last_result: Optional[AgentResult],
                      current_kwargs: dict) -> dict:
        """
        Override in subclasses to modify kwargs between retry attempts.
        E.g., ExtractionAgent can relax the gate margin on retry.
        """
        return current_kwargs

    def _input_snapshot(self, state: Dict[str, Any]) -> str:
        """Override to customize what gets logged as input. Keep it short."""
        keys = list(state.keys())
        return f"State keys: {keys}"

    def _output_snapshot(self, result: AgentResult) -> str:
        """Override to customize what gets logged as output. Keep it short."""
        data_keys = list(result.data.keys()) if result.data else []
        return f"confidence={result.confidence:.2f}, keys={data_keys}"
