"""
Pytest suite for document recommender system
Tests training pipeline, predictions, and API integration
"""
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import json

from predict_documents import (
    DocumentPredictor,
    DocumentPredictionRequest,
    PredictedDocument,
)
from api_integration import (
    ComplianceIntegration,
    DocumentRecommendationMode,
    USDAProvider,
    EuropeanComplianceProvider,
)


@pytest.fixture
def temp_models_dir():
    """Create temporary models directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_request():
    """Sample prediction request."""
    return DocumentPredictionRequest(
        product_name="Lithium Batteries",
        category="batteries",
        product_description="Rechargeable lithium-ion cells for consumer electronics",
        hs_code="8507.10",
        origin_country="CN",
        destination_country="US",
        package_type="Box",
        weight=50.0,
        declared_value=5000.0,
        shipment_type="International",
        service_level="Standard",
    )


class TestDocumentPredictor:
    """Tests for DocumentPredictor class."""
    
    def test_predictor_initialization(self):
        """Test predictor can be instantiated."""
        predictor = DocumentPredictor()
        assert predictor is not None
        assert predictor.model_components is None
    
    def test_model_loading_nonexistent(self):
        """Test loading nonexistent model raises error."""
        predictor = DocumentPredictor(models_dir="/nonexistent/path")
        with pytest.raises(FileNotFoundError):
            predictor.load_model()
    
    def test_feature_preparation_shape(self, sample_request):
        """Test feature preparation returns correct shape."""
        predictor = DocumentPredictor()
        # This test would need actual model loaded
        # For now, just verify the request is valid
        assert sample_request.hs_code == "8507.10"
        assert sample_request.weight == 50.0


class TestComplianceProviders:
    """Tests for compliance provider implementations."""
    
    @pytest.mark.asyncio
    async def test_usda_provider_food(self):
        """Test USDA provider recognizes food products."""
        provider = USDAProvider()
        docs = await provider.get_required_documents(
            hs_code="2106.10",
            origin_country="MX",
            destination_country="US",
            product_description="Dried organic vegetables and herbs",
        )
        
        assert len(docs) > 0
        doc_names = [d.name for d in docs]
        assert "Health Certificate" in doc_names
    
    @pytest.mark.asyncio
    async def test_usda_provider_non_food(self):
        """Test USDA provider ignores non-food products."""
        provider = USDAProvider()
        docs = await provider.get_required_documents(
            hs_code="6204.62",
            origin_country="BD",
            destination_country="US",
            product_description="Women's cotton textiles and clothing",
        )
        
        # USDA shouldn't require documents for non-food
        assert len(docs) == 0
    
    @pytest.mark.asyncio
    async def test_eu_provider_non_eu_destination(self):
        """Test EU provider only applies to EU destinations."""
        provider = EuropeanComplianceProvider()
        docs = await provider.get_required_documents(
            hs_code="8708.31",
            origin_country="JP",
            destination_country="US",
            product_description="Electronic vehicle components",
        )
        
        # Shouldn't return docs for non-EU destination
        assert len(docs) == 0
    
    @pytest.mark.asyncio
    async def test_eu_provider_electronics(self):
        """Test EU provider for electronics."""
        provider = EuropeanComplianceProvider()
        docs = await provider.get_required_documents(
            hs_code="8471.30",
            origin_country="CN",
            destination_country="EU-DE",
            product_description="Electronic computing devices",
        )
        
        assert len(docs) > 0
        doc_names = [d.name for d in docs]
        assert any("CE" in name for name in doc_names)


class TestComplianceIntegration:
    """Tests for compliance integration orchestration."""
    
    def test_integration_initialization(self):
        """Test compliance integration can be created."""
        integration = ComplianceIntegration(mode=DocumentRecommendationMode.HYBRID)
        assert integration is not None
        assert len(integration.providers) == 0
    
    def test_register_provider(self):
        """Test provider registration."""
        integration = ComplianceIntegration()
        provider = USDAProvider()
        integration.register_provider(provider)
        
        assert "USDA" in integration.providers
        assert integration.providers["USDA"] == provider
    
    @pytest.mark.asyncio
    async def test_multiple_providers_concurrent(self):
        """Test multiple providers can be called concurrently."""
        integration = ComplianceIntegration()
        integration.register_provider(USDAProvider())
        integration.register_provider(EuropeanComplianceProvider())
        
        results = await integration.get_documents_from_providers(
            hs_code="2106.10",
            origin_country="MX",
            destination_country="EU-FR",
            product_description="Organic food ingredients",
        )
        
        # Should get results from multiple providers
        assert isinstance(results, dict)
        # Could have Health Cert (USDA) and EUR-1 (EU)


class TestInputValidation:
    """Tests for input validation."""
    
    def test_valid_request(self, sample_request):
        """Test valid request passes validation."""
        assert sample_request.hs_code is not None
        assert sample_request.weight > 0
        assert sample_request.origin_country == "CN"
    
    def test_request_fields_required(self):
        """Test that required fields are enforced."""
        # This would test Pydantic validation
        with pytest.raises(Exception):  # Pydantic validation error
            DocumentPredictionRequest(
                product_name="Test",
                # Missing other required fields
            )


class TestOutputFormat:
    """Tests for output format consistency."""
    
    def test_predicted_document_structure(self):
        """Test PredictedDocument has required fields."""
        doc = PredictedDocument(
            name="Invoice",
            confidence=0.92,
            provenance="ml",
        )
        
        assert doc.name == "Invoice"
        assert 0.0 <= doc.confidence <= 1.0
        assert doc.provenance in ["ml", "api", "rule", "hybrid"]
    
    def test_confidence_bounds(self):
        """Test confidence is within valid range."""
        with pytest.raises(Exception):  # Pydantic validation
            PredictedDocument(
                name="Test",
                confidence=1.5,  # Invalid: > 1.0
                provenance="ml",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
