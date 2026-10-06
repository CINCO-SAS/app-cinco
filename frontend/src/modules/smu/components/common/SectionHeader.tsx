import React from "react";

interface SectionHeaderProps {
  title: string;
  description?: string;
  /** Contenido extra a la derecha (ej: badge contador, botón global) */
  action?: React.ReactNode;
}

/**
 * Encabezado estándar para cada sección de los formularios SMU.
 * Muestra título, descripción opcional y un slot de acción a la derecha.
 */
const SectionHeader: React.FC<SectionHeaderProps> = ({ title, description, action }) => {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">{title}</h4>
        {description && (
          <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
        )}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
};

export default SectionHeader;
