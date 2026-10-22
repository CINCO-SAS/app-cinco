// src/modules/transporte/informes/components/InformeToolbar.tsx
//
// Selector de período yerruptor "Aprobados" de la pantalla de Informes.
//
// Un solo selector de período para TODA la pantalla (año · mes · día), como
// el calendario único del legacy: de ahí que mover el mes recolocque el día,
// y no que cada bloque tenga su propio calendario.
//
// El interruptor "Aprobados" solo afecta al bloque Mes — el backend lo
// admite en `/informes/area/` y no en `/informes/dia/`.

import { MESES } from "../informesView.utils";

interface InformeToolbarProps {
  anio: number;
  mes: number;
  dia: number;
  /** Último día válido del mes (limita el selector de día). */
  maximoDia: number;
  hoy: string;
  cambiarAnio: (anio: number) => void;
  cambiarMes: (mes: number) => void;
  setDia: (dia: number) => void;
  irAlPrimero: () => void;
  irAHoy: () => void;
  soloAprobados: boolean;
  setSoloAprobados: (valor: boolean) => void;
  recargar: () => void;
}

const SELECT_CLASES =
  "h-9 rounded-lg border border-gray-300 bg-white px-2.5 text-sm text-gray-700 " +
  "focus:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500/20 " +
  "dark:border-gray-700 dark:bg-gray-900 dark:text-white/90";

const BOTON_CLASES =
  "h-9 rounded-lg border border-gray-300 bg-white px-3 text-sm text-gray-700 " +
  "hover:bg-gray-50 focus:border-brand-500 focus:outline-none focus:ring-2 " +
  "focus:ring-brand-500/20 dark:border-gray-700 dark:bg-gray-900 " +
  "dark:text-white/90 dark:hover:bg-gray-800";

export const InformeToolbar = ({
  anio,
  mes,
  dia,
  maximoDia,
  hoy,
  cambiarAnio,
  cambiarMes,
  setDia,
  irAlPrimero,
  irAHoy,
  soloAprobados,
  setSoloAprobados,
  recargar,
}: InformeToolbarProps) => {
  const anioActual = Number(hoy.slice(0, 4));
  const anios = Array.from(
    { length: 7 },
    (_, indice) => anioActual - 5 + indice,
  );

  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="flex flex-col gap-1">
        <span className="text-xs text-gray-500 dark:text-gray-400">Año</span>
        <select
          value={anio}
          onChange={(e) => cambiarAnio(Number(e.target.value))}
          className={SELECT_CLASES}
          aria-label="Año del informe"
        >
          {anios.map((valor) => (
            <option key={valor} value={valor}>
              {valor}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-xs text-gray-500 dark:text-gray-400">Mes</span>
        <select
          value={mes}
          onChange={(e) => cambiarMes(Number(e.target.value))}
          className={SELECT_CLASES}
          aria-label="Mes del informe"
        >
          {MESES.map((nombre, indice) => (
            <option key={nombre} value={indice + 1}>
              {nombre.charAt(0) + nombre.slice(1).toLowerCase()}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <span className="text-xs text-gray-500 dark:text-gray-400">Día</span>
        <select
          value={dia}
          onChange={(e) => setDia(Number(e.target.value))}
          className={SELECT_CLASES}
          aria-label="Día del bloque Día"
        >
          {Array.from({ length: maximoDia }, (_, indice) => indice + 1).map(
            (valor) => (
              <option key={valor} value={valor}>
                {valor}
              </option>
            ),
          )}
        </select>
      </div>

      <button type="button" onClick={irAlPrimero} className={BOTON_CLASES}>
        1.º del mes
      </button>

      <button type="button" onClick={irAHoy} className={BOTON_CLASES}>
        Hoy
      </button>

      <button
        type="button"
        onClick={recargar}
        className={BOTON_CLASES}
        title="Volver a consultar al servidor"
      >
        ↻
      </button>

      <label className="ml-auto flex h-9 cursor-pointer items-center gap-2 pl-2">
        <span className="text-sm text-gray-700 dark:text-white/90">
          Solo aprobados
        </span>
        <span className="relative inline-flex">
          <input
            type="checkbox"
            className="peer sr-only"
            checked={soloAprobados}
            onChange={(e) => setSoloAprobados(e.target.checked)}
          />
          <span className="block h-5 w-9 rounded-full bg-gray-300 transition-colors peer-checked:bg-brand-500 peer-focus:ring-2 peer-focus:ring-brand-500/30 dark:bg-gray-700" />
          <span className="pointer-events-none absolute left-0.5 top-0.5 block h-4 w-4 rounded-full bg-white transition-transform peer-checked:translate-x-4" />
        </span>
      </label>
    </div>
  );
};
