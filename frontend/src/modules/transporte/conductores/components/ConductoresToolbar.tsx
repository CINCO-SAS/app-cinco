// src/modules/transporte/conductores/components/ConductoresToolbar.tsx
//
// Barra de filtros de Conductores. Deliberadamente liviana (misma gramática
// que FlotaToolbar): selects finos + contador + alta.
//
// El semáforo `vigencia` filtra sobre el dato YA calculado por el servidor
// (`estado_licencia`), igual que SOAT/CDA en flota: aquí no se compara ninguna
// fecha.

import Button from "@/components/ui/button/Button";
import type { FiltrosConductores } from "../conductoresView.hooks";
import { ETIQUETAS_VINCULACION } from "../conductoresView.utils";

interface ConductoresToolbarProps {
  total: number;
  filtros: FiltrosConductores;
  actualizarFiltro: (clave: keyof FiltrosConductores, valor: string) => void;
  limpiarFiltros: () => void;
  hayFiltrosActivos: boolean;
  onNuevo: () => void;
}

const SELECT_CLASES =
  "h-9 rounded-lg border border-gray-300 bg-white px-2.5 text-sm text-gray-700 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

export const ConductoresToolbar = ({
  total,
  filtros,
  actualizarFiltro,
  limpiarFiltros,
  hayFiltrosActivos,
  onNuevo,
}: ConductoresToolbarProps) => (
  <div className="flex flex-wrap items-center gap-2">
    <select
      value={filtros.tipo_vinculacion}
      onChange={(e) => actualizarFiltro("tipo_vinculacion", e.target.value)}
      className={SELECT_CLASES}
      aria-label="Filtrar por tipo de vínculo"
    >
      <option value="">Todos los vínculos</option>
      {Object.entries(ETIQUETAS_VINCULACION).map(([valor, etiqueta]) => (
        <option key={valor} value={valor}>
          {etiqueta}
        </option>
      ))}
    </select>

    <select
      value={filtros.activo}
      onChange={(e) => actualizarFiltro("activo", e.target.value)}
      className={SELECT_CLASES}
      aria-label="Filtrar por estado"
    >
      <option value="">Activos e inactivos</option>
      <option value="true">Solo activos</option>
      <option value="false">Solo inactivos</option>
    </select>

    <select
      value={filtros.vigencia}
      onChange={(e) => actualizarFiltro("vigencia", e.target.value)}
      className={SELECT_CLASES}
      aria-label="Filtrar por vigencia de licencia"
    >
      <option value="">Cualquier licencia</option>
      <option value="VIGENTE">Licencia vigente</option>
      <option value="POR_VENCER">Licencia por vencer</option>
      <option value="VENCIDA">Licencia vencida</option>
      <option value="SIN_REGISTRO">Sin registro</option>
    </select>

    {hayFiltrosActivos && (
      <button
        type="button"
        onClick={limpiarFiltros}
        className="text-sm text-brand-500 hover:text-brand-600 dark:text-brand-400"
      >
        Limpiar
      </button>
    )}

    <span className="ml-auto text-sm text-gray-500 dark:text-gray-400">
      {total} conductor{total === 1 ? "" : "es"}
    </span>

    <Button size="sm" variant="primary" onClick={onNuevo}>
      Nuevo conductor
    </Button>
  </div>
);
