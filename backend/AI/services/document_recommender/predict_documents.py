"""
Document Requirement Inference Module
Loads trained model and generates predictions for shipments
"""
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import asyncio
import logging

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.preprocessing import MultiLabelBinarizer
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentRecommendationMode(str, Enum):
    """Mode of operation for document recommendation."""
    ML_ONLY = "ml_only"
    API_ONLY = "api_only"
    HYBRID = "hybrid"


class DocumentPredictionRequest(BaseModel):
    """Input request for document prediction."""
    product_name: str
    category: str
    product_description: str
    hs_code: str
    origin_country: str
    destination_country: str
    package_type: str
    weight: float
    declared_value: float
    shipment_type: str
    service_level: str


class PredictedDocument(BaseModel):
    """A predicted document requirement."""
    name: str
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    provenance: str = Field("ml", description="'ml', 'api', or 'rule'")
    description: Optional[str] = None
    regulatory_basis: Optional[str] = None


class DocumentPredictionResponse(BaseModel):
    """Response containing predicted documents."""
    shipment_id: Optional[str] = None
    predicted_documents: List[PredictedDocument]
    mode: str
    model_version: str
    timestamp: str
    confidence_threshold: float


@dataclass
class ModelComponents:
    """Loaded model components."""
    classifier: object
    mlb: MultiLabelBinarizer
    label_names: List[str]
    metadata: Dict


class DocumentPredictor:
    """Loads and uses trained model for predictions."""
    
    def __init__(self, models_dir: str = None):
        self.models_dir = Path(models_dir or Path(__file__).parent / "models")
        self.model_components: Optional[ModelComponents] = None
        self.text_encoder = None
        self.tfidf = None
        self.ohe = None
        self.scaler = None
    
    def load_model(self):
        """Load trained model and preprocessing components."""
        model_path = self.models_dir / "required_docs_model.pkl"
        
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        with open(model_path, "rb") as f:
            data = pickle.load(f)
        
        self.model_components = ModelComponents(
            classifier=data["classifier"],
            mlb=data["mlb"],
            label_names=data["label_names"],
            metadata=data.get("metadata", {})
        )
        
        # Initialize text encoder
        if self.model_components.metadata.get("text_encoder") == "sentence-transformers":
            if HAS_SENTENCE_TRANSFORMERS:
                model_name = self.model_components.metadata.get("text_model", "all-MiniLM-L6-v2")
                self.text_encoder = SentenceTransformer(model_name)
            else:
                logger.warning("sentence-transformers not available, using TF-IDF")
                self.tfidf = TfidfVectorizer(max_features=128, stop_words="english")
        else:
            self.tfidf = TfidfVectorizer(max_features=128, stop_words="english")
        
        logger.info(f"✓ Loaded model with {len(self.model_components.label_names)} document types")
    
    def _prepare_features(
        self,
        product_name: str,
        category: str,
        product_description: str,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        package_type: str,
        weight: float,
        declared_value: float,
        shipment_type: str,
        service_level: str,
    ) -> np.ndarray:
        """Prepare feature vector for prediction."""
        
        # Text features
        text_input = (
            f"{product_name} {category} {product_description} {hs_code}"
        )
        
        if HAS_SENTENCE_TRANSFORMERS and self.text_encoder:
            text_features = self.text_encoder.encode([text_input], show_progress_bar=False)[0]
        else:
            # Fallback: TF-IDF
            if self.tfidf is None:
                self.tfidf = TfidfVectorizer(max_features=128, stop_words="english")
                self.tfidf.fit([text_input])
            text_features = self.tfidf.transform([text_input]).toarray()[0]
        
        # Categorical features (one-hot encode)
        if self.ohe is None:
            self.ohe = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
            categorical_data = np.array([[
                origin_country, destination_country, package_type, shipment_type, service_level
            ]])
            self.ohe.fit(categorical_data)
        
        categorical_features = self.ohe.transform(np.array([[
            origin_country, destination_country, package_type, shipment_type, service_level
        ]]))[0]
        
        # Numeric features
        if self.scaler is None:
            self.scaler = StandardScaler()
            self.scaler.fit(np.array([[weight, declared_value]]))
        
        numeric_features = self.scaler.transform(np.array([[weight, declared_value]]))[0]
        
        # Combine all features
        features = np.hstack([text_features, categorical_features, numeric_features])
        return features.reshape(1, -1)
    
    def predict(
        self,
        request: DocumentPredictionRequest,
        confidence_threshold: float = 0.5,
    ) -> List[PredictedDocument]:
        """Generate document predictions for a shipment."""
        
        if not self.model_components:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Prepare features
        features = self._prepare_features(
            product_name=request.product_name,
            category=request.category,
            product_description=request.product_description,
            hs_code=request.hs_code,
            origin_country=request.origin_country,
            destination_country=request.destination_country,
            package_type=request.package_type,
            weight=request.weight,
            declared_value=request.declared_value,
            shipment_type=request.shipment_type,
            service_level=request.service_level,
        )
        
        # Get predictions and probabilities
        predictions = self.model_components.classifier.predict(features)[0]
        
        # Get probability estimates from individual classifiers
        probabilities = []
        for estimator in self.model_components.classifier.estimators_:
            proba = estimator.predict_proba(features)[0]
            probabilities.append(proba[1])  # Probability of positive class
        probabilities = np.array(probabilities)
        
        # Build results
        results = []
        for idx, label_name in enumerate(self.model_components.label_names):
            if predictions[idx]:  # If predicted as required
                confidence = float(probabilities[idx])
                if confidence >= confidence_threshold:
                    results.append(PredictedDocument(
                        name=label_name,
                        confidence=confidence,
                        provenance="ml",
                    ))
        
        # Sort by confidence (highest first)
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def predict_batch(
        self,
        requests: List[DocumentPredictionRequest],
        confidence_threshold: float = 0.5,
    ) -> List[List[PredictedDocument]]:
        """Predict for multiple shipments."""
        return [
            self.predict(req, confidence_threshold=confidence_threshold)
            for req in requests
        ]


async def merge_ml_and_api_predictions(
    ml_predictions: List[PredictedDocument],
    api_predictions: Dict[str, Dict],
    ml_weight: float = 0.6,
    api_weight: float = 0.4,
) -> List[PredictedDocument]:
    """Merge ML and API predictions using weighted confidence."""
    
    merged = {}
    
    # Add ML predictions
    for doc in ml_predictions:
        merged[doc.name] = doc.copy(deep=True)
    
    # Merge with API predictions
    for doc_name, api_doc in api_predictions.items():
        if doc_name in merged:
            # Weight the confidences
            ml_conf = merged[doc_name].confidence
            api_conf = api_doc.get("confidence", 0.9)
            merged_conf = (ml_conf * ml_weight + api_conf * api_weight) / (ml_weight + api_weight)
            merged[doc_name].confidence = merged_conf
            merged[doc_name].provenance = "hybrid"
        else:
            # Add new API prediction
            merged[doc_name] = PredictedDocument(
                name=doc_name,
                confidence=api_doc.get("confidence", 0.9),
                provenance="api",
                description=api_doc.get("description"),
                regulatory_basis=api_doc.get("regulatory_basis"),
            )
    
    # Sort by confidence
    results = list(merged.values())
    results.sort(key=lambda x: x.confidence, reverse=True)
    
    return results


def load_predictor(models_dir: str = None) -> DocumentPredictor:
    """Helper to load and return a predictor."""
    predictor = DocumentPredictor(models_dir=models_dir)
    predictor.load_model()
    return predictor
