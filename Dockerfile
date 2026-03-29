FROM python:3.11-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for Docker layer caching
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Download spaCy model and NLTK data at build time
RUN python -m spacy download en_core_web_sm
RUN python -c "import nltk; nltk.download('stopwords', quiet=True)"

# Copy all project files
COPY app.py ./
COPY pipeline.py ./
COPY implication_engine.py ./
COPY knowledge_base.py ./
COPY llm_client.py ./
COPY rag_engine.py ./
COPY embedding_module.py ./
COPY similarity_engine.py ./
COPY phrase_extracter.py ./
COPY abbreviation_matcher.py ./
COPY debug.py ./
COPY setup.py ./
COPY main.py ./

# HF Spaces expects port 7860, but Streamlit default is 8501
# We use 8501 and set app_port in README.md metadata
EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.fileWatcherType=none", "--server.enableCORS=false", "--server.enableXsrfProtection=false"]
