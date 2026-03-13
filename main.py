from rag_engine import get_rag_engine

# This will initialize the model and build the FAISS index based on your knowledge base
engine = get_rag_engine()

# Retrieve top context / documents about a skill (e.g., 'Python' or 'Kubernetes')
results = engine.retrieve("Vue.js")
print(results)

# Exit python
exit()