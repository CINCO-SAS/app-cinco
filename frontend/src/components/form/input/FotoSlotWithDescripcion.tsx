import React from "react";
import FotoSlotCard from "./FotoSlotCard";

interface FotoSlotWithDescripcionProps {
  /** Número de orden visible en el badge (1-based) */
  index: number;
  /** Nombre/título del slot fotográfico */
  titulo: string;
  /** URL de preview si ya hay una foto cargada */
  previewUrl?: string;
  /** ID único del input file */
  inputId: string;
  /** Callback al seleccionar un archivo ya validado. Recibe File o null al eliminar. */
  onUpload: (file: File | null) => void;
  /** Callback al presionar el botón de eliminar */
  onRemove: () => void;
  /** Tamaño máximo por foto en MB. Por defecto 5 (FOTO_MAX_SIZE_MB). */
  maxSizeMb?: number;

  // ── Descripción de la fotografía ──
  /** Valor actual del campo de descripción */
  descripcion?: string;
  /** Callback cuando cambia el texto de descripción */
  onDescripcionChange: (value: string) => void;
  /** Placeholder del campo de descripción */
  descripcionPlaceholder?: string;
  /** Label opcional sobre el textarea */
  descripcionLabel?: string;
}

/**
 * Contenedor que "acobija" a FotoSlotCard y le agrega de manera fija un slot
 * de textarea para la descripción de la foto.
 *
 * Componente global, reutilizable por cualquier módulo:
 * `import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion"`
 *
 * Diseñado para casos donde el técnico debe ingresar tanto la foto como la
 * explicación detallada de lo que se evidencia.
 */
const FotoSlotWithDescripcion: React.FC<FotoSlotWithDescripcionProps> = ({
  index,
  titulo,
  previewUrl,
  inputId,
  onUpload,
  onRemove,
  maxSizeMb,
  descripcion = "",
  onDescripcionChange,
  descripcionPlaceholder = "Describe el hallazgo o detalle de la foto...",
  descripcionLabel = "Descripción de la evidencia",
}) => {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-gray-200 bg-white p-3 shadow-xs transition-all dark:border-gray-800 dark:bg-white/2">
      {/* Slot de Fotografía */}
      <FotoSlotCard
        index={index}
        titulo={titulo}
        previewUrl={previewUrl}
        inputId={inputId}
        onUpload={onUpload}
        onRemove={onRemove}
        maxSizeMb={maxSizeMb}
      />

      {/* Slot de Descripción permanente */}
      <div className="flex flex-col gap-1 px-1">
        {descripcionLabel && (
          <label className="text-[11px] font-medium text-gray-500 dark:text-gray-400">
            {descripcionLabel}
          </label>
        )}
        <textarea
          rows={2}
          value={descripcion}
          onChange={(e) => onDescripcionChange(e.target.value)}
          placeholder={descripcionPlaceholder}
          className="focus:border-brand-400 focus:ring-brand-500/20 dark:focus:border-brand-500 w-full resize-none rounded-lg border border-gray-200 bg-gray-50/50 px-3 py-2 text-xs text-gray-700 placeholder-gray-400 transition-all focus:bg-white focus:ring-2 focus:outline-none dark:border-gray-700 dark:bg-white/4 dark:text-gray-200 dark:placeholder-gray-500 dark:focus:bg-white/6"
        />
      </div>
    </div>
  );
};

export default FotoSlotWithDescripcion;
