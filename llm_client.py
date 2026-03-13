"""
llm_client.py  –  Offline-first LLM integration for Career Copilot.

Operating modes (auto-selected):
────────────────────────────────
  Mode 1 │ Ollama  (richer quality, optional)
  ───────┼────────────────────────────────────────────────────────────────────
         │ Requires Ollama running locally: https://ollama.com
         │ Env vars (optional, these are the defaults):
         │   OLLAMA_BASE_URL=http://localhost:11434
         │   OLLAMA_MODEL=llama3.2
         │   OLLAMA_TIMEOUT=90
         │
  Mode 2 │ Template engine  (always available, zero dependencies)
  ───────┼────────────────────────────────────────────────────────────────────
         │ Generates structured career advice from the knowledge base and the
         │ actual skill gap data found in the analysis. No network, no model
         │ download, no API key.  Deterministic and fast.

Design goals
────────────
• Domain-agnostic: works for any JD / resume combination — not just tech
• No hardcoded skill names or domain assumptions in advice logic
• Both modes return the same dict schema so callers need no changes
• perform_full_gap_analysis() always returns None — the NLP pipeline
  (spaCy → SentenceTransformer → cosine similarity) handles gap analysis
  completely without an LLM
"""
from __future__ import annotations

import os
import json
import textwrap
from typing import List, Dict, Optional
from dataclasses import dataclass, field

from knowledge_base import get_skill_knowledge

# ── Ollama config ─────────────────────────────────────────────────────────────
_OLLAMA_URL     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
_OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "llama3.2")
_OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))


# ── Helpers ───────────────────────────────────────────────────────────────────
@dataclass
class SkillExtraction:
    technical_skills:     List[str] = field(default_factory=list)
    soft_skills:          List[str] = field(default_factory=list)
    tools_and_frameworks: List[str] = field(default_factory=list)
    domain_expertise:     List[str] = field(default_factory=list)


