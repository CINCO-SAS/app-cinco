// src/modules/transporte/flota/components/FlotaToolbar.tsx
//
// Barra de filtros de Flota. Deliberadamente liviana: una sola línea de
// selects. Los KPIs NO viven aquí porque compiten visualmente con los
// filtros dentro de la tarjeta de la tabla; están en `FlotaKpis`, justo
// encima de la tabla.

import type { FiltrosFlota } from "../flotaView.hooks";
import { ETIQUETAS_TIPO_CONTRATO } from "../flotaView.utils";

interface FlotaToolbarProps {
  filtros: FiltrosFlota;
  actualizarFiltro: (clave: keyof FiltrosFlota, valor: string) => void;
  limpiarFiltros: () => void;
  hayFiltrosActivos: boolean;
}

const SELECT_CLASES =
  "h-9 rounded-lg border border-gray-300 bg-white px-2.5 text-sm text-gray-700 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

export const FlotaToolbar = ({
  filtros,
  actualizarFiltro,
  limpiarFiltros,
  hayFiltrosActivos,
}: FlotaToolbarProps) => (
  <div className="flex flex-wrap items-center gap-2">
    <select
      value={filtros.tipo_contrato}
      onChange={(e) => actualizarFiltro("tipo_contrato", e.target.value)}
      className={SELECT_CLASES}
      aria-label="Filtrar por tipo de contrato"
    >
      <option value="">Todos los contratos</option>
      {Object.entries(ETIQUETAS_TIPO_CONTRATO).map(([valor, etiqueta]) => (
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
      aria-label="Filtrar por vigencia documental"
    >
      <option value="">Cualquier vigencia</option>
      <option value="AL_DIA">Documentos al día</option>
      <option value="POR_VENCER">Al menos uno por vencer</option>
      <option value="VENCIDA">Al menos uno vencido</option>
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
  </div>
);
