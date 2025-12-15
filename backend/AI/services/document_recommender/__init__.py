"""Document Recommender - ML-based document requirement prediction system."""

__version__ = "1.0.0"
__author__ = "Pre-Clear Team"

from .predict_documents import (
    DocumentPredictor,
    DocumentPredictionRequest,
    DocumentPredictionResponse,
    PredictedDocument,
)

from .api_integration import (
    ComplianceProvider,
    ComplianceIntegration,
    create_default_integration,
)

__all__ = [
    "DocumentPredictor",
    "DocumentPredictionRequest",
    "DocumentPredictionResponse",
    "PredictedDocument",
    "ComplianceProvider",
    "ComplianceIntegration",
    "create_default_integration",
]
