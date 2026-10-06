"use client";

import React from "react";
import { ChevronLeft, ChevronRight, Check } from "lucide-react";

export interface StepItem {
  id: string;
  title: string;
  shortTitle?: string;
  icon?: React.ReactNode;
}

interface FormStepSliderProps {
  steps: StepItem[];
  currentStep: number;
  onStepChange: (stepIndex: number) => void;
  children: React.ReactNode;
  onPrev?: () => void;
  onNext?: () => void;
  onSubmit?: () => void;
  isFirstStep?: boolean;
  isLastStep?: boolean;
  submitLabel?: string;
  isSubmitting?: boolean;
}

export const FormStepSlider: React.FC<FormStepSliderProps> = ({
  steps,
  currentStep,
  onStepChange,
  children,
  onPrev,
  onNext,
  onSubmit,
  isFirstStep = currentStep === 0,
  isLastStep = currentStep === steps.length - 1,
  submitLabel = "Guardar y Finalizar",
  isSubmitting = false,
}) => {
  const handleNext = () => {
    if (isLastStep) {
      onSubmit?.();
    } else {
      if (onNext) {
        onNext();
      } else {
        onStepChange(Math.min(currentStep + 1, steps.length - 1));
      }
    }
  };

  const handlePrev = () => {
    if (onPrev) {
      onPrev();
    } else {
      onStepChange(Math.max(currentStep - 1, 0));
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {/* ── Stepper Header Visual Responsivo (Acomoda todas las secciones) ── */}
      <div className="rounded-2xl border border-gray-200 bg-white p-4 sm:p-5 dark:border-gray-800 dark:bg-white/3">
        {/* Barra de progreso visual continua */}
        <div className="relative mb-4 h-1.5 w-full overflow-hidden rounded-full bg-gray-100 dark:bg-gray-800">
          <div
            className="h-full bg-brand-500 transition-all duration-300 ease-out dark:bg-brand-400"
            style={{
              width: `${((currentStep + 1) / steps.length) * 100}%`,
            }}
          />
        </div>

        {/* Pasos organizados en cuadrícula responsiva que se ajusta a pantalla */}
        <div className="grid grid-cols-4 gap-1.5 sm:grid-cols-4 md:grid-cols-8">
          {steps.map((step, index) => {
            const isCompleted = index < currentStep;
            const isCurrent = index === currentStep;

            return (
              <button
                key={step.id}
                type="button"
                onClick={() => onStepChange(index)}
                title={step.title}
                className={`group flex flex-col items-center justify-center gap-1 rounded-xl p-2 text-center transition-all duration-200 ${
                  isCurrent
                    ? "bg-brand-50 text-brand-600 ring-1 ring-brand-500/30 dark:bg-brand-500/10 dark:text-brand-400"
                    : isCompleted
                      ? "text-gray-700 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-white/5"
                      : "text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-400"
                }`}
              >
                <span
                  className={`flex h-6 w-6 items-center justify-center rounded-lg text-xs font-bold transition-all ${
                    isCurrent
                      ? "bg-brand-500 text-white shadow-xs dark:bg-brand-400 dark:text-gray-900"
                      : isCompleted
                        ? "bg-brand-100 text-brand-700 dark:bg-brand-500/20 dark:text-brand-300"
                        : "bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500"
                  }`}
                >
                  {isCompleted ? <Check className="h-3.5 w-3.5" /> : index + 1}
                </span>

                {/* Título adaptable */}
                <span className="w-full truncate text-[11px] font-medium leading-tight">
                  {step.shortTitle || step.title}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Contenedor del paso activo ── */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 transition-all duration-200 dark:border-gray-800 dark:bg-white/3">
        {children}
      </div>

      {/* ── Barra de navegación inferior ── */}
      <div className="flex flex-col-reverse items-center justify-between gap-3 sm:flex-row">
        <button
          type="button"
          onClick={handlePrev}
          disabled={isFirstStep || isSubmitting}
          className={`inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 shadow-theme-xs transition-all hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700`}
        >
          <ChevronLeft className="h-4 w-4" />
          Anterior
        </button>

        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          Sección {currentStep + 1} de {steps.length} · {steps[currentStep]?.title}
        </span>

        <button
          type="button"
          onClick={handleNext}
          disabled={isSubmitting}
          className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-medium text-white shadow-theme-xs transition-all hover:bg-brand-600 active:scale-[0.99] disabled:cursor-not-allowed disabled:opacity-50 dark:bg-brand-500 dark:hover:bg-brand-600"
        >
          {isLastStep ? (
            <span>{isSubmitting ? "Guardando..." : submitLabel}</span>
          ) : (
            <>
              Siguiente
              <ChevronRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

export default FormStepSlider;
