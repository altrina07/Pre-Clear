"""
FastAPI Service for Document Requirement Predictions
Serves ML model predictions with optional API integration
"""
import os
import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel

from predict_documents import (
    DocumentPredictor,
    DocumentPredictionRequest,
    DocumentPredictionResponse,
    PredictedDocument,
    merge_ml_and_api_predictions,
    load_predictor,
)
from api_integration import (
    DocumentRecommendationMode,
    ComplianceIntegration,
    create_default_integration,
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
DOCUMENT_RECOMMENDER_MODE = os.getenv(
    "DOCUMENT_RECOMMENDER_MODE",
    DocumentRecommendationMode.HYBRID.value
)
DOCUMENT_MODEL_PATH = os.getenv(
    "DOCUMENT_MODEL_PATH",
    str(Path(__file__).parent / "models")
)
COMPLIANCE_API_BASE_URL = os.getenv("COMPLIANCE_API_BASE_URL", "")
COMPLIANCE_API_KEY = os.getenv("COMPLIANCE_API_KEY", "")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
ML_WEIGHT = float(os.getenv("ML_WEIGHT", "0.6"))
API_WEIGHT = float(os.getenv("API_WEIGHT", "0.4"))

# Initialize FastAPI app
app = FastAPI(
    title="Document Requirement Predictor",
    description="Predicts required shipping documents using ML and optional API integration",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
predictor: Optional[DocumentPredictor] = None
compliance_integration: Optional[ComplianceIntegration] = None


@app.on_event("startup")
async def startup_event():
    """Initialize ML model and providers on startup."""
    global predictor, compliance_integration
    
    logger.info("Starting Document Requirement Predictor Service...")
    
    try:
        # Load ML model
        logger.info(f"Loading ML model from {DOCUMENT_MODEL_PATH}...")
        predictor = load_predictor(models_dir=DOCUMENT_MODEL_PATH)
        logger.info("✓ ML model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load ML model: {e}")
        if DOCUMENT_RECOMMENDER_MODE.lower() == "ml_only":
            raise
    
    # Initialize compliance integration for API mode
    if DOCUMENT_RECOMMENDER_MODE.lower() in ["api_only", "hybrid"]:
        try:
            logger.info(f"Initializing compliance providers (mode: {DOCUMENT_RECOMMENDER_MODE})...")
            mode = DocumentRecommendationMode(DOCUMENT_RECOMMENDER_MODE.lower())
            compliance_integration = create_default_integration(
                mode=mode,
                descartes_api_key=COMPLIANCE_API_KEY if COMPLIANCE_API_KEY else None,
            )
            logger.info("✓ Compliance integration initialized")
        except Exception as e:
            logger.error(f"Failed to initialize compliance integration: {e}")
            if DOCUMENT_RECOMMENDER_MODE.lower() == "api_only":
                raise
    
    logger.info(f"Service ready in {DOCUMENT_RECOMMENDER_MODE} mode")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    mode: str
    ml_model_ready: bool
    api_providers_ready: bool


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and readiness."""
    return HealthResponse(
        status="healthy",
        mode=DOCUMENT_RECOMMENDER_MODE,
        ml_model_ready=predictor is not None,
        api_providers_ready=compliance_integration is not None,
    )


class ModelInfoResponse(BaseModel):
    """Model information response."""
    version: str
    mode: str
    num_document_types: int
    document_types: List[str]
    timestamp: str


@app.get("/model-info", response_model=ModelInfoResponse)
async def model_info():
    """Get information about loaded model."""
    if not predictor or not predictor.model_components:
        raise HTTPException(status_code=503, detail="ML model not loaded")
    
    return ModelInfoResponse(
        version=predictor.model_components.metadata.get("model_version", "unknown"),
        mode=DOCUMENT_RECOMMENDER_MODE,
        num_document_types=len(predictor.model_components.label_names),
        document_types=predictor.model_components.label_names,
        timestamp=predictor.model_components.metadata.get("training_timestamp", ""),
    )


@app.post("/predict", response_model=DocumentPredictionResponse)
async def predict_documents(
    request: DocumentPredictionRequest,
    shipment_id: Optional[str] = None,
    confidence_threshold: Optional[float] = None,
):
    """
    Predict required documents for a shipment.
    
    Args:
        request: Shipment details
        shipment_id: Optional shipment ID for reference
        confidence_threshold: Override default confidence threshold (0.0-1.0)
    
    Returns:
        DocumentPredictionResponse with predicted documents
    """
    
    threshold = confidence_threshold or CONFIDENCE_THRESHOLD
    
    # ML predictions
    ml_predictions = []
    if DOCUMENT_RECOMMENDER_MODE.lower() in ["ml_only", "hybrid"]:
        if not predictor:
            raise HTTPException(status_code=503, detail="ML model not loaded")
        try:
            ml_predictions = predictor.predict(request, confidence_threshold=threshold)
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            if DOCUMENT_RECOMMENDER_MODE.lower() == "ml_only":
                raise HTTPException(status_code=500, detail=str(e))
    
    # API predictions
    api_predictions = {}
    if DOCUMENT_RECOMMENDER_MODE.lower() in ["api_only", "hybrid"]:
        if not compliance_integration:
            raise HTTPException(status_code=503, detail="Compliance integration not initialized")
        try:
            api_docs = await compliance_integration.get_documents_from_providers(
                hs_code=request.hs_code,
                origin_country=request.origin_country,
                destination_country=request.destination_country,
                product_description=request.product_description,
            )
            api_predictions = {
                name: {
                    "confidence": doc.confidence or 0.9,
                    "description": doc.description,
                    "regulatory_basis": doc.regulatory_basis,
                }
                for name, doc in api_docs.items()
            }
        except Exception as e:
            logger.error(f"API prediction error: {e}")
            if DOCUMENT_RECOMMENDER_MODE.lower() == "api_only":
                raise HTTPException(status_code=500, detail=str(e))
    
    # Merge predictions based on mode
    if DOCUMENT_RECOMMENDER_MODE.lower() == "hybrid":
        final_predictions = await merge_ml_and_api_predictions(
            ml_predictions,
            api_predictions,
            ml_weight=ML_WEIGHT,
            api_weight=API_WEIGHT,
        )
    elif DOCUMENT_RECOMMENDER_MODE.lower() == "api_only":
        final_predictions = [
            PredictedDocument(
                name=name,
                confidence=data["confidence"],
                provenance="api",
                description=data["description"],
                regulatory_basis=data["regulatory_basis"],
            )
            for name, data in api_predictions.items()
        ]
    else:  # ml_only
        final_predictions = ml_predictions
    
    return DocumentPredictionResponse(
        shipment_id=shipment_id,
        predicted_documents=final_predictions,
        mode=DOCUMENT_RECOMMENDER_MODE,
        model_version=predictor.model_components.metadata.get("model_version", "unknown")
            if predictor else "unknown",
        timestamp=datetime.utcnow().isoformat(),
        confidence_threshold=threshold,
    )


@app.post("/predict-batch")
async def predict_batch(
    requests: List[DocumentPredictionRequest],
    confidence_threshold: Optional[float] = None,
):
    """Predict documents for multiple shipments."""
    
    results = []
    for i, request in enumerate(requests):
        try:
            result = await predict_documents(
                request,
                shipment_id=f"batch_{i}",
                confidence_threshold=confidence_threshold,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Batch item {i} error: {e}")
            results.append({
                "error": str(e),
                "shipment_id": f"batch_{i}",
            })
    
    return {"results": results}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Document Requirement Predictor",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "model_info": "/model-info",
            "predict": "/predict",
            "predict_batch": "/predict-batch",
        }
    }


def main():
    """Start the FastAPI server."""
    port = int(os.getenv("DOCUMENT_PREDICTOR_PORT", "8002"))
    host = os.getenv("DOCUMENT_PREDICTOR_HOST", "0.0.0.0")
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
