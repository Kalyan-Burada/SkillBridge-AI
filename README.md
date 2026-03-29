# SkillBridge-AI ⚡ 
**Enterprise Agentic Workflow Orchestrator**

An autonomous, multi-agent AI system built to solve **ET Gen AI Hackathon Problem Statement 2 (Agentic AI for Autonomous Enterprise Workflows)**. 

SkillBridge-AI fundamentally redesigns the complex, high-friction enterprise process of Technical Candidate Screening. It replaces manual HR review with an intelligent, self-correcting decision graph that calculates semantic overlap, flags candidate deficits, and generates immutable audit trails of every programmatic decision made.


## ✨ Key Features

* **🔒 Privacy-First & Offline**: Computations are done locally on your machine. No mandatory API keys (like OpenAI) are required. User data never leaves the server.
* **🧠 Semantic Match Engine**: Uses Hugging Face's `SentenceTransformers` (`all-MiniLM-L6-v2`) to mathematically calculate the similarity between resume skills and job requirements.
* **⚡ Dual-Mode Advice Generation**:
    * **Mode 1 (Ollama integration)**: Securely connects to a local [Ollama](https://ollama.com/) instance (e.g., `llama3.2`) for rich, contextual career advice.
    * **Mode 2 (Template Engine)**: A zero-dependency, deterministic fallback mode that provides structured skill gap analysis if no local LLM is available.
* **🎯 Domain-Agnostic**: Works across multiple industries. It isn't hardcoded for tech jobs; the similarity engine figures out contexts dynamically.
* **📊 Interactive Web UI**: A clean, responsive user interface built with Streamlit.

---
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
## 📁 Project Structure

```text
📦 SkillBridge-AI
 ┣ 📂 agents/                 # Multi-Agent Subsystems
 ┃  ┣ 📜 base_agent.py        # Abstract agent blueprints and result schema
 ┃  ┣ 📜 ingestion_agent.py   # PDF digestion (with Tesseract OCR bounds)
 ┃  ┣ 📜 extraction_agent.py  # Zero-Shot NLP named entity recognition
 ┃  ┣ 📜 analysis_agent.py    # 7-pass vector implication and skill mapping
 ┃  ┣ 📜 strategy_agent.py    # Generates upskilling protocols via LLM
 ┃  ┣ 📜 fast_track_agent.py  # Generates interview prep for 90%+ matches
 ┃  ┣ 📜 redirect_agent.py    # Pivots sub-40% candidates to alternate roles
 ┃  ┗ 📜 compliance_agent.py  # Validates LLM outputs for bias/hallucination
 ┣ 📜 agent_orchestrator.py   # The central state-machine, delegator & routing decision engine
 ┣ 📜 audit_logger.py         # Immutable ledger tracking SLAs, decisions, and exceptions
 ┣ 📜 app.py                  # Streamlit Enterprise Workflow Health Dashboard
 ┣ 📜 implication_engine.py   # Resolves semantic overlaps (e.g., PyTorch implies Python)
 ┣ 📜 llm_client.py           # Native urllib client pinging local Ollama (Llama 3.2)
 ┣ 📜 embedding_module.py     # Local SentenceTransformer embeddings logic
 ┣ 📜 similarity_engine.py    # FAISS Cosine similarity for multidimensional semantic scoring
 ┣ 📜 phrase_extracter.py     # Core NLP grammatical stripping rulebook
 ┣ 📜 knowledge_base.py       # Domain semantic dictionary reference
 ┗ 📜 requirements.txt        # Enterprise project dependencies

---

💡 How it Works (Under the Hood)
Unlike standard linear pipelines, this system operates dynamically based on real-time execution thresholds and error bounds.

State Orchestration: agent_orchestrator.py initiates a localized memory ledger (WorkflowState). It dictates which agent executes next and permanently logs all routing decisions to audit_logger.py.
Ingestion & Extraction: The Orchestrator calls the IngestionAgent to pull raw text (deploying OCR dynamically if standard layout parsing fails), followed by the ExtractionAgent which isolates pure competencies using Zero-Shot NLP.
Semantic Mapping: The AnalysisAgent activates the implication_engine.py using localized FAISS vectors and SentenceTransformers to detect direct hits, implied relationships, and ultimate deficit scores.
Autonomous Execution: Based on the exact mathematical threshold from step #3, the Orchestrator delegates to a specific generative node (e.g., FastTrackAgent vs StrategyAgent).
Generative Compliance: Local llm_client.py formulates the drafted business logic via Llama 3.2. Finally, the ComplianceAgent bounds-checks the result. If hallucinations are flagged, the Orchestrator executes a self-correction loop back to the generative node before reporting the final output to the user.
