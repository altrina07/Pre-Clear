import { Sparkles, Check } from 'lucide-react';

export function HsSuggestionPanel({
  suggestions,
  loading,
  onSelect,
  selectedCode
}) {
  if (!suggestions || suggestions.length === 0) {
    return null;
  }

  return (
    <div className="mt-6 p-6 rounded-2xl shadow-md" style={{ background: '#FBF9F6', border: 'none' }}>
      <div className="flex items-center gap-3 mb-4">
        <Sparkles className="w-5 h-5" style={{ color: '#2F1B17' }} />
        <h4 className="font-semibold text-lg" style={{ color: '#2F1B17' }}>
          AI-Suggested HS Codes
        </h4>
      </div>

      {loading && (
        <div className="flex items-center gap-3 p-4 bg-white rounded-lg border border-slate-200 animate-pulse">
          <div className="w-3 h-3 rounded-full" style={{ background: '#2F1B17' }} />
          <span className="text-sm" style={{ color: '#2F1B17' }}>
            Finding HS codes...
          </span>
        </div>
      )}

      {!loading && (
        <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => onSelect(s.code || s.hscode)}
              className="w-full text-left p-4 rounded-xl transition-all transform hover:scale-105 active:scale-95"
              style={{
                background: selectedCode === (s.code || s.hscode) ? '#EAD8C3' : '#FFFFFF',
                border: '2px solid #D4C5B9',
                color: '#2F1B17'
              }}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-base">
                    {s.code || s.hscode}
                  </div>
                  <p className="text-sm mt-1 break-words">
                    {s.description || 'No description'}
                  </p>
                     {/* Match score display removed per user request */}
                </div>
                {selectedCode === (s.code || s.hscode) && (
                  <Check className="w-5 h-5 flex-shrink-0 mt-1" style={{ color: '#2F1B17' }} />
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
