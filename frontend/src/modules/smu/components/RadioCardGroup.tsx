"use client";

import React from "react";

export interface RadioCardOption<T extends string> {
  value: T;
  label: string;
  descripcion?: string;
}

interface RadioCardGroupProps<T extends string> {
  name: string;
  label?: string;
  options: RadioCardOption<T>[];
  value: T | null;
  onChange: (value: T) => void;
  cols?: 2 | 3 | 4;
}

function RadioCardGroup<T extends string>({
  name,
  label,
  options,
  value,
  onChange,
  cols = 2,
}: RadioCardGroupProps<T>) {
  const colClass = {
    2: "sm:grid-cols-2",
    3: "sm:grid-cols-3",
    4: "sm:grid-cols-4",
  }[cols];

  return (
    <div className="flex flex-col gap-3">
      {label && (
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
          <span className="text-error-500 ml-1">*</span>
        </p>
      )}

      <div className={`grid grid-cols-1 gap-3 ${colClass}`}>
        {options.map((opcion) => {
          const isSelected = value === opcion.value;
          return (
            <label
              key={opcion.value}
              htmlFor={`${name}-${opcion.value}`}
              className={`flex cursor-pointer flex-col gap-1 rounded-xl border px-5 py-4 transition-all duration-200 select-none ${
                isSelected
                  ? "border-brand-500 bg-brand-50 dark:border-brand-400 dark:bg-brand-500/10"
                  : "border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:bg-white/3 dark:hover:border-gray-600 dark:hover:bg-white/5"
              } `}
            >
              <input
                type="radio"
                id={`${name}-${opcion.value}`}
                name={name}
                value={opcion.value}
                checked={isSelected}
                onChange={() => onChange(opcion.value)}
                className="sr-only"
              />

              <span className="flex items-center gap-2.5">
                {/* Indicador radio custom */}
                <span
                  className={`flex h-4.5 w-4.5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-all duration-200 ${
                    isSelected
                      ? "border-brand-500 dark:border-brand-400"
                      : "border-gray-300 dark:border-gray-600"
                  } `}
                >
                  {isSelected && (
                    <span className="bg-brand-500 dark:bg-brand-400 h-2 w-2 rounded-full" />
                  )}
                </span>
                <span
                  className={`text-sm font-semibold transition-colors duration-200 ${
                    isSelected
                      ? "text-brand-600 dark:text-brand-400"
                      : "text-gray-700 dark:text-gray-300"
                  } `}
                >
                  {opcion.label}
                </span>
              </span>

              {opcion.descripcion && (
                <span className="pl-7 text-xs text-gray-500 dark:text-gray-400">
                  {opcion.descripcion}
                </span>
              )}
            </label>
          );
        })}
      </div>
    </div>
  );
}

export default RadioCardGroup;