def _ollama_available() -> bool:
    """Quick liveness check — returns True only if Ollama responds within 3 s."""
    try:
        import urllib.request
        req = urllib.request.Request(f"{_OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


def _ollama_generate(prompt: str, system: str = "") -> str:
    """Call Ollama /api/generate (non-streaming). Pure stdlib."""
    import urllib.request

    payload: dict = {
        "model":  _OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 1200},
    }
    if system:
        payload["system"] = system

    data = json.dumps(payload).encode()
    req  = urllib.request.Request(
        f"{_OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=_OLLAMA_TIMEOUT) as resp:
        body = json.loads(resp.read())
        return body.get("response", "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# Template engine  (offline fallback)
# ─────────────────────────────────────────────────────────────────────────────
def _score_label(pct: float) -> str:
    if pct >= 80: return "strong"
    if pct >= 60: return "moderate"
    if pct >= 40: return "partial"
    return "low"


def _template_career_advice(
    matched_skills:  List[str],
    missing_skills:  List[str],
    skill_contexts:  List[Dict],
    job_description: str = "",
) -> Dict:
    """
    Generate structured career advice purely from the knowledge base
    and the actual skill gap data.

    Domain-agnostic: no assumptions about industry, role, or tech stack.
    """
    total     = len(matched_skills) + len(missing_skills)
    match_pct = round(len(matched_skills) / max(total, 1) * 100)
    label     = _score_label(match_pct)
    top_miss  = missing_skills[:5]
    top_match = matched_skills[:8]

    # ── Career summary ─────────────────────────────────────────────────────
    if match_pct >= 80:
        summary = (
            f"Your profile is an excellent match ({match_pct} %). "
            f"You already demonstrate {len(matched_skills)} of the required skills. "
            "Focus on the remaining gaps to make your application stand out."
        )
    elif match_pct >= 55:
        summary = (
            f"You have a {label} match ({match_pct} %) with {len(matched_skills)} "
            f"skills aligned. Closing the {len(missing_skills)} identified gaps "
            "over the next 2–4 months would make you a competitive candidate."
        )
    else:
        summary = (
            f"Your current profile has a {label} overlap ({match_pct} %) with this role. "
            f"Prioritise the top {min(len(missing_skills), 5)} missing skills below. "
            "A focused 3–6 month upskilling plan will significantly improve your readiness."
        )

    # ── Strengths ──────────────────────────────────────────────────────────
    strengths = [f"Proficient in {s}" for s in top_match[:5]]
    if len(matched_skills) > 5:
        strengths.append(
            f"Broad coverage across {len(matched_skills)} relevant skill areas"
        )

    # ── Priority skills ────────────────────────────────────────────────────
    ctx_map        = {c["skill"].lower(): c for c in skill_contexts}
    priority_skills = []

    for skill in top_miss:
        kb  = get_skill_knowledge(skill)
        ctx = ctx_map.get(skill.lower(), {})
        resources = ctx.get("learning_resources") or kb["learning_resources"]
        est_time  = ctx.get("estimated_time")      or kb["estimated_time"]

        priority_skills.append({
            "skill":    skill,
            "reason":   kb["description"],
            "timeline": est_time,
            "actions":  resources[:4],
        })

    # ── Recommended projects ───────────────────────────────────────────────
    recommended_projects = []
    seen: set = set()

    for skill in top_miss[:3]:
        kb = get_skill_knowledge(skill)
        for proj in kb["project_ideas"][:1]:
            if proj not in seen:
                seen.add(proj)
                recommended_projects.append({
                    "name":           proj[:60],
                    "description":    proj,
                    "intuition":      (
                        f"Hands-on practice is the fastest path to {skill} proficiency."
                    ),
                    "tech_stack":     skill,
                    "skills_covered": [skill],
                })

    # ── Career paths ───────────────────────────────────────────────────────
    all_paths: list = []
    for skill in top_miss[:3]:
        kb = get_skill_knowledge(skill)
        all_paths.extend(kb.get("career_paths", []))
    immediate   = sorted(set(all_paths[:4]))
    upskilled   = sorted({f"Senior {p}" for p in immediate[:3]})

    # ── 90-day plan ────────────────────────────────────────────────────────
    w1_skills = top_miss[:2]
    w2_skills = top_miss[2:4]

    def _learn_items(skills: List[str]) -> List[str]:
        items = []
        for s in skills:
            kb = get_skill_knowledge(s)
            items.append(f"Study {s}: {kb['learning_resources'][0]}")
        return items or [
            "Review the job description and map each requirement to your current profile"
        ]

    def _build_items(skills: List[str]) -> List[str]:
        items = []
        for s in skills:
            kb = get_skill_knowledge(s)
            if kb["project_ideas"]:
                items.append(f"Build: {kb['project_ideas'][0]}")
        return items or ["Integrate newly learned skills into a portfolio project"]

    action_plan = {
        "weeks_1_4": _learn_items(w1_skills) + [
            (
                f"Complete a focused course for: {', '.join(top_miss[:2])}"
                if top_miss
                else "Reinforce matched skills with advanced material"
            )
        ],
        "weeks_5_8": _build_items(w2_skills) + [
            "Document your work with a README and demo",
            "Push projects to a public repository",
        ],
        "weeks_9_12": [
            "Tailor your resume to mirror the exact language in this job description",
            "Prepare STAR-format stories for each matched skill",
            f"Practice explaining your approach to: {', '.join(top_miss[:3])}"
            if top_miss else "Practice explaining your strongest matched skills",
            "Run at least 2 mock interviews focusing on gap areas",
        ],
    }

    return {
        "career_summary":       summary,
        "strengths":            strengths,
        "priority_skills":      priority_skills,
        "recommended_projects": recommended_projects,
        "career_paths":         {
            "immediate":        immediate or [f"Roles matching {len(matched_skills)} of your skills"],
            "after_upskilling": upskilled or ["Senior positions in this domain"],
        },
        "action_plan": action_plan,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Ollama-powered career advice
# ─────────────────────────────────────────────────────────────────────────────
def _ollama_career_advice(
    matched_skills:  List[str],
    missing_skills:  List[str],
    skill_contexts:  List[Dict],
    job_description: str = "",
) -> Optional[Dict]:
    """
    Use local Ollama model to generate career advice.
    Returns None on any failure so the caller falls back to the template engine.
    """
    ctx_text = ""
    for ctx in skill_contexts[:4]:
        ctx_text += (
            f"\n{ctx['skill'].upper()}:\n"
            f"  Time: {ctx.get('estimated_time', 'varies')}\n"
            f"  Resources: {'; '.join(ctx.get('learning_resources', [])[:2])}\n"
        )

    prompt = textwrap.dedent(f"""
        You are a career coach. Analyse this skill gap and return ONLY valid JSON
        with no markdown fences or extra text.

        MATCHED SKILLS ({len(matched_skills)}): {', '.join(matched_skills[:12])}
        MISSING SKILLS ({len(missing_skills)}): {', '.join(missing_skills[:10])}
        JD EXCERPT: {job_description[:600]}
        SKILL CONTEXT: {ctx_text}

        Return JSON with exactly these keys:
        {{
          "career_summary": "2-3 sentence honest assessment",
          "strengths": ["strength1", "strength2", "strength3"],
          "priority_skills": [
            {{
              "skill": "name",
              "reason": "why important for this role",
              "timeline": "X weeks",
              "actions": ["step1", "step2", "step3"]
            }}
          ],
          "recommended_projects": [
            {{
              "name": "project name",
              "description": "what to build",
              "intuition": "why this helps",
              "tech_stack": "technologies used",
              "skills_covered": ["skill1"]
            }}
          ],
          "career_paths": {{
            "immediate": ["role1", "role2"],
            "after_upskilling": ["role3", "role4"]
          }},
          "action_plan": {{
            "weeks_1_4": ["item1", "item2"],
            "weeks_5_8": ["item1", "item2"],
            "weeks_9_12": ["item1", "item2"]
          }}
        }}
    """).strip()

    try:
        raw = _ollama_generate(
            prompt,
            system="Return only valid JSON with no markdown, no explanation, no preamble.",
        )
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        print(f"  Ollama career advice failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# LLMClient  (public interface)
# ─────────────────────────────────────────────────────────────────────────────
class LLMClient:
    """
    Offline-first LLM client.

    provider = "ollama"   → local Ollama model (auto-detected)
    provider = "offline"  → template engine (always available)

    Both providers return the same dict schema from generate_career_advice().
    """

    def __init__(self, provider: str = "auto"):
        if provider == "auto":
            self.provider = "ollama" if _ollama_available() else "offline"
        else:
            self.provider = provider

        if self.provider == "ollama":
            print(f"  LLM: Ollama ({_OLLAMA_MODEL}) at {_OLLAMA_URL}")
        else:
            print("  LLM: offline template engine (Ollama not detected)")

    def perform_full_gap_analysis(self, resume_text: str, jd_text: str) -> None:
        """
        Always returns None — the NLP pipeline handles gap analysis.
        Returning None signals api_server / app to use the pipeline directly.
        """
        return None

    def extract_skills(self, text: str) -> List[str]:
        """Legacy shim — used only if phrase_extracter is unavailable."""
        return []

    def generate_career_advice(
        self,
        matched_skills:  List[str],
        missing_skills:  List[str],
        skill_contexts:  List[Dict],
        job_description: str = "",
    ) -> Dict:
        """
        Generate structured career advice.
        Tries Ollama first (if available), then falls back to the template engine.
        Always succeeds — never raises.
        """
        if self.provider == "ollama":
            result = _ollama_career_advice(
                matched_skills, missing_skills, skill_contexts, job_description
            )
            if result:
                return result
            print("  Falling back to template engine.")

        return _template_career_advice(
            matched_skills, missing_skills, skill_contexts, job_description
        )


# ─────────────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────────────
def get_llm_client() -> LLMClient:
    """
    Always returns a working LLMClient — no API key needed.
    Uses Ollama if available on localhost:11434, otherwise the offline
    template engine. Never returns None.
    """
    return LLMClient(provider="auto")