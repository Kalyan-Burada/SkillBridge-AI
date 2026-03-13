"""
setup.py  —  One-time setup script for Career Copilot.

Run once after installing dependencies:
    python setup.py

Downloads:
  • spaCy en_core_web_sm          (~12 MB, English NLP model)
  • NLTK stopwords corpus          (~2 MB, used for noise filtering)
  • sentence-transformers/all-MiniLM-L6-v2  (~90 MB, embedding model)
"""
import subprocess
import sys


def run(cmd: str, step: str) -> None:
    print(f"\n[{step}]  {cmd}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"  ✗ Command failed (exit code {result.returncode})")
        sys.exit(1)
    print("  ✓ Done")


def main():
    print("=" * 62)
    print("  Career Copilot — One-Time Setup")
    print("=" * 62)

    run(f"{sys.executable} -m spacy download en_core_web_sm",
        "1/3  spaCy English model (~12 MB)")

    run(f'{sys.executable} -c "import nltk; nltk.download(\'stopwords\')"',
        "2/3  NLTK stopwords corpus")

    run(
        f'{sys.executable} -c '
        '"from sentence_transformers import SentenceTransformer; '
        'SentenceTransformer(\'all-MiniLM-L6-v2\'); print(\'Model cached.\')"',
        "3/3  sentence-transformers model (~90 MB, first run only)",
    )

    print("\n" + "=" * 62)
    print("  Setup complete!  All models are cached locally.")
    print("")
    print("  Start the Streamlit app:")
    print("    streamlit run app.py")
    print("")
    print("  Start the API server:")
    print("    python api_server.py")
    print("")
    print("  Optional — richer career advice:")
    print("    Install Ollama → https://ollama.com")
    print("    ollama pull llama3.2")
    print("=" * 62)


if __name__ == "__main__":
    main()