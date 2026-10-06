// src/modules/smu/gestion_smu/GestionSmuToolbar.tsx
//
// Filtros de cabecera y acciones de la tabla de gestión SMU. El export usa
// las mismas filas visibles que la tabla (búsqueda y filtros incluidos).

"use client";

import Button from "@/components/ui/button/Button";
import { DownloadIcon } from "@/icons";
import type {
  ActividadSmuResumen,
  FiltrosActividadSmu,
} from "@/services/smu.service";
import { exportToCsv } from "@/utils/csv";
import { gestionSmuCsvColumns } from "./columns";
import {
  CATEGORIAS_SMU,
  ESTADOS_SMU,
  GESTION_SMU_CONFIG,
  TIPOS_FORMULARIO_SMU,
  type OpcionFiltro,
} from "./constants";

interface GestionSmuToolbarProps {
  filtros: FiltrosActividadSmu;
  onFiltroChange: (campo: keyof FiltrosActividadSmu, valor: string) => void;
  /** Filas que cumplen la búsqueda y los filtros: lo que se exporta. */
  filas: ActividadSmuResumen[];
  /** Total de formularios descargados del servidor (antes de filtrar). */
  total: number;
}

const selectClasses =
  "h-9 w-full rounded-lg border border-gray-300 bg-transparent px-2 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 sm:w-auto dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const Filtro = ({
  etiqueta,
  valor,
  opciones,
  onChange,
}: {
  etiqueta: string;
  valor: string | undefined;
  opciones: OpcionFiltro[];
  onChange: (valor: string) => void;
}) => (
  <select
    aria-label={etiqueta}
    className={selectClasses}
    value={valor ?? ""}
    onChange={(event) => onChange(event.target.value)}
  >
    <option value="">{etiqueta}</option>
    {opciones.map((opcion) => (
      <option key={opcion.valor} value={opcion.valor}>
        {opcion.etiqueta}
      </option>
    ))}
  </select>
);

export const GestionSmuToolbar = ({
  filtros,
  onFiltroChange,
  filas,
  total,
}: GestionSmuToolbarProps) => {
  const exportar = () => {
    if (!filas.length) return;
    exportToCsv(filas, {
      fileName: GESTION_SMU_CONFIG.csvFileName,
      columns: gestionSmuCsvColumns,
    });
  };

  return (
    <div className="flex flex-wrap items-center gap-3">
      <span className="text-sm text-gray-500 dark:text-gray-400">
        {filas.length} de {total} formularios
      </span>

      <Filtro
        etiqueta="Todas las categorías"
        valor={filtros.categoria}
        opciones={CATEGORIAS_SMU}
        onChange={(valor) => onFiltroChange("categoria", valor)}
      />
      <Filtro
        etiqueta="Todos los tipos"
        valor={filtros.tipo_formulario}
        opciones={TIPOS_FORMULARIO_SMU}
        onChange={(valor) => onFiltroChange("tipo_formulario", valor)}
      />
      <Filtro
        etiqueta="Todos los estados"
        valor={filtros.estado}
        opciones={ESTADOS_SMU}
        onChange={(valor) => onFiltroChange("estado", valor)}
      />

      <span title="CSV de las filas filtradas en pantalla. El Excel con el formato de cada formulario está en la columna EXPORTAR.">
        <Button
          variant="outline"
          size="sm"
          className="flex w-full items-center justify-center gap-2 sm:w-auto"
          onClick={exportar}
          startIcon={<DownloadIcon className="h-4 w-4" />}
          disabled={!filas.length}
        >
          Exportar CSV
        </Button>
      </span>
    </div>
  );
};
