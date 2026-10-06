import React from "react";
import { Plus } from "lucide-react";

interface AddItemButtonProps {
  label: string;
  onClick: () => void;
  className?: string;
}

/**
 * Botón estándar para agregar un elemento dinámico (compresor, manejadora, etc.)
 * en los formularios SMU.
 */
const AddItemButton: React.FC<AddItemButtonProps> = ({ label, onClick, className }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-lg border border-brand-200 bg-brand-50 px-3.5 py-2 text-xs font-medium text-brand-600 transition-all hover:bg-brand-100 dark:border-brand-500/30 dark:bg-brand-500/10 dark:text-brand-400 dark:hover:bg-brand-500/20 ${className ?? ""}`}
    >
      <Plus className="h-3.5 w-3.5" />
      {label}
    </button>
  );
};

export default AddItemButton;
