import os
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import faiss

BASE_DIR = os.path.dirname(__file__)
# Navigate up 3 levels: hs_service -> services -> AI -> models
MODELS_DIR = os.path.join(BASE_DIR, '..', '..', 'models')
MODELS_DIR = os.path.normpath(MODELS_DIR)

app = FastAPI(title='HS Code Suggestion Service')

class SuggestRequest(BaseModel):
    name: str = ''
    category: str = ''
    description: str = ''
    k: int = 5

class SuggestItem(BaseModel):
    hscode: str
    description: str
    score: float

class SuggestResponse(BaseModel):
    suggestions: List[SuggestItem]

model = None
index = None
meta = None

@app.on_event('startup')
def load_resources():
    global model, index, meta
    # Paths
    fs_index = os.path.join(MODELS_DIR, 'hs_index.faiss')
    meta_csv = os.path.join(MODELS_DIR, 'hs_meta.csv')
    emb_npy = os.path.join(MODELS_DIR, 'embeddings.npy')

    if not os.path.exists(fs_index) or not os.path.exists(meta_csv) or not os.path.exists(emb_npy):
        print('WARNING: Model files missing in', MODELS_DIR)
        print('  Expected:', fs_index, meta_csv, emb_npy)
        print('  Please run: python backend/AI/scripts/prepare_hs_data.py && python backend/AI/scripts/build_hs_embeddings.py')
        return

    model = SentenceTransformer('all-MiniLM-L6-v2')
    index = faiss.read_index(fs_index)
    meta = pd.read_csv(meta_csv)
    print('Loaded HS model and index. Rows:', len(meta))

@app.post('/suggest-hs', response_model=SuggestResponse)
def suggest_hs(req: SuggestRequest):
    if index is None or model is None or meta is None:
        return {'suggestions': []}
    q = f"{req.name or ''} {req.category or ''} {req.description or ''}".strip().lower()
    emb = model.encode([q], convert_to_numpy=True)
    faiss.normalize_L2(emb)
    D, I = index.search(emb, req.k)
    suggestions = []
    for score, idx in zip(D[0], I[0]):
        if idx < 0:
            continue
        row = meta.iloc[int(idx)]
        suggestions.append({'hscode': str(row.get('hscode', '')), 'description': str(row.get('description', '')), 'score': float(score)})
    return {'suggestions': suggestions}

@app.get('/health')
def health():
    return {'status': 'ok'}

@app.get('/model-info')
def model_info():
    if meta is None:
        return {'loaded': False}
    return {'loaded': True, 'rows': len(meta)}
