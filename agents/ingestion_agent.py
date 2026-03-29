"""
agents/ingestion_agent.py  —  Document Ingestion with OCR fallback.

Self-correction:
  - Primary: pdfplumber text extraction
  - Fallback: If < 50 chars extracted, retry with OCR (pytesseract)
  - If both fail: report failure for orchestrator to escalate
"""
from __future__ import annotations

import io
from typing import Any, Dict

from agents.base_agent import BaseAgent, AgentResult


class IngestionAgent(BaseAgent):
    """Extracts text from PDF resumes with self-correcting OCR fallback."""

    @property
    def name(self) -> str:
        return "IngestionAgent"

    def _execute(self, state: Dict[str, Any], **kwargs) -> AgentResult:
        pdf_bytes = state.get("pdf_bytes")
        if not pdf_bytes:
            return AgentResult(success=False, message="No PDF bytes provided")

        use_ocr = kwargs.get("use_ocr", False)
        text = ""

        if not use_ocr:
            # Primary: pdfplumber
            text = self._extract_pdfplumber(pdf_bytes)
        else:
            # Fallback: OCR mode
            self.audit.log_self_correction(
                self.name,
                "Switching to OCR mode — primary text extraction returned insufficient text",
                reasoning="PDF may be image-based or scanned",
            )
            text = self._extract_ocr(pdf_bytes)

        # Validate
        if len(text.strip()) < 50:
            if not use_ocr:
                return AgentResult(
                    success=False,
                    message=f"Insufficient text extracted ({len(text.strip())} chars). May need OCR.",
                    confidence=0.1,
                    data={"text": text, "needs_ocr": True},
                )
            else:
                return AgentResult(
                    success=False,
                    message=f"OCR also failed — only {len(text.strip())} chars extracted",
                    confidence=0.0,
                    data={"text": text},
                )

        # Count pages for context
        page_count = text.count("\n\n") + 1  # rough estimate

        return AgentResult(
            success=True,
            data={
                "resume_text": text,
                "char_count": len(text),
                "page_count_estimate": page_count,
                "extraction_method": "ocr" if use_ocr else "pdfplumber",
            },
            confidence=0.95 if not use_ocr else 0.75,
            message=f"Extracted {len(text)} chars via {'OCR' if use_ocr else 'pdfplumber'}",
        )

    def _extract_pdfplumber(self, pdf_bytes: bytes) -> str:
        """Primary extraction using pdfplumber."""
        import pdfplumber
        pages = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    pages.append(t)
        return "\n".join(pages).strip()

    def _extract_ocr(self, pdf_bytes: bytes) -> str:
        """
        OCR fallback using pytesseract + pdf2image.
        If these libraries aren't installed, returns empty string
        so the orchestrator can escalate gracefully.
        """
        try:
            from pdf2image import convert_from_bytes
            import pytesseract

            images = convert_from_bytes(pdf_bytes, dpi=300)
            texts = []
            for img in images:
                t = pytesseract.image_to_string(img)
                if t:
                    texts.append(t)
            return "\n".join(texts).strip()
        except ImportError:
            self.audit.log_fallback(
                self.name,
                "OCR libraries (pytesseract/pdf2image) not installed — cannot perform OCR",
                reasoning="Install pytesseract and pdf2image for OCR support",
            )
            return ""
        except Exception as e:
            self.audit.log_agent_fail(self.name, f"OCR error: {e}")
            return ""

    def _retry_kwargs(self, attempt, last_result, current_kwargs):
        """On retry, switch to OCR mode."""
        if last_result and last_result.data.get("needs_ocr"):
            return {**current_kwargs, "use_ocr": True}
        return {**current_kwargs, "use_ocr": True}

    def _input_snapshot(self, state):
        size = len(state.get("pdf_bytes", b""))
        return f"PDF: {size / 1024:.1f} KB"

    def _output_snapshot(self, result):
        cc = result.data.get("char_count", 0)
        method = result.data.get("extraction_method", "unknown")
        return f"{cc} chars via {method}"
