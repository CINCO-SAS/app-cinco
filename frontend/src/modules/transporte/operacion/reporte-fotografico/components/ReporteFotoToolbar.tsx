// src/modules/transporte/operacion/reporte-fotografico/components/ReporteFotoToolbar.tsx
//
// Barra de filtros del reporte fotográfico (F3/B3).
//
// Todo se traduce en parámetros del SERVIDOR (`desde`, `hasta`, `vehiculo`,
// `search`): no se filtra en cliente. La búsqueda va diferida (300 ms) para
// no pegar un `GET` + `COUNT(*)` por tecla.

import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import type { FiltrosReporteFoto } from "../reporteFotoView.hooks";
import {
  RANGOS_RAPIDOS,
  desplazarDias,
  hoyISO,
} from "../reporteFotoView.utils";

interface ReporteFotoToolbarProps {
  total: number;
  filtros: FiltrosReporteFoto;
  actualizarFiltro: (clave: keyof FiltrosReporteFoto, valor: string) => void;
  limpiarFiltros: () => void;
  hayFiltrosActivos: boolean;
  /** Texto del input de búsqueda, sincronizado con `?q=` de la URL. */
  busqueda: string;
  setBusqueda: (valor: string) => void;
  onNuevo: () => void;
}

const CLASES =
  "h-9 rounded-lg border border-gray-300 bg-white px-2.5 text-sm text-gray-700 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const CLASES_RANGO =
  "h-9 rounded-lg border px-2.5 text-sm transition-colors " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20";

export const ReporteFotoToolbar = ({
  total,
  filtros,
  actualizarFiltro,
  limpiarFiltros,
  hayFiltrosActivos,
  busqueda,
  setBusqueda,
  onNuevo,
}: ReporteFotoToolbarProps) => {
  const hoy = hoyISO();

  const aplicarRango = (dias: number) => {
    actualizarFiltro("desde", desplazarDias(hoy, -dias));
    actualizarFiltro("hasta", hoy);
  };

  const rangoActivo = (dias: number) =>
    filtros.desde === desplazarDias(hoy, -dias) && filtros.hasta === hoy;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* --- Rangos rápidos --- */}
      <div className="flex items-center gap-1.5">
        {RANGOS_RAPIDOS.map((rango) => (
          <button
            key={rango.id}
            type="button"
            onClick={() => aplicarRango(rango.dias)}
            className={
              `${CLASES_RANGO} ` +
              (rangoActivo(rango.dias)
                ? "border-brand-500 bg-brand-500 text-white hover:bg-brand-600"
                : "border-gray-300 bg-white text-gray-600 hover:border-brand-400 hover:text-brand-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300 dark:hover:border-brand-500 dark:hover:text-brand-400")
            }
          >
            {rango.etiqueta}
          </button>
        ))}
        <button
          type="button"
          onClick={() => {
            actualizarFiltro("desde", "");
            actualizarFiltro("hasta", "");
          }}
          className={
            `${CLASES_RANGO} ` +
            (!filtros.desde && !filtros.hasta
              ? "border-brand-500 bg-brand-500 text-white hover:bg-brand-600"
              : "border-gray-300 bg-white text-gray-600 hover:border-brand-400 hover:text-brand-600 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300")
          }
        >
          Todo
        </button>
      </div>

      {/* --- Rango libre --- */}
      <input
        type="date"
        value={filtros.desde}
        max={filtros.hasta || undefined}
        onChange={(e) => actualizarFiltro("desde", e.target.value)}
        aria-label="Fecha desde"
        className={CLASES}
      />
      <span className="text-sm text-gray-400">—</span>
      <input
        type="date"
        value={filtros.hasta}
        min={filtros.desde || undefined}
        onChange={(e) => actualizarFiltro("hasta", e.target.value)}
        aria-label="Fecha hasta"
        className={CLASES}
      />

      {/* --- Placa --- */}
      <input
        type="text"
        value={filtros.vehiculo}
        onChange={(e) =>
          actualizarFiltro("vehiculo", e.target.value.toUpperCase())
        }
        placeholder="Placa"
        aria-label="Filtrar por placa"
        className={`${CLASES} w-28`}
      />

      {/* --- Búsqueda (?search=) --- */}
      <Input
        type="search"
        placeholder="Placa, OT, responsable u observación..."
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        className="w-full sm:w-64"
        aria-label="Buscar reportes"
      />

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
        {total} reporte{total === 1 ? "" : "s"}
      </span>

      <Button size="sm" variant="primary" onClick={onNuevo}>
        Nuevo reporte
      </Button>
    </div>
  );
};
