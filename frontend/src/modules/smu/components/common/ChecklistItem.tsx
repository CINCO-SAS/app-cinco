import React from "react";
import { CheckCircle2, XCircle, MinusCircle } from "lucide-react";

export type ChecklistEstado = "Si" | "No" | "No Aplica";

interface ChecklistItemProps {
  numero: number;
  parametro: string;
  value: ChecklistEstado;
  onChange: (estado: ChecklistEstado) => void;
}

/**
 * Fila individual del checklist de inspección en formularios SMU.
 * Muestra el número, el texto del parámetro y los botones Sí / No / N/A.
 */
const ChecklistItem: React.FC<ChecklistItemProps> = ({ numero, parametro, value, onChange }) => {
  const btnBase =
    "inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold transition-all";
  const btnInactive =
    "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700";

  return (
    <div className="flex flex-col justify-between gap-3 p-3.5 transition-all hover:bg-gray-50/50 sm:flex-row sm:items-center dark:hover:bg-white/1">
      {/* Número + texto */}
      <div className="flex items-start gap-3 pr-2">
        <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gray-100 text-[10px] font-bold text-gray-600 dark:bg-gray-800 dark:text-gray-300">
          {numero}
        </span>
        <p className="text-xs font-medium text-gray-700 dark:text-gray-200">{parametro}</p>
      </div>

      {/* Botones de estado */}
      <div className="flex shrink-0 items-center gap-1 self-end sm:self-auto">
        <button
          type="button"
          onClick={() => onChange("Si")}
          className={`${btnBase} ${
            value === "Si"
              ? "bg-success-500 text-white shadow-xs dark:bg-success-600"
              : btnInactive
          }`}
        >
          <CheckCircle2 className="h-3 w-3" />
          Sí
        </button>

        <button
          type="button"
          onClick={() => onChange("No")}
          className={`${btnBase} ${
            value === "No"
              ? "bg-error-500 text-white shadow-xs dark:bg-error-600"
              : btnInactive
          }`}
        >
          <XCircle className="h-3 w-3" />
          No
        </button>

        <button
          type="button"
          onClick={() => onChange("No Aplica")}
          className={`${btnBase} ${
            value === "No Aplica"
              ? "bg-gray-600 text-white shadow-xs dark:bg-gray-700"
              : btnInactive
          }`}
        >
          <MinusCircle className="h-3 w-3" />
          N/A
        </button>
      </div>
    </div>
  );
};

export default ChecklistItem;
