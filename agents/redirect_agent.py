"""
agents/redirect_agent.py  —  Low-match candidate handler.

When match score < 40%, the orchestrator routes here to suggest
alternative roles the candidate IS suited for, based on their
existing skills and the knowledge base career paths.
"""
from __future__ import annotations

from typing import Any, Dict, List

from agents.base_agent import BaseAgent, AgentResult


class RedirectAgent(BaseAgent):
    """Suggests alternative career paths for low-match candidates (<40%)."""

    @property
    def name(self) -> str:
        return "RedirectAgent"

    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        matched_skills = state.get("matched_skills", [])
        missing_skills = state.get("missing_skills", [])
        match_score    = state.get("match_score", 0.0)

        from knowledge_base import get_skill_knowledge
        from collections import Counter

        # Collect career paths from the candidate's MATCHED skills
        # (these are the roles they ARE suited for)
        role_counter: Counter = Counter()
        skill_to_roles: Dict[str, List[str]] = {}

        for skill in matched_skills:
            kb = get_skill_knowledge(skill)
            paths = kb.get("career_paths", [])
            # Filter out generic defaults
            real_paths = [p for p in paths
                         if p != "Specialist and senior roles in this domain"]
            if real_paths:
                skill_to_roles[skill] = real_paths
                for role in real_paths:
                    role_counter[role.strip()] += 1

        # Top alternative roles ranked by how many matched skills support them
        alt_roles = []
        for role, count in role_counter.most_common(6):
            supporting_skills = [s for s, roles in skill_to_roles.items()
                                 if role in roles]
            alt_roles.append({
                "role": role,
                "supporting_skills": supporting_skills[:5],
                "skill_coverage": count,
                "recommendation": (
                    f"Your skills in {', '.join(supporting_skills[:3])} "
                    f"align well with a {role} position."
                ),
            })

        # Build transition plan
        transition_skills = []
        if alt_roles:
            # For the top alternative role, what ADDITIONAL skills would help?
            top_role = alt_roles[0]["role"]
            # Use matched skills as the base, suggest deepening
            for skill in matched_skills[:3]:
                kb = get_skill_knowledge(skill)
                resources = kb.get("learning_resources", [])
                if resources and resources[0] != "Search for dedicated courses on Coursera, Udemy, or LinkedIn Learning":
                    transition_skills.append({
                        "skill": skill,
                        "action": f"Deepen expertise: {resources[0]}",
                    })

        report = {
            "report_type": "career_redirect",
            "match_score": match_score,
            "verdict": "MISALIGNED — Candidate better suited for alternative roles",
            "current_match_summary": (
                f"Only {match_score}% match with the target role. "
                f"The candidate possesses {len(matched_skills)} relevant skills "
                f"but is missing {len(missing_skills)} critical requirements."
            ),
            "alternative_roles": alt_roles,
            "transition_plan": transition_skills,
            "recommendation": (
                f"Rather than pursuing significant upskilling for this role, "
                f"consider these better-aligned positions: "
                + ", ".join(r["role"] for r in alt_roles[:3])
                if alt_roles else
                "Consider broader career exploration based on foundational skills."
            ),
        }

        return AgentResult(
            success=True,
            data={"career_advice": report, "redirected": True},
            confidence=0.85,
            message=f"Redirected: {match_score}% match — {len(alt_roles)} alternative roles suggested",
        )

    def _input_snapshot(self, state):
        ms = state.get("match_score", 0)
        mc = len(state.get("matched_skills", []))
        return f"Match: {ms}%, Matched skills: {mc}"
