import os
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
os.makedirs(MODELS_DIR, exist_ok=True)

meta_parquet = os.path.join(MODELS_DIR, 'hs_meta.parquet')
if not os.path.exists(meta_parquet):
    raise FileNotFoundError(f"Missing {meta_parquet}. Run prepare_hs_data.py first.")

hs = pd.read_parquet(meta_parquet)
texts = hs['text'].astype(str).tolist()

model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

# Normalize embeddings for cosine via inner product
faiss.normalize_L2(embeddings)

d = embeddings.shape[1]
index = faiss.IndexFlatIP(d)
index.add(embeddings)

faiss.write_index(index, os.path.join(MODELS_DIR, 'hs_index.faiss'))
np.save(os.path.join(MODELS_DIR, 'embeddings.npy'), embeddings)
hs.to_csv(os.path.join(MODELS_DIR, 'hs_meta.csv'), index=False)

print('Embeddings shape:', embeddings.shape)
print('Saved FAISS index and embeddings.')
