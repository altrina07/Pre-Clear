import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Hook for fetching required document recommendations
 * Calls POST /api/ai/documents/predict with shipment details
 * Returns debounced predictions with confidence scores and provenance
 */
export const useRequiredDocuments = (
  shipmentData = null,
  debounceMs = 500,
  enabled = true
) => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [metadata, setMetadata] = useState(null);
  const debounceTimer = useRef(null);

  /**
   * Fetch document recommendations from backend
   */
  const fetchDocuments = useCallback(async (data) => {
    if (!data || !enabled) return;

    setLoading(true);
    setError(null);

    try {
      // Map frontend field names to API format expected by backend
      const request = {
        product_category: data.productCategory || data.category || '',
        product_description: data.productDescription || '',
        hs_code: data.hsCode || '',
        origin_country: data.originCountry || data.shipper?.country || '',
        destination_country: data.destinationCountry || data.consignee?.country || '',
        package_type_weight: data.packageTypeWeight || '',
        mode_of_transport: data.mode || '',
        hts_flag: !!data.htsFlag
      };

      const response = await fetch('/api/ai/documents/predict', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const result = await response.json();

      // result.required_documents = ["Invoice", "Packing List"]
      const docs = (result.required_documents || []).map((name) => ({
        name,
        confidence: (result.confidence_scores && result.confidence_scores[name]) || 0,
        provenance: (result.provenance && result.provenance[name]) || 'ml',
      }));

      // Sort by confidence descending
      const sorted = docs.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));

      setDocuments(sorted);
      setMetadata({
        mode: result.mode || 'ml',
        modelVersion: result.model_version || '1.0',
        timestamp: result.timestamp || new Date().toISOString(),
        confidenceThreshold: result.confidence_threshold || 0.3,
      });
    } catch (err) {
      setError(err.message || 'Failed to fetch document recommendations');
      setDocuments([]);
      setMetadata(null);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  /**
   * Debounced version of fetchDocuments
   * Cancels previous requests if shipment data changes
   */
  const debouncedFetch = useCallback((data) => {
    // Clear existing timer
    if (debounceTimer.current) {
      clearTimeout(debounceTimer.current);
    }

    // Set new debounce timer
    debounceTimer.current = setTimeout(() => {
      fetchDocuments(data);
    }, debounceMs);
  }, [fetchDocuments, debounceMs]);

  /**
   * Effect to trigger debounced fetch when shipmentData changes
   */
  useEffect(() => {
    if (shipmentData && enabled) {
      debouncedFetch(shipmentData);
    }

    // Cleanup timer on unmount
    return () => {
      if (debounceTimer.current) {
        clearTimeout(debounceTimer.current);
      }
    };
  }, [shipmentData, enabled, debouncedFetch]);

  /**
   * Manual refresh function
   */
  const refresh = useCallback(() => {
    if (shipmentData) {
      fetchDocuments(shipmentData);
    }
  }, [shipmentData, fetchDocuments]);

  return {
    documents,
    loading,
    error,
    metadata,
    refresh,
  };
};

export default useRequiredDocuments;
