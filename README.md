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
# 🚀 Career Copilot: AI Skill Gap Analyzer

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B.svg)
![Offline First](https://img.shields.io/badge/Privacy-Offline_First-success.svg)

**Career Copilot** is a privacy-focused, offline-first tool designed to bridge the gap between a candidate's Resume and a target Job Description (JD). It leverages local Natural Language Processing (NLP) and vector embeddings to extract skills, perform semantic matching, and generate actionable career advice—all without requiring paid external APIs.

---

## ✨ Key Features

* **🔒 Privacy-First & Offline**: Computations are done locally on your machine. No mandatory API keys (like OpenAI) are required. User data never leaves the server.
* **🧠 Semantic Match Engine**: Uses Hugging Face's `SentenceTransformers` (`all-MiniLM-L6-v2`) to mathematically calculate the similarity between resume skills and job requirements.
* **⚡ Dual-Mode Advice Generation**:
    * **Mode 1 (Ollama integration)**: Securely connects to a local [Ollama](https://ollama.com/) instance (e.g., `llama3.2`) for rich, contextual career advice.
    * **Mode 2 (Template Engine)**: A zero-dependency, deterministic fallback mode that provides structured skill gap analysis if no local LLM is available.
* **🎯 Domain-Agnostic**: Works across multiple industries. It isn't hardcoded for tech jobs; the similarity engine figures out contexts dynamically.
* **📊 Interactive Web UI**: A clean, responsive user interface built with Streamlit.

---

## 🛠️ Architecture & Tech Stack

* **Frontend**: Streamlit (`app.py`)
* **Core NLP**: `spaCy` for text parsing and phrase extraction.
* **Embeddings**: `SentenceTransformers` for creating dense vector representations of skills.
* **Matching**: Cosine similarity calculations for intelligent abbreviation handling and skill alignment.
* **LLM Engine**: `llm_client.py` orchestrates interaction with Ollama or falls back to standard heuristic templates.

---

## 🚀 Getting Started

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your machine.
*(Optional but recommended)*: Install [Ollama](https://ollama.com/) if you want advanced LLM-based output locally.

### 2. Installation
Clone the repository and set up your virtual environment:

```bash
git clone https://github.com/your-username/career-copilot.git
cd career-copilot

# Create and activate virtual environment
python -m venv venv

# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) You may need to download the spaCy language model depending on your requirements.txt setup:
# python -m spacy download en_core_web_md
```

### 3. Running the App
Spin up the interactive Streamlit interface:

```bash
streamlit run app.py
```
This will open the web app in your default browser at `http://localhost:8501`. 

*(To run the backend API server instead, you can run `python api_server.py` or `python main.py` for terminal usage).*

---

## 📁 Project Structure

```text
📦 Career Copilot
 ┣ 📜 app.py                  # Streamlit Web UI
 ┣ 📜 api_server.py           # Backend API entrypoint
 ┣ 📜 pipeline.py             # Main execution pipeline connecting modules
 ┣ 📜 llm_client.py           # Dual-mode (Ollama + Template) advice generator
 ┣ 📜 embedding_module.py     # Local SentenceTransformer embedding logic
 ┣ 📜 skill_gap_analyzer.py   # Computes matched, missing, and partial skills
 ┣ 📜 rag_engine.py           # Retrieves context-aware skill references
 ┣ 📜 similarity_engine.py    # Cosine similarity logic for matching
 ┣ 📜 phrase_extracter.py     # spaCy-based info extraction
 ┣ 📜 abbreviation_matcher.py # Normalizes abbreviations (e.g. AWS = Amazon Web Services)
 ┣ 📜 knowledge_base.py       # Domain semantic dictionary references
 ┗ 📜 requirements.txt        # Project dependencies
```

---

## 💡 How it Works (Under the Hood)
1. **Extraction**: The app reads the Resume and Job Description and uses `phrase_extracter.py` and `abbreviation_matcher.py` to identify tech/soft skills.
2. **Embedding**: `embedding_module.py` converts these terms into 384-dimensional mathematical arrays locally.
3. **Similarity**: The app compares arrays using `similarity_engine.py` to find direct hits, near hits, and misses.
4. **Advisory**: The gap data is passed to `llm_client.py`, which generates a human-readable roadmap using either local AI or standard templates.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
