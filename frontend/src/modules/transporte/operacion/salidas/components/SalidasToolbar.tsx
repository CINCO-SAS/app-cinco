// src/modules/transporte/operacion/salidas/components/SalidasToolbar.tsx
//
// Barra de filtros de Salidas (B1: rango de fechas + rangos rápidos).
//
// Todos los controles se traducen en parámetros del SERVIDOR (`desde`,
// `hasta`, `estado`, `search`): no se filtra en cliente porque hay ~253 mil
// filas. La búsqueda además va diferida (300 ms) para no pegar un `GET` +
// `COUNT(*)` por tecla.
//
// No hay select de área ni de conductor: `?search=` ya cubre placa, cédula,
// nombre, área y observación, así que un select de área (que además exigiría
// cargar un catálogo inexistente) solo añadiría ruido.

import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import { ESTADOS_SALIDA } from "@/types/transporte.types";
import type { FiltrosSalidas } from "../salidasView.hooks";
import {
  RANGOS_RAPIDOS,
  desplazarDias,
  ETIQUETAS_ESTADO,
  hoyISO,
} from "../salidasView.utils";

interface SalidasToolbarProps {
  total: number;
  filtros: FiltrosSalidas;
  actualizarFiltro: (clave: keyof FiltrosSalidas, valor: string) => void;
  limpiarFiltros: () => void;
  hayFiltrosActivos: boolean;
  /** Texto del input de búsqueda, sincronizado con `?q=` de la URL. */
  busqueda: string;
  setBusqueda: (valor: string) => void;
  /** S6: alta de salida. */
  onNuevo: () => void;
  /** Ítem L · nº de filas seleccionadas en la página (B12). */
  seleccionCantidad: number;
  onAprobarLote: () => void;
  onLimpiarSeleccion: () => void;
}

const CLASES =
  "h-9 rounded-lg border border-gray-300 bg-white px-2.5 text-sm text-gray-700 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const CLASES_RANGO =
  "h-9 rounded-lg border px-2.5 text-sm transition-colors " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20";

export const SalidasToolbar = ({
  total,
  filtros,
  actualizarFiltro,
  limpiarFiltros,
  hayFiltrosActivos,
  busqueda,
  setBusqueda,
  onNuevo,
  seleccionCantidad,
  onAprobarLote,
  onLimpiarSeleccion,
}: SalidasToolbarProps) => {
  const hoy = hoyISO();

  /** B1: "Hoy" / "7 días" / "30 días" = desde (hoy − n) hasta hoy. */
  const aplicarRango = (dias: number) => {
    actualizarFiltro("desde", desplazarDias(hoy, -dias));
    actualizarFiltro("hasta", hoy);
  };

  const rangoActivo = (dias: number) =>
    filtros.desde === desplazarDias(hoy, -dias) && filtros.hasta === hoy;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {/* --- Rangos rápidos (B1) --- */}
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

      {/* --- Estado --- */}
      <select
        value={filtros.estado}
        onChange={(e) => actualizarFiltro("estado", e.target.value)}
        className={CLASES}
        aria-label="Filtrar por estado"
      >
        {/* Vacío = el servidor EXCLUYE los eliminados (ver `listar()`). */}
        <option value="">Sin eliminados</option>
        {ESTADOS_SALIDA.map((estado) => (
          <option key={estado} value={estado}>
            {ETIQUETAS_ESTADO[estado]}
          </option>
        ))}
      </select>

      {/* --- Búsqueda (?search=) --- */}
      <Input
        type="search"
        placeholder="Placa, cédula, nombre, área u observación..."
        value={busqueda}
        onChange={(e) => setBusqueda(e.target.value)}
        className="w-full sm:w-64"
        aria-label="Buscar salidas"
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

      {/* Ítem L (B12): solo aparece con selección, para no ensanchar la
          barra de filtros en el uso diario. */}
      {seleccionCantidad > 0 && (
        <span className="flex items-center gap-2">
          <Button size="sm" variant="primary" onClick={onAprobarLote}>
            Aprobar {seleccionCantidad}
          </Button>
          <button
            type="button"
            onClick={onLimpiarSeleccion}
            className="text-sm text-brand-500 hover:text-brand-600 dark:text-brand-400"
          >
            Quitar selección
          </button>
        </span>
      )}

      <span className="ml-auto text-sm text-gray-500 dark:text-gray-400">
        {total} salida{total === 1 ? "" : "s"}
      </span>

      <Button size="sm" variant="primary" onClick={onNuevo}>
        Nueva salida
      </Button>
    </div>
  );
};
