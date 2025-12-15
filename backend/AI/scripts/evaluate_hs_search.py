import os
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
MODELS_DIR = os.path.join(BASE_DIR, 'models')

index_path = os.path.join(MODELS_DIR, 'hs_index.faiss')
meta_csv = os.path.join(MODELS_DIR, 'hs_meta.csv')

if not os.path.exists(index_path) or not os.path.exists(meta_csv):
    print('Evaluation script ready. Provide input manually.')
else:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    index = faiss.read_index(index_path)
    meta = pd.read_csv(meta_csv)

    def suggest_hs(name, category, description, k=5):
        q = ' '.join([str(name or ''), str(category or ''), str(description or '')]).strip().lower()
        emb = model.encode([q], convert_to_numpy=True)
        faiss.normalize_L2(emb)
        D, I = index.search(emb, k)
        results = []
        for score, idx in zip(D[0], I[0]):
            if idx < 0:
                continue
            row = meta.iloc[int(idx)]
            results.append({'hscode': row.get('hscode', ''), 'description': row.get('description', ''), 'score': float(score)})
        return results

    print('Evaluation script ready. Provide input manually.')
