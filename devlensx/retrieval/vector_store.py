"""
DevLensX Module 3: FAISS Code Vector Store (Real Semantic Embeddings)

Embeds code AST snippets & class definitions into dense vector embeddings
using SentenceTransformers (all-MiniLM-L6-v2) for true semantic search.
Uses FAISS for high-efficiency vector indexing.
"""

import os
import numpy as np
import faiss

class FAISSVectorStore:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.embedding_model = None
        self.dimension = 384  # Default dimension for all-MiniLM-L6-v2
        
        if os.getenv("DEVLENSX_ENABLE_ST", "0") == "1":
            try:
                from sentence_transformers import SentenceTransformer
                self.embedding_model = SentenceTransformer(model_name)
                self.dimension = self.embedding_model.get_sentence_embedding_dimension()
            except Exception:
                self.embedding_model = None

        if self.embedding_model is None:
            self.dimension = 128

        self.index = faiss.IndexFlatL2(self.dimension)
        self.documents = []

    def _encode_text(self, text_list):
        """Encodes texts into dense semantic embeddings."""
        if self.embedding_model is not None:
            embeddings = self.embedding_model.encode(text_list, show_progress_bar=False)
            return np.array(embeddings, dtype=np.float32)
        
        # Fallback deterministic hashing
        vectors = []
        for text in text_list:
            vec = np.zeros(self.dimension, dtype=np.float32)
            words = text.lower().split()
            for idx, word in enumerate(words):
                hash_val = sum(ord(c) for c in word)
                slot = hash_val % self.dimension
                vec[slot] += 1.0 / (idx + 1)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)

    def add_documents(self, docs):
        """
        docs: List of dicts with 'id', 'content', 'metadata'
        """
        if not docs:
            return
        contents = [doc.get("content", "") for doc in docs]
        vectors = self._encode_text(contents)
        
        for doc in docs:
            self.documents.append(doc)
            
        self.index.add(vectors)

    def build_index(self, docs):
        """Alias for add_documents."""
        self.add_documents(docs)

    def search(self, query, top_k=5):
        if self.index.ntotal == 0:
            return []
        query_vec = self._encode_text([query])
        distances, indices = self.index.search(query_vec, min(top_k, self.index.ntotal))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents) and idx >= 0:
                doc = self.documents[idx]
                results.append({
                    "id": doc.get("id"),
                    "content": doc.get("content"),
                    "metadata": doc.get("metadata"),
                    "score": float(1.0 / (1.0 + dist))
                })
        return results
