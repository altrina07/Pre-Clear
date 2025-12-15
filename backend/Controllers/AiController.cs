using System.Threading.Tasks;
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Extensions.Logging;
using PreClear.Api.Interfaces;

namespace PreClear.Api.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class AiController : ControllerBase
    {
        private readonly IAiService _ai;
        private readonly IDocumentRepository _docRepo;
        private readonly ILogger<AiController> _logger;

        public AiController(IAiService ai, IDocumentRepository docRepo, ILogger<AiController> logger)
        {
            _ai = ai;
            _docRepo = docRepo;
            _logger = logger;
        }

        public class AnalyzeRequest
        {
            public string Description { get; set; } = string.Empty;
        }

        [HttpPost("analyze")]
        public async Task<IActionResult> Analyze([FromBody] AnalyzeRequest req)
        {
            if (req == null || string.IsNullOrWhiteSpace(req.Description))
                return BadRequest(new { error = "description_required" });

            try
            {
                var result = await _ai.AnalyzeAsync(req.Description);
                return Ok(result);
            }
            catch (ArgumentException aex)
            {
                _logger.LogWarning(aex, "Bad request in AI analyze");
                return BadRequest(new { error = "invalid_input", detail = aex.Message });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Unexpected error during AI analysis");
                return StatusCode(500, new { error = "internal_error", detail = "An unexpected error occurred while analyzing the description." });
            }
        }

        public class HsSuggestRequest
        {
            public string Name { get; set; } = string.Empty;
            public string Category { get; set; } = string.Empty;
            public string Description { get; set; } = string.Empty;
            public int K { get; set; } = 5;
        }

        [HttpPost("hs/suggest")]
        public async Task<IActionResult> SuggestHs([FromBody] HsSuggestRequest req)
        {
            try
            {
                var suggestions = await _ai.SuggestHsAsync(req?.Name ?? string.Empty, req?.Category ?? string.Empty, req?.Description ?? string.Empty, req?.K ?? 5);
                // Map to response
                var result = suggestions.Select(s => new { hscode = s.HsCode, description = s.Description, score = s.Score }).ToList();
                return Ok(new { suggestions = result });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error while suggesting HS codes");
                return StatusCode(500, new { error = "internal_error" });
            }
        }

        public class DocumentPredictRequest
        {
            public string ProductCategory { get; set; } = string.Empty;
            public string ProductDescription { get; set; } = string.Empty;
            public string HsCode { get; set; } = string.Empty;
            public string OriginCountry { get; set; } = string.Empty;
            public string DestinationCountry { get; set; } = string.Empty;
            public string PackageTypeWeight { get; set; } = string.Empty;
            public string ModeOfTransport { get; set; } = string.Empty;
            public bool HtsFlag { get; set; } = false;
            public long ShipmentId { get; set; } = 0;
        }

        [HttpPost("documents/predict")]
        public async Task<IActionResult> SuggestDocuments([FromBody] DocumentPredictRequest req)
        {
            try
            {
                if (req == null)
                {
                    return BadRequest(new { error = "request_required" });
                }

                var aiRequest = new PreClear.Api.Services.DocumentPredictionRequest
                {
                    OriginCountry = req.OriginCountry ?? string.Empty,
                    DestinationCountry = req.DestinationCountry ?? string.Empty,
                    HsCode = req.HsCode ?? string.Empty,
                    HtsFlag = req.HtsFlag,
                    ProductCategory = req.ProductCategory ?? string.Empty,
                    ProductDescription = req.ProductDescription ?? string.Empty,
                    PackageTypeWeight = req.PackageTypeWeight ?? string.Empty,
                    ModeOfTransport = req.ModeOfTransport ?? string.Empty,
                    ConfidenceThreshold = 0.3f
                };

                var result = await _ai.PredictRequiredDocumentsAsync(aiRequest);
                return Ok(result);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error while suggesting required documents");
                return StatusCode(500, new { error = "internal_error" });
            }
        }

        [HttpPost("required-documents")]
        public async Task<IActionResult> SaveRequiredDocuments([FromBody] DocumentPredictRequest req)
        {
            try
            {
                if (req == null || req.ShipmentId == 0)
                {
                    return BadRequest(new { error = "shipment_id_required" });
                }

                var aiRequest = new PreClear.Api.Services.DocumentPredictionRequest
                {
                    OriginCountry = req.OriginCountry ?? string.Empty,
                    DestinationCountry = req.DestinationCountry ?? string.Empty,
                    HsCode = req.HsCode ?? string.Empty,
                    HtsFlag = req.HtsFlag,
                    ProductCategory = req.ProductCategory ?? string.Empty,
                    ProductDescription = req.ProductDescription ?? string.Empty,
                    PackageTypeWeight = req.PackageTypeWeight ?? string.Empty,
                    ModeOfTransport = req.ModeOfTransport ?? string.Empty,
                    ConfidenceThreshold = 0.3f
                };

                var prediction = await _ai.PredictRequiredDocumentsAsync(aiRequest);

                // Persist each predicted document as required and not uploaded
                var docsToSave = new List<PreClear.Api.Models.ShipmentDocument>();
                foreach (var name in prediction.RequiredDocuments ?? Array.Empty<string>())
                {
                    var doc = new PreClear.Api.Models.ShipmentDocument
                    {
                        ShipmentId = req.ShipmentId,
                        DocumentType = PreClear.Api.Models.DocumentType.Other,
                        Name = name,
                        FileUrl = null,
                        UploadedBy = null,
                        VerifiedByBroker = false,
                        Required = true,
                        Uploaded = false,
                        UploadedAt = System.DateTime.UtcNow,
                        Version = 1
                    };

                    var saved = await _docRepo.AddAsync(doc);
                    docsToSave.Add(saved);
                }

                return Ok(new { saved = docsToSave.Count, documents = docsToSave.Select(d => new { d.Id, d.Name, d.Required, d.Uploaded }) });
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Error while saving required documents");
                return StatusCode(500, new { error = "internal_error" });
            }
        }

        [HttpGet("hs/sections")]
        public IActionResult GetHsSections()
        {
            try
            {
                // Locate sections.csv under backend/AI/datasets
                var baseDir = Directory.GetCurrentDirectory();
                var candidate = Path.Combine(baseDir, "AI", "datasets", "sections.csv");
                if (!System.IO.File.Exists(candidate))
                {
                    return NotFound(new { error = "sections_not_found" });
                }

                var lines = System.IO.File.ReadAllLines(candidate);
                if (lines.Length == 0) return Ok(Array.Empty<object>());

                var rows = new List<object>();
                for (int i = 1; i < lines.Length; i++)
                {
                    var line = lines[i];
                    // Handle quoted fields: split by comma but respect quotes
                    var parts = new System.Collections.Generic.List<string>();
                    var current = new System.Text.StringBuilder();
                    var inQuotes = false;
                    foreach (var ch in line)
                    {
                        if (ch == '"') inQuotes = !inQuotes;
                        else if (ch == ',' && !inQuotes)
                        {
                            parts.Add(current.ToString().Trim().Trim('"'));
                            current.Clear();
                        }
                        else current.Append(ch);
                    }
                    if (current.Length > 0) parts.Add(current.ToString().Trim().Trim('"'));

                    string code = parts.Count > 0 ? parts[0].Trim() : i.ToString();
                    string title = parts.Count > 1 ? parts[1].Trim().Trim('"') : "";
                    // Capitalize first letter of each word
                    title = System.Globalization.CultureInfo.CurrentCulture.TextInfo.ToTitleCase(title.ToLower());
                    // Remove any remaining quotes
                    title = title.Replace("\"", "");
                    rows.Add(new { code, title });
                }

                return Ok(rows);
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Failed to read HS sections");
                return StatusCode(500, new { error = "internal_error" });
            }
        }
    }
}

