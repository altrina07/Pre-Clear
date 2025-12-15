import { ChevronDown } from 'lucide-react';

export function HSSectionDropdown({ value, onChange, options, label = "Category", required = false, disabled = false }) {
  return (
    <div className="w-full">
      <label className="block text-sm font-medium text-slate-700 mb-2">
        {label}
        {required && <span className="text-red-600">*</span>}
      </label>
      <div className="relative">
        <select
          value={value}
          onChange={onChange}
          required={required}
          disabled={disabled}
          className={`w-full px-4 py-3 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500 transition-all appearance-none cursor-pointer ${disabled ? 'bg-slate-100 text-slate-500 cursor-not-allowed' : 'bg-white text-slate-900 shadow-sm hover:shadow-md border border-slate-200'}`}
        >
          <option value="">-- Select {label} --</option>
          {options && options.map((opt, idx) => {
            const displayText = opt.title || opt.label || opt.code || '';
            return (
              <option key={idx} value={opt.code || opt.value || idx}>
                {displayText}
              </option>
            );
          })}
        </select>
        <div className="pointer-events-none absolute right-4 top-3.5 flex items-center px-2 text-slate-400">
          <ChevronDown className="h-5 w-5" />
        </div>
      </div>
      {/* Display selected section description */}
      {value && options && (
        <div className="mt-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
          {(() => {
            const selected = options.find(opt => (opt.code || opt.value || '') === value);
            if (selected) {
              return (
                <p className="text-sm text-blue-900 leading-relaxed break-words">
                  <strong>Selected:</strong> {selected.title || selected.label || selected.code}
                </p>
              );
            }
            return null;
          })()}
        </div>
      )}
    </div>
  );
}
