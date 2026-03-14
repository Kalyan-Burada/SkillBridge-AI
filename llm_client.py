"""
llm_client.py  —  Offline-first LLM integration for Career Copilot.

FIXES IN THIS VERSION
═════════════════════
FIX-1  Career paths showing generic "Specialist and senior roles in this domain"
       The template engine only pulled career paths from the top 3 MISSING skills.
       If those skills aren't in the KB (e.g. "data scientist", "cloud platforms"),
       they fall through to the "default" entry which has the generic text.
       FIX: Collect career paths from BOTH matched AND missing skills, preferring
       KB-specific entries over the default fallback. Deduplicate and rank by
       frequency so the most relevant roles appear first.

Operating modes (auto-selected):
────────────────────────────────
  Mode 1 │ Ollama  (richer quality, optional)
  Mode 2 │ Template engine  (always available, zero dependencies)
"""
from __future__ import annotations
import os
import json
import textwrap
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from knowledge_base import get_skill_knowledge

_OLLAMA_URL     = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
_OLLAMA_MODEL   = os.getenv("OLLAMA_MODEL", "llama3.2")
_OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "90"))

_DEFAULT_ENTRY_DESC = "Specialist and senior roles in this domain"  # sentinel


@dataclass
class SkillExtraction:
    technical_skills:     List[str] = field(default_factory=list)
    soft_skills:          List[str] = field(default_factory=list)
    tools_and_frameworks: List[str] = field(default_factory=list)
    domain_expertise:     List[str] = field(default_factory=list)


