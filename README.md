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
