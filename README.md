---
title: SkillBridge AI - Enterprise Agentic Workflow Orchestrator
emoji: ⚡
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 8501
tags:
- streamlit
- multi-agent
- agentic-ai
- enterprise-workflow
- ollama
- nlp
pinned: true
short_description: Multi-agent system automating enterprise HR screening workflows offline
license: mit
---

# SkillBridge-AI ⚡ 
**Enterprise Agentic Workflow Orchestrator**

An autonomous, multi-agent AI system built to solve **ET Gen AI Hackathon Problem Statement 2 (Agentic AI for Autonomous Enterprise Workflows)**. 

SkillBridge-AI fundamentally redesigns the complex, high-friction enterprise process of Technical Candidate Screening. It replaces manual HR review with an intelligent, self-correcting decision graph that calculates semantic overlap, flags candidate deficits, and generates immutable audit trails of every programmatic decision made.

---
- **Depth of Autonomy:** The `AgentOrchestrator` determines payload routing based on calculated dynamic thresholds. High-scoring candidates bypass strategy agents and go directly to Fast-Track Interview prep agents. Zero hardcoded "skill lists" are used.
- **Error Recovery & Self-Correction:** Features an **OCR Recovery Loop** (if standard PDF scraping yields 0 NLP tokens, the orchestrator loops back seamlessly with Tesseract OCR activation) and a **Compliance Constraints Loop** (if output hallucinations or biases are detected, the orchestrator forces up to 2 regenerative retries under strict token limits).
- **100% Offline-Native (Enterprise PII Safe):** Corporate HR workflows absolutely cannot pass unfiltered candidate PII (names, emails) to external generic LLM pipes like ChatGPT. This system evaluates everything natively over Llama 3.2, spaCy, and FAISS. Zero internet necessary.
- **Immutable Ledger:** Every programmatic decision, execution timer, and agent output is synchronized into an uneditable, JSON-exportable `AuditLogger`, assuring total enterprise compliance and workflow accountability.

---

## 🧠 The Multi-Agent Ecosystem

The system operates as an overarching router delegating strictly typed workflows to specialized sub-agents:

1. **`AgentOrchestrator`**: The global state-manager monitoring SLAs, logging audits, and managing conditional routing logic.
2. **`IngestionAgent` & `ExtractionAgent`**: The miners. Translating arbitrary PDF structures into raw text, executing zero-shot semantic rule mapping, and cleaning tokens of linguistic noise.
3. **`AnalysisAgent`**: The vector mapper. Evaluates the candidate tokens against Job Description (JD) tokens utilizing a 7-pass FAISS matrix classifier.
4. **`StrategyAgent`|`FastTrackAgent`|`RedirectAgent`**: The generative squad. Based on the Orchestrator's score bounds, one of these agents takes temporary hold over the `llama3.2` endpoint to draft the response payload.
5. **`ComplianceAgent`**: The bound-checker. Re-checks the drafted payload for basic alignment, bias, or logical failures before allowing the Orchestrator to submit the data.

---

## 🛠 Tech Stack

| Domain | Technology Layer |
| :--- | :--- |
| **User Interface** | Streamlit |
| **Agent Orchestration** | Custom State-Machine Logic & AuditLedger |
| **Vector Database** | Meta FAISS (CPU-Optimized) |
| **NLP & Extraction** | `en_core_web_sm` (spaCy), pdfplumber, pytesseract |
| **Embedding Models** | all-MiniLM-L6-v2 (`sentence-transformers`) |
| **Generative LLM**| Ollama (`llama3.2` model) |

---

## Setup & Execution 

SkillBridge-AI is executed locally. **Python 3.10+** and **Ollama** are required.

### 1. Initialize the Local Inference Engine (Ollama)
Install [Ollama](https://ollama.ai/), then open a terminal and pull the model we map to our generative agents:
```bash
ollama pull llama3.2
ollama serve
```
*(Leave this terminal window running so our agents can ping `http://localhost:11434`)*

### 2. Install Python Dependencies
Open a new terminal window in the root of the SkillBridge-AI project repository:
```bash
# Optional: Create and activate a virtual environment
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

# Install the Python packages
pip install -r requirements.txt

# Download the spaCy English NLP model used by the ExtractionAgent
python -m spacy download en_core_web_sm
```

*(Note: For the OCR Fallback to function, ensure `pdf2image` prerequisites and Tesseract are installed on your OS level. On Windows, [install Tesseract OCR via executable](https://github.com/UB-Mannheim/tesseract/wiki); on Mac/Linux use `brew install tesseract` / `apt-get install tesseract-ocr`)*

### 3. Launch the Orchestrator Dashboard
Execute the pipeline:
```bash
streamlit run app.py
```
Upload an enterprise resume payload, paste your target process requirements (JD), and watch the agents negotiate an outcome in real-time on your dashboard.
