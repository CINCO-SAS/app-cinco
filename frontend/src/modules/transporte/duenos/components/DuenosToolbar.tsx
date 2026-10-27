// src/modules/transporte/duenos/components/DuenosToolbar.tsx
//
// Barra de herramientas y filtros para la vista de Dueños de Vehículos.

import Button from "@/components/ui/button/Button";
import type { FiltrosDuenos } from "../duenosView.hooks";

interface DuenosToolbarProps {
  total: number;
  filtros: FiltrosDuenos;
  actualizarFiltro: (clave: keyof FiltrosDuenos, valor: string) => void;
  limpiarFiltros: () => void;
  hayFiltrosActivos: boolean;
  onNuevo: () => void;
}

const SELECT_CLASES =
  "h-9 rounded-lg border border-gray-300 bg-white px-2.5 text-sm text-gray-700 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

export const DuenosToolbar = ({
  total,
  filtros,
  actualizarFiltro,
  limpiarFiltros,
  hayFiltrosActivos,
  onNuevo,
}: DuenosToolbarProps) => (
  <div className="flex flex-wrap items-center gap-2">
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
      {total} dueño{total === 1 ? "" : "s"}
    </span>

    <Button size="sm" variant="primary" onClick={onNuevo}>
      Nuevo dueño
    </Button>
  </div>
);
