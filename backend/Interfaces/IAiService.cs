namespace PreClear.Api.Interfaces
{
    public interface IAiService
    {
        System.Threading.Tasks.Task<PreClear.Api.Models.AiResultDto> AnalyzeAsync(string description);
        System.Threading.Tasks.Task<System.Collections.Generic.List<PreClear.Api.Services.AiService.HsSuggestion>> SuggestHsAsync(string name, string category, string description, int k = 5);
        System.Threading.Tasks.Task<PreClear.Api.Services.DocumentPredictionResponse> PredictRequiredDocumentsAsync(PreClear.Api.Services.DocumentPredictionRequest request);
    }
}
