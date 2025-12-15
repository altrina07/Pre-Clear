import { useState, useEffect } from 'react';
import { ShipmentForm } from './ShipmentForm';
import { CheckCircle2, ChevronRight, ChevronLeft } from 'lucide-react';

const steps = [
  { id: 1, label: 'Shipment Basics' },
  { id: 2, label: 'Shipper Info' },
  { id: 3, label: 'Consignee Info' },
  { id: 4, label: 'Packages & Service' },
  { id: 5, label: 'Documents' }
];

export function ShipmentFormMultiStep({ shipment, onNavigate }) {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState(shipment || {});

  const handleNext = () => {
    if (currentStep < steps.length) setCurrentStep(currentStep + 1);
  };

  const handlePrev = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  const isFirstStep = currentStep === 1;
  const isLastStep = currentStep === steps.length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Multi-Step Header with Circles */}
        <div className="mb-12">
          <div className="flex items-center justify-between gap-2 md:gap-4">
            {steps.map((step, idx) => (
              <div key={step.id} className="flex items-center flex-1">
                {/* Step Circle */}
                <button
                  onClick={() => setCurrentStep(step.id)}
                  className={`flex-shrink-0 w-12 h-12 rounded-full font-bold text-sm transition-all duration-300 flex items-center justify-center ${
                    currentStep === step.id
                      ? 'bg-blue-600 text-white shadow-lg scale-110'
                      : currentStep > step.id
                      ? 'bg-green-500 text-white'
                      : 'bg-slate-300 text-slate-700 hover:bg-slate-400'
                  }`}
                >
                  {currentStep > step.id ? <CheckCircle2 className="w-6 h-6" /> : step.id}
                </button>

                {/* Label */}
                <p
                  className={`ml-2 text-xs md:text-sm font-semibold hidden md:block ${
                    currentStep === step.id ? 'text-blue-600' : currentStep > step.id ? 'text-green-600' : 'text-slate-600'
                  }`}
                >
                  {step.label}
                </p>

                {/* Connector Line */}
                {idx < steps.length - 1 && (
                  <div
                    className={`flex-1 h-1 ml-2 md:ml-4 rounded transition-all ${
                      currentStep > step.id ? 'bg-green-500' : 'bg-slate-300'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Form Content */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          {/* Step-specific rendering would go here */}
          <ShipmentForm shipment={formData} onNavigate={onNavigate} currentStep={currentStep} />
        </div>

        {/* Navigation Buttons */}
        <div className="flex gap-4 justify-between items-center">
          <button
            onClick={handlePrev}
            disabled={isFirstStep}
            className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold transition-all ${
              isFirstStep
                ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                : 'bg-slate-600 text-white hover:bg-slate-700 shadow-md hover:shadow-lg'
            }`}
          >
            <ChevronLeft className="w-5 h-5" /> Previous
          </button>

          <div className="text-sm font-medium text-slate-600">
            Step {currentStep} of {steps.length}
          </div>

          <button
            onClick={handleNext}
            disabled={isLastStep}
            className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold transition-all ${
              isLastStep
                ? 'bg-green-600 text-white hover:bg-green-700 shadow-md hover:shadow-lg'
                : 'bg-blue-600 text-white hover:bg-blue-700 shadow-md hover:shadow-lg'
            }`}
          >
            {isLastStep ? 'Submit' : 'Next'} <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
}
