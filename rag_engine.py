"""
rag_engine.py  —  Retrieval-Augmented Generation engine for Career Copilot.

Uses FAISS for efficient vector similarity search over the knowledge base.
Provides contextual learning resources, project ideas, and career paths
for any missing skill identified during gap analysis.
"""
from __future__ import annotations

import numpy as np
import faiss

from embedding_module import generate_embeddings
from knowledge_base import get_all_knowledge_texts, get_skill_knowledge


class RAGEngine:
    """
    FAISS-backed retrieval engine over the skill knowledge base.

    On first use it embeds all knowledge documents and builds an index.
    Subsequent queries are fast in-memory lookups.
    """

    def __init__(self):
        self.documents:     list  = get_all_knowledge_texts()
        self.index:         object = None
        self.doc_embeddings: np.ndarray = None
        self._build_index()

    def _build_index(self) -> None:
        print("Building RAG knowledge-base index…")
        doc_texts            = [doc["text"] for doc in self.documents]
        self.doc_embeddings  = generate_embeddings(doc_texts)
        dimension            = self.doc_embeddings.shape[1]
        self.index           = faiss.IndexFlatL2(dimension)
        self.index.add(self.doc_embeddings.astype("float32"))
        print(f"  ✓ Indexed {len(self.documents)} knowledge documents")

    def retrieve(self, query: str, top_k: int = 3) -> list:
        """
        Retrieve the top-k most relevant knowledge documents for a query.

        Args:
            query:  skill name or free-form query text
            top_k:  number of results to return

        Returns:
            List of dicts with keys: document, distance, similarity
        """
        query_emb  = generate_embeddings([query])
        distances, indices = self.index.search(
            query_emb.astype("float32"), top_k
        )
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                results.append({
                    "document":   self.documents[idx],
                    "distance":   float(dist),
                    "similarity": 1 / (1 + float(dist)),
                })
        return results

    def get_context_for_skill(self, skill: str) -> dict:
        """
        Get rich learning context for a skill.

        Combines direct KB lookup with RAG retrieval for related context.

        Returns:
            Dict with: skill, description, learning_resources, project_ideas,
            career_paths, estimated_time, related_skills
        """
        knowledge = get_skill_knowledge(skill)
        retrieved = self.retrieve(skill, top_k=2)

        return {
            "skill":              skill,
            "description":        knowledge["description"],
            "learning_resources": knowledge["learning_resources"],
            "project_ideas":      knowledge["project_ideas"],
            "career_paths":       knowledge["career_paths"],
            "estimated_time":     knowledge["estimated_time"],
            "related_skills":     [
                r["document"]["skill"]
                for r in retrieved
                if r["document"]["skill"] != skill
            ],
        }

    def get_context_for_missing_skills(self, missing_skills: list) -> list:
        """Return context dicts for all missing skills."""
        return [self.get_context_for_skill(skill) for skill in missing_skills]


# ── Singleton factory ─────────────────────────────────────────────────────────
_rag_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    """Return the shared RAGEngine singleton (built on first call)."""
    global _rag_engine
    if _rag_engine is None:
        _rag_engine = RAGEngine()
    return _rag_engine