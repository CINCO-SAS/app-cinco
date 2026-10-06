import React from "react";
import { Trash2 } from "lucide-react";

interface DynamicItemCardProps {
  /** Texto del badge superior, ej: "COMPRESOR 1", "MANEJADORA 2" */
  label: string;
  /** Callback para eliminar el item. Si no se pasa, no muestra el botón. */
  onRemove?: () => void;
  children: React.ReactNode;
}

/**
 * Card estándar para items dinámicos en formularios SMU.
 * Muestra un badge con el label, un botón opcional de eliminar
 * y un contenedor para los campos del item.
 */
const DynamicItemCard: React.FC<DynamicItemCardProps> = ({ label, onRemove, children }) => {
  return (
    <div className="relative rounded-xl border border-gray-200 bg-gray-50/40 p-5 transition-all dark:border-gray-800 dark:bg-white/2">
      <div className="mb-4 flex items-center justify-between">
        <span className="rounded-md bg-brand-500/10 px-2.5 py-1 text-xs font-bold text-brand-600 dark:text-brand-400">
          {label}
        </span>
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-error-500 transition-all hover:bg-error-50 dark:hover:bg-error-500/10"
            title={`Eliminar ${label}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
            Eliminar
          </button>
        )}
      </div>
      {children}
    </div>
  );
};

export default DynamicItemCard;
