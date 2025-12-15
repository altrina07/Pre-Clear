"""
API Integration Layer for Document Requirements
Interfaces with external compliance/regulatory APIs to retrieve document requirements
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
import aiohttp
from requests.adapters import Retry
from requests.packages.urllib3.util.retry import Retry as UrllibRetry
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class DocumentRequirement:
    """Represents a required document with metadata."""
    name: str
    provider: str
    confidence: Optional[float] = None
    description: Optional[str] = None
    regulatory_basis: Optional[str] = None
    required: bool = True


class ComplianceMode(str, Enum):
    """Mode of operation for document recommendation."""
    ML_ONLY = "ml_only"
    API_ONLY = "api_only"
    HYBRID = "hybrid"


class ComplianceProvider(ABC):
    """Abstract base class for compliance data providers."""
    
    def __init__(self, name: str, max_retries: int = 3, timeout: int = 10):
        self.name = name
        self.max_retries = max_retries
        self.timeout = timeout
    
    @abstractmethod
    async def get_required_documents(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        product_description: str,
        **kwargs
    ) -> List[DocumentRequirement]:
        """Get required documents for a shipment."""
        pass
    
    async def _retry_request(
        self,
        session: aiohttp.ClientSession,
        method: str,
        url: str,
        **kwargs
    ) -> Any:
        """Execute HTTP request with exponential backoff."""
        for attempt in range(self.max_retries):
            try:
                async with session.request(method, url, timeout=self.timeout, **kwargs) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status >= 500:
                        if attempt < self.max_retries - 1:
                            wait_time = 2 ** attempt
                            logger.warning(
                                f"{self.name}: Server error (attempt {attempt + 1}/{self.max_retries}), "
                                f"retrying in {wait_time}s"
                            )
                            await asyncio.sleep(wait_time)
                            continue
                    raise Exception(f"API returned {resp.status}")
            except asyncio.TimeoutError:
                if attempt < self.max_retries - 1:
                    logger.warning(f"{self.name}: Timeout (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        raise Exception(f"Failed after {self.max_retries} attempts")


class DescartesProvider(ComplianceProvider):
    """Descartes compliance data provider."""
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.descartes.com",
        **kwargs
    ):
        super().__init__(name="Descartes", **kwargs)
        self.api_key = api_key
        self.base_url = base_url
    
    async def get_required_documents(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        product_description: str,
        **kwargs
    ) -> List[DocumentRequirement]:
        """Get documents from Descartes API."""
        
        # Map to Descartes endpoints
        endpoint = f"{self.base_url}/v1/regulations/documents"
        
        params = {
            "hs_code": hs_code,
            "origin": origin_country,
            "destination": destination_country,
            "product": product_description,
        }
        
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                data = await self._retry_request(session, "GET", endpoint, params=params, headers=headers)
            
            documents = []
            if isinstance(data, dict) and "documents" in data:
                for doc in data["documents"]:
                    documents.append(DocumentRequirement(
                        name=doc.get("name"),
                        provider="Descartes",
                        confidence=doc.get("confidence", 0.95),
                        description=doc.get("description"),
                        regulatory_basis=doc.get("regulation", "Unknown"),
                    ))
            
            return documents
        
        except Exception as e:
            logger.error(f"Descartes API error: {e}")
            return []


class USDAProvider(ComplianceProvider):
    """USDA food/agricultural import requirements provider."""
    
    def __init__(self, **kwargs):
        super().__init__(name="USDA", **kwargs)
    
    async def get_required_documents(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        product_description: str,
        **kwargs
    ) -> List[DocumentRequirement]:
        """Get USDA agricultural requirements."""
        
        # For food/agriculture products
        is_food = any(kw in product_description.lower() for kw in ["food", "agricultural", "plant", "meat", "dairy"])
        
        if not is_food:
            return []
        
        documents = []
        
        # USDA requires specific documents for food imports
        documents.append(DocumentRequirement(
            name="Health Certificate",
            provider="USDA",
            confidence=0.98,
            description="Food safety certificate from origin country",
            regulatory_basis="21 CFR Part 1 (FDA)",
            required=True
        ))
        
        documents.append(DocumentRequirement(
            name="Phytosanitary Certificate",
            provider="USDA",
            confidence=0.95,
            description="Plant health certificate",
            regulatory_basis="IPPC Standards",
            required="plant" in product_description.lower()
        ))
        
        # Specific for meat products
        if "meat" in product_description.lower() or "poultry" in product_description.lower():
            documents.append(DocumentRequirement(
                name="FSIS Import Permit",
                provider="USDA",
                confidence=0.99,
                description="USDA FSIS permit for meat/poultry",
                regulatory_basis="FSIS Regulations",
                required=True
            ))
        
        return documents


class EuropeanComplianceProvider(ComplianceProvider):
    """European Union/EMCS compliance provider."""
    
    def __init__(self, **kwargs):
        super().__init__(name="EUCompliance", **kwargs)
    
    async def get_required_documents(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        product_description: str,
        **kwargs
    ) -> List[DocumentRequirement]:
        """Get EU compliance requirements."""
        
        if not destination_country.startswith("EU-"):
            return []
        
        documents = []
        
        # Check for CE marking required products
        if any(kw in product_description.lower() for kw in ["electronic", "machinery", "medical", "toys"]):
            documents.append(DocumentRequirement(
                name="CE Declaration of Conformity",
                provider="EU",
                confidence=0.98,
                description="EU CE marking declaration of conformity",
                regulatory_basis="EU 2016/425",
                required=True
            ))
        
        # All imports to EU need customs documentation
        documents.append(DocumentRequirement(
            name="EUR-1 Form",
            provider="EU",
            confidence=0.95,
            description="EU form of proof of origin",
            regulatory_basis="EC 2454/93",
            required=True
        ))
        
        return documents


class ComplianceIntegration:
    """Orchestrates multiple compliance providers."""
    
    def __init__(self, mode: ComplianceMode = ComplianceMode.HYBRID):
        self.mode = mode
        self.providers: Dict[str, ComplianceProvider] = {}
    
    def register_provider(self, provider: ComplianceProvider):
        """Register a compliance provider."""
        self.providers[provider.name] = provider
    
    async def get_documents_from_providers(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        product_description: str,
    ) -> Dict[str, DocumentRequirement]:
        """Get documents from all registered providers."""
        
        results = {}
        
        # Run all provider calls concurrently
        tasks = [
            provider.get_required_documents(
                hs_code=hs_code,
                origin_country=origin_country,
                destination_country=destination_country,
                product_description=product_description,
            )
            for provider in self.providers.values()
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for provider, response in zip(self.providers.values(), responses):
            if isinstance(response, Exception):
                logger.error(f"Provider {provider.name} error: {response}")
                continue
            
            for doc in response:
                if doc.name not in results:
                    results[doc.name] = doc
                else:
                    # Keep highest confidence
                    if doc.confidence and (
                        not results[doc.name].confidence or
                        doc.confidence > results[doc.name].confidence
                    ):
                        results[doc.name] = doc
        
        return results


def create_default_integration(
    mode: ComplianceMode = ComplianceMode.HYBRID,
    descartes_api_key: Optional[str] = None,
) -> ComplianceIntegration:
    """Create a compliance integration with default providers."""
    
    integration = ComplianceIntegration(mode=mode)
    
    # Register rule-based providers
    integration.register_provider(USDAProvider())
    integration.register_provider(EuropeanComplianceProvider())
    
    # Register API-based provider if credentials available
    if descartes_api_key:
        integration.register_provider(DescartesProvider(api_key=descartes_api_key))
    
    return integration
