// src/modules/transporte/informes/components/informeCierre.utils.tsx
//
// Celdas y pie COMPARTIDOS por las dos tablas del cierre del mes (nómina y
// liquidación, Paso 7): son el mismo periodo con dos agrupaciones, así que
// el pagador, el dinero y el pie de totales deben verse idénticos. Si cada
// tabla formateara a su manera, dos cifras del mismo mes podrían no
// coincidir entre bloques por una diferencia de redondeo en el render.

import { formatoCOP } from "../informesView.utils";

export const CLASE_NUMEROS =
  "whitespace-nowrap text-sm tabular-nums text-gray-700 dark:text-gray-300";

export const CLASE_TEXTO = "text-sm text-gray-600 dark:text-gray-400";

export const Raya = () => <span className="text-gray-400">—</span>;

/**
 * Nombre + cédula de quien recibe el pago.
 *
 * Llega resuelto EN SERVIDOR desde los datos bancarios vigentes del
 * vehículo (CR-13); sin dato bancario el backend devuelve el propietario.
 */
export const Pagador = ({
  nombre,
  cedula,
}: {
  nombre: string;
  cedula: string;
}) => (
  <div className="flex flex-col">
    <span className="text-sm text-gray-700 dark:text-gray-300">
      {nombre || "—"}
    </span>
    <span className="text-xs text-gray-400 dark:text-gray-500">
      CC {cedula || "—"}
    </span>
  </div>
);

/**
 * Pie de totales del bloque.
 *
 * Va FUERA del `DataTable` (que no tiene `tfoot`) y suma el arreglo COMPLETO
 * que devolvió el servidor: nómina y liquidación no vienen paginadas, así
 * que el total es del mes entero y no de la página visible.
 */
export const PieTotales = ({
  etiquetas,
}: {
  etiquetas: Array<{ rotulo: string; valor: number }>;
}) => (
  <div className="flex flex-wrap items-center justify-end gap-x-6 gap-y-1 border-t border-gray-100 bg-gray-50 px-3 py-2 dark:border-white/5 dark:bg-gray-800/40">
    {etiquetas.map(({ rotulo, valor }) => (
      <span
        key={rotulo}
        className="text-xs text-gray-500 dark:text-gray-400"
      >
        {rotulo}{" "}
        <span className="text-sm font-semibold tabular-nums text-gray-800 dark:text-white/90">
          {formatoCOP(valor)}
        </span>
      </span>
    ))}
  </div>
);
