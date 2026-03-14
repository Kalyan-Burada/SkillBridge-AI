"""
api_server.py  —  Career Copilot FastAPI backend.
Start:
    python api_server.py
  or
    uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload
All analysis logic lives in pipeline.py.
Career advice logic lives in llm_client.py.
"""
from __future__ import annotations
import os
import traceback
from contextlib import asynccontextmanager
from typing import List, Optional, Union
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pipeline import run_analysis


def _get_rag():
    try:
        from rag_engine import get_rag_engine
        return get_rag_engine()
    except Exception as e:
        print(f"  RAG engine unavailable: {e}")
        return None


def _get_llm():
    try:
        from llm_client import get_llm_client
        return get_llm_client()
    except Exception as e:
        print(f"  LLM client unavailable: {e}")
        return None


rag_engine = None
llm_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_engine, llm_client
    print("\n Career Copilot API starting (offline)...")
    rag_engine = _get_rag()
    llm_client = _get_llm()
    prov = llm_client.provider if llm_client else "unavailable"
    print(f"  LLM provider : {prov}")
    print("  API ready     — no API key required\n")
    yield


app = FastAPI(
    title="Career Copilot API",
    description=(
        "Offline skill gap analysis — "
        "spaCy extraction + cosine similarity matching. "
        "Works for any job domain."
    ),
    version="5.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ── Response schema ───────────────────────────────────────────────────────────

class SkillScore(BaseModel):
    best_score: float
    best_match: Optional[str]
    # match_pass is a string label, not an int.
    # Values: "exact" | "overlap" | "cosine" | "abbrev" | "implied" | "missing"
    # (Previously typed as int — that crashed when ImplicationEngine returned
    # string labels like "implied-A". Fixed to Union[str, int] with normalisation.)
    match_pass: Union[str, int]

    @classmethod
    def _normalise_pass(cls, raw_pass) -> str:
        """Convert any pass value (int or string) to a human-readable label."""
        _INT_LABELS = {
            0: "missing",
            1: "exact",
            2: "overlap",
            3: "cosine",
            4: "abbrev",
        }
        if isinstance(raw_pass, int):
            return _INT_LABELS.get(raw_pass, str(raw_pass))
        # String passes from ImplicationEngine: "implied-A", "implied-B", "implied-C"
        if isinstance(raw_pass, str) and raw_pass.startswith("implied"):
            return "implied"
        return str(raw_pass)


class AnalysisResponse(BaseModel):
    jd_skills:            List[str]
    resume_skills:        List[str]
    matched_skills:       List[str]
    missing_skills:       List[str]
    match_score:          float
    jd_skills_count:      int
    resume_skills_count:  int
    llm_provider:         str
    per_skill_scores:     dict
    career_advice:        Optional[dict] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {
        "status":  "healthy",
        "service": "Career Copilot API (offline)",
        "version": "5.0.0",
        "note":    "Works for any job domain — no API key required",
    }


@app.get("/api/health")
async def health():
    return {
        "api":          "healthy",
        "rag_engine":   "available" if rag_engine else "unavailable",
        "llm_provider": llm_client.provider if llm_client else "offline",
        "offline_mode": True,
    }


@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze(
    resume:          UploadFile = File(...),
    job_description: str        = Form(...),
):
    """
    Full skill gap analysis pipeline.
    1. PDF → text            (pdfplumber)
    2. Text → skill phrases  (spaCy + zero-shot SentenceTransformer)
    3. Skills → embeddings   (all-MiniLM-L6-v2)
    4. Cosine similarity matrix
    5. 7-pass classification  → matched / missing
    6. Career advice          (Ollama or template engine)
    Works for any industry and job role — no hardcoded skill dictionaries.
    """
    pdf_bytes = await resume.read()
    try:
        result = run_analysis(pdf_bytes, job_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Log the full traceback server-side for debugging.
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Reshape per_skill_scores into Pydantic-safe dicts.
    # IMPORTANT: normalise match_pass to a string so Pydantic never tries
    # to coerce "implied-A" → int (which caused the original crash).
    pss = {
        skill: SkillScore(
            best_score=info["best_score"],
            best_match=info.get("best_match"),
            match_pass=SkillScore._normalise_pass(info.get("pass", 0)),
        )
        for skill, info in result["per_skill_scores"].items()
    }

    # Career advice (optional — never fails the whole request)
    career_advice: Optional[dict] = None
    if result["missing_skills"] and rag_engine and llm_client:
        try:
            contexts = rag_engine.get_context_for_missing_skills(
                result["missing_skills"][:5]
            )
            career_advice = llm_client.generate_career_advice(
                matched_skills=result["matched_skills"],
                missing_skills=result["missing_skills"],
                skill_contexts=contexts,
                job_description=job_description,
            )
        except Exception as e:
            print(f"  Career advice error: {e}")

    return AnalysisResponse(
        jd_skills=result["jd_skills"],
        resume_skills=result["resume_skills"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        match_score=result["match_score"],
        jd_skills_count=len(result["jd_skills"]),
        resume_skills_count=len(result["resume_skills"]),
        llm_provider=llm_client.provider if llm_client else "offline",
        per_skill_scores={k: v.model_dump() for k, v in pss.items()},
        career_advice=career_advice,
    )


@app.get("/api/skill-context")
async def skill_context(skill: str):
    if not rag_engine:
        raise HTTPException(status_code=503, detail="RAG engine not available.")
    try:
        return rag_engine.get_context_for_skill(skill)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)