def _ollama_available() -> bool:
    try:
        import urllib.request
        req = urllib.request.Request(f"{_OLLAMA_URL}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=3):
            return True
    except Exception:
        return False


def _ollama_generate(prompt: str, system: str = "") -> str:
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


def _score_label(pct: float) -> str:
    if pct >= 80: return "strong"
    if pct >= 60: return "moderate"
    if pct >= 40: return "partial"
    return "low"

# Sentinel: first learning resource of the generic "default" KB entry.
# Any skill whose KB lookup returns this string has no real KB entry.
_GENERIC_KB_SENTINEL = "Search for dedicated courses on Coursera, Udemy, or LinkedIn Learning"


def _collect_career_paths(
    matched_skills: List[str],
    missing_skills: List[str],
) -> Dict[str, list]:
    """
    Collect career path suggestions from the knowledge base by scanning
    BOTH matched and missing skills.

    Strategy:
      1. For each skill, get its KB entry's career_paths list.
      2. Skip entries that fall back to the generic default sentinel.
      3. Count how many skills point to each role → rank by frequency.
      4. Return top roles for immediate + senior variants for after-upskilling.
    """
    from collections import Counter

    role_counter: Counter = Counter()
    all_skills   = matched_skills[:8] + missing_skills[:5]

    for skill in all_skills:
        kb    = get_skill_knowledge(skill)
        paths = kb.get("career_paths", [])
        # Skip if it's the generic default
        if not paths or paths == ["Specialist and senior roles in this domain"]:
            continue
        for role in paths:
            role_stripped = role.strip()
            if role_stripped and role_stripped != _DEFAULT_ENTRY_DESC:
                role_counter[role_stripped] += 1

    # If we still have nothing meaningful, widen the net to all matched skills
    if not role_counter:
        for skill in matched_skills:
            kb    = get_skill_knowledge(skill)
            paths = kb.get("career_paths", [])
            for role in paths:
                role_stripped = role.strip()
                if role_stripped and role_stripped != _DEFAULT_ENTRY_DESC:
                    role_counter[role_stripped] += 1

    # Top roles by frequency, break ties alphabetically
    top_roles = [r for r, _ in role_counter.most_common(6)]

    if not top_roles:
        # Last resort: derive from the matched skill names themselves
        top_roles = [f"{s.title()} Specialist" for s in matched_skills[:3]]

    immediate         = top_roles[:4]
    after_upskilling  = [
        f"Senior {r}" if not r.lower().startswith("senior") else r
        for r in top_roles[:3]
    ]

    return {
        "immediate":        immediate,
        "after_upskilling": after_upskilling,
    }


def _template_career_advice(
    matched_skills:  List[str],
    missing_skills:  List[str],
    skill_contexts:  List[Dict],
    job_description: str = "",
) -> Dict:
    total     = len(matched_skills) + len(missing_skills)
    match_pct = round(len(matched_skills) / max(total, 1) * 100)
    label     = _score_label(match_pct)

    top_miss  = missing_skills[:5]
    top_match = matched_skills[:8]

    # ── Career summary
    if match_pct >= 80:
        summary = (
            f"Your profile is an excellent match ({match_pct}%). "
            f"You already demonstrate {len(matched_skills)} of the required skills. "
            "Focus on the remaining gaps to make your application stand out."
        )
    elif match_pct >= 55:
        summary = (
            f"You have a {label} match ({match_pct}%) with {len(matched_skills)} "
            f"skills aligned. Closing the {len(missing_skills)} identified gaps "
            "over the next 2–4 months would make you a competitive candidate."
        )
    else:
        summary = (
            f"Your current profile has a {label} overlap ({match_pct}%) with this role. "
            f"Prioritise the top {min(len(missing_skills), 5)} missing skills below. "
            "A focused 3–6 month upskilling plan will significantly improve your readiness."
        )

    # ── Strengths
    strengths = [f"Proficient in {s}" for s in top_match[:5]]
    if len(matched_skills) > 5:
        strengths.append(
            f"Broad coverage across {len(matched_skills)} relevant skill areas"
        )

    # ── Priority skills — only show skills with real KB entries
    ctx_map        = {c["skill"].lower(): c for c in skill_contexts}
    priority_skills = []
    for skill in top_miss:
        kb        = get_skill_knowledge(skill)
        resources = kb.get("learning_resources", [])
        # Skip skills that fell through to the generic default
        if not resources or resources[0] == _GENERIC_KB_SENTINEL:
            continue
        ctx      = ctx_map.get(skill.lower(), {})
        resources = ctx.get("learning_resources") or kb["learning_resources"]
        est_time  = ctx.get("estimated_time")      or kb["estimated_time"]
        priority_skills.append({
            "skill":    skill,
            "reason":   kb["description"],
            "timeline": est_time,
            "actions":  resources[:4],
        })

    # ── Recommended projects — only for skills with real KB entries
    recommended_projects = []
    seen: set = set()
    for skill in top_miss[:3]:
        kb = get_skill_knowledge(skill)
        resources = kb.get("learning_resources", [])
        if not resources or resources[0] == _GENERIC_KB_SENTINEL:
            continue
        for proj in kb["project_ideas"][:1]:
            if proj not in seen:
                seen.add(proj)
                recommended_projects.append({
                    "name":           proj[:60],
                    "description":    proj,
                    "intuition":      f"Hands-on practice is the fastest path to {skill} proficiency.",
                    "tech_stack":     skill,
                    "skills_covered": [skill],
                })

    # ── Career paths (fixed: uses both matched + missing, skips generic default)
    career_paths = _collect_career_paths(matched_skills, missing_skills)

    # ── 90-day plan (domain-aware, filters out skills with no KB entry)

    def _has_real_kb(skill: str) -> bool:
        """Return True if the skill has a specific KB entry, not the generic default."""
        kb = get_skill_knowledge(skill)
        resources = kb.get("learning_resources", [])
        return bool(resources) and resources[0] != _GENERIC_KB_SENTINEL

    def _skill_label(skill: str) -> str:
        """Title-case the skill for display, handling multi-word phrases."""
        return skill.title()

    # Filter missing skills to only those with real KB entries
    real_missing = [s for s in top_miss if _has_real_kb(s)]
    # If filtering removed everything, fall back to the raw list but cap at 3
    if not real_missing:
        real_missing = top_miss[:3]

    # Infer domain from matched skills that have real KB entries
    domain_skills = [s for s in matched_skills if _has_real_kb(s)]

    # ── Weeks 1-4: Learn the top 2 missing skills with specific resources
    weeks_1_4 = []
    for skill in real_missing[:2]:
        kb        = get_skill_knowledge(skill)
        ctx       = ctx_map.get(skill.lower(), {})
        resources = ctx.get("learning_resources") or kb["learning_resources"]
        est_time  = ctx.get("estimated_time") or kb.get("estimated_time", "")
        # Pick the most actionable first resource
        resource = resources[0] if resources else f"Find a course on {skill}"
        time_str  = f" (~{est_time})" if est_time else ""
        weeks_1_4.append(f"Learn **{_skill_label(skill)}**{time_str}: {resource}")
    # Add a consolidation task using domain context
    if domain_skills:
        domain_str = ", ".join(_skill_label(s) for s in domain_skills[:3])
        weeks_1_4.append(
            f"Review fundamentals connecting your existing strengths "
            f"({domain_str}) to the new skills you're learning"
        )
    elif real_missing:
        weeks_1_4.append(
            f"Complete at least one hands-on exercise for each new skill: "
            + ", ".join(_skill_label(s) for s in real_missing[:2])
        )

    # ── Weeks 5-8: Build projects using the missing skills
    weeks_5_8 = []
    seen_projs: set = set()
    for skill in real_missing[:3]:
        kb = get_skill_knowledge(skill)
        projects = kb.get("project_ideas", [])
        for proj in projects[:1]:
            if proj and proj not in seen_projs:
                seen_projs.add(proj)
                weeks_5_8.append(f"**{_skill_label(skill)}** — {proj}")
    # If we only got one project, pad with a combination project
    if len(weeks_5_8) < 2 and len(real_missing) >= 2:
        combo = " + ".join(_skill_label(s) for s in real_missing[:2])
        weeks_5_8.append(
            f"Build an end-to-end mini-project combining {combo}"
        )
    weeks_5_8 += [
        "Document each project with a clear README, architecture notes, and usage examples",
        "Push all work to GitHub with descriptive commit history",
    ]

    # ── Weeks 9-12: Interview prep, tailored to the actual skills
    weeks_9_12 = [
        "Rewrite your resume using the exact terminology from this job description — "
        "mirror keywords like: " + ", ".join(
            _skill_label(s) for s in (real_missing[:2] + domain_skills[:2])
        ),
    ]
    if real_missing:
        weeks_9_12.append(
            "Prepare 2–3 STAR-format stories demonstrating your work with: "
            + ", ".join(_skill_label(s) for s in (domain_skills[:3] or matched_skills[:3]))
        )
        weeks_9_12.append(
            "Practice explaining how you would apply "
            + ", ".join(_skill_label(s) for s in real_missing[:2])
            + " in a real project scenario"
        )
    weeks_9_12.append(
        "Run 2+ mock interviews with a focus on gap areas: "
        + ", ".join(_skill_label(s) for s in real_missing[:3])
        if real_missing else
        "Run 2+ mock interviews focusing on your strongest matched skills"
    )

    action_plan = {
        "weeks_1_4":  weeks_1_4,
        "weeks_5_8":  weeks_5_8,
        "weeks_9_12": weeks_9_12,
    }


    return {
        "career_summary":       summary,
        "strengths":            strengths,
        "priority_skills":      priority_skills,
        "recommended_projects": recommended_projects,
        "career_paths":         career_paths,
        "action_plan":          action_plan,
    }


def _ollama_career_advice(
    matched_skills:  List[str],
    missing_skills:  List[str],
    skill_contexts:  List[Dict],
    job_description: str = "",
) -> Optional[Dict]:
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


class LLMClient:
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
        return None

    def extract_skills(self, text: str) -> List[str]:
        return []

    def generate_career_advice(
        self,
        matched_skills:  List[str],
        missing_skills:  List[str],
        skill_contexts:  List[Dict],
        job_description: str = "",
    ) -> Dict:
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


def get_llm_client() -> LLMClient:
    return LLMClient(provider="auto")