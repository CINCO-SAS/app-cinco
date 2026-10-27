// src/modules/transporte/informes/components/InformeReporteArea.tsx
//
// Bloque "Reporte Área" (legacy: `createTableReportEstado`, tabla
// `tb_trans_x_aprobacion`).
//
// QUÉ MUESTRA: por cada área del mes, cuántas salidas y cuánto dinero hay
// en cada estado. La columna "Cnt / Val" es APROBADO + VALIDADO juntos: es
// lo que el operario mira para saber cuánto ya está listo.
//
// DE DÓNDE SALEN LOS DATOS: del MISMO `/informes/area/` que alimenta el
// bloque "Transporte Mes". En el legacy, `loadInfoArea()` construía
// `tb_area` y `tb_aprob` en un único recorrido del mismo dataset
// (líneas 2854-2945), así que aquí NO hay petición nueva.
//
// EL INTERRUPTOR "Solo aprobados" NO TOCA ESTA TABLA. En el legacy
// `arr_estado` se acumulaba ANTES del filtro `only_apro` (se acumula en
// 2893-2909 y el filtro corta recién en 2910), y el backend hace lo
// mismo: `InformeService._acumular` incrementa `arr_estado` siempre.
//
// "PENDIENTE" ES EL ESTADO REPORTADO. El legacy llamaba `pendiente` a
// REPORTADO (JS 3007-3011); el backend ya usa el nombre real en el dato.
// Aquí se conserva la etiqueta con la que el operario conoce la columna y
// se anota el mapeo, para que nadie busque un estado "PENDIENTADO".
//
// ORDENACIÓN: el legacy pedía `order: [[5, 'DESC']]`, es decir Pendiente
// de mayor a menor — lo que queda pendiente primero. `Array.sort` es
// estable, así que los empates conservan el orden alfabético de llegada.
//
// PENDIENTE: si el área era "I&M", el legacy mostraba un icono de refresco
// que lanzaba un job de validación WFM (`POST /wfm/validar/`). Ese botón
// escribe validaciones y requiere permiso + confirmación explícita, así que
// se diferió. El botón Excel (↓ Excel) ya está cableado en `informesView.tsx`
// vía `InformeExportarReporteArea` (acciones del bloque `InformeBloque`).

import { useMemo } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  AreaInforme,
  ContadorEstadoInforme,
} from "@/types/transporte.types";
import { formatoCOP } from "../informesView.utils";
import { InformeWfmRefresh } from "./InformeWfmRefresh";

/** Fila de este bloque: el resumen de estados de UN área. */
interface ResumenArea {
  area: string;
  /** APROBADO + VALIDADO, que es lo que la tabla rotula "Cnt / Val". */
  cntVal: ContadorEstadoInforme;
  aprobado: ContadorEstadoInforme;
  validado: ContadorEstadoInforme;
  rechazado: ContadorEstadoInforme;
  /** `reportado` en el backend — "Pendiente" en la cabecera. */
  pendiente: ContadorEstadoInforme;
}

const sumar = (
  a: ContadorEstadoInforme,
  b: ContadorEstadoInforme,
): ContadorEstadoInforme => ({ cnt: a.cnt + b.cnt, valor: a.valor + b.valor });

const aResumen = (area: AreaInforme): ResumenArea => ({
  area: area.area,
  cntVal: sumar(area.arr_estado.aprobado, area.arr_estado.validado),
  aprobado: area.arr_estado.aprobado,
  validado: area.arr_estado.validado,
  rechazado: area.arr_estado.rechazado,
  pendiente: area.arr_estado.reportado,
});

/** Tono de la celda, heredado de los `bg_info_*` del legacy. */
const TONOS = {
  positivo: "bg-success-50 text-success-700 dark:bg-success-950/40 dark:text-success-300",
  negativo: "bg-error-50 text-error-700 dark:bg-error-950/40 dark:text-error-300",
  pendiente: "bg-warning-50 text-warning-700 dark:bg-warning-950/40 dark:text-warning-300",
} as const;

/**
 * Celda apilada: conteo arriba, importe debajo, con marco — la forma que
 * dibujaba el `render` de la columna en el legacy.
 */
const CeldaEstado = ({
  dato,
  tono,
}: {
  dato: ContadorEstadoInforme;
  tono: string;
}) => (
  <td className="px-2 py-1.5 align-middle">
    <div className="mx-auto flex min-w-[6.5rem] flex-col border border-gray-200 dark:border-gray-700">
      <span className="px-1 py-0.5 text-center text-sm font-semibold text-gray-800 dark:text-white/90">
        {dato.cnt}
      </span>
      <span className={`px-1 py-0.5 text-center text-[11px] font-medium ${tono}`}>
        {formatoCOP(dato.valor)}
      </span>
    </div>
  </td>
);

const ENCABEZADO_CLASE =
  "px-2 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400";

/** Cabecera: el área y los 5 bloques de estado. */
const Cabecera = () => (
  <TableHeader className="border-b border-gray-100 bg-white dark:border-white/5 dark:bg-gray-900">
    <TableRow className="bg-white dark:bg-gray-900">
      <TableCell isHeader className={`${ENCABEZADO_CLASE} text-start`}>
        Área
      </TableCell>
      <TableCell isHeader className={`${ENCABEZADO_CLASE} text-center`}>
        Cnt / Val
      </TableCell>
      <TableCell isHeader className={`${ENCABEZADO_CLASE} text-center`}>
        Aprobado
      </TableCell>
      <TableCell isHeader className={`${ENCABEZADO_CLASE} text-center`}>
        Validado
      </TableCell>
      <TableCell isHeader className={`${ENCABEZADO_CLASE} text-center`}>
        Rechazado
      </TableCell>
      <TableCell isHeader className={`${ENCABEZADO_CLASE} text-center`}>
        Pendiente
      </TableCell>
      <TableCell isHeader className={`${ENCABEZADO_CLASE} text-center`}>
        Acción
      </TableCell>
    </TableRow>
  </TableHeader>
);

/** Fila de una área o, en el pie, el acumulado de todas. */
const FilaEstado = ({
  area,
  resumen,
  esTotal = false,
  mes,
  anio,
  onWfmValidado,
}: {
  area: string;
  resumen: ResumenArea;
  esTotal?: boolean;
  mes?: number;
  anio?: number;
  onWfmValidado?: () => void;
}) => (
  <TableRow
    className={
      esTotal
        ? "border-t border-gray-200 bg-gray-50 dark:border-white/10 dark:bg-gray-800/50"
        : "border-b border-gray-100 last:border-0 dark:border-white/5"
    }
  >
    <td
      className={`px-3 py-2 text-left text-sm ${
        esTotal
          ? "font-semibold text-gray-700 dark:text-gray-200"
          : "font-medium text-gray-800 dark:text-white/90"
      }`}
    >
      {area}
    </td>
    <CeldaEstado dato={resumen.cntVal} tono={TONOS.positivo} />
    <CeldaEstado dato={resumen.aprobado} tono={TONOS.positivo} />
    <CeldaEstado dato={resumen.validado} tono={TONOS.positivo} />
    <CeldaEstado dato={resumen.rechazado} tono={TONOS.negativo} />
    <CeldaEstado dato={resumen.pendiente} tono={TONOS.pendiente} />
    <td className="px-2 py-1.5 text-center align-middle">
      {!esTotal && mes !== undefined && anio !== undefined && (
        <InformeWfmRefresh
          area={area}
          mes={mes}
          anio={anio}
          onValidado={onWfmValidado}
        />
      )}
    </td>
  </TableRow>
);

interface InformeReporteAreaProps {
  areas: AreaInforme[];
  isLoading?: boolean;
  vacio?: string;
  mes: number;
  anio: number;
  onWfmValidado?: () => void;
}

export const InformeReporteArea = ({
  areas,
  isLoading = false,
  vacio = "No hay salidas registradas en este período.",
  mes,
  anio,
  onWfmValidado,
}: InformeReporteAreaProps) => {
  // Pendiente primero (orden `[[5, 'DESC']]` del legacy). `sort` es
  // estable, así que los empates quedan en orden alfabético.
  const resumenes = useMemo(
    () =>
      [...areas.map(aResumen)].sort(
        (a, b) => b.pendiente.cnt - a.pendiente.cnt,
      ),
    [areas],
  );

  // El pie replica las mismas celdas apiladas, sumadas por columna.
  const totales = useMemo<ResumenArea>(
    () =>
      resumenes.reduce<ResumenArea>(
        (acumulado, resumen) => ({
          area: "Totales",
          cntVal: sumar(acumulado.cntVal, resumen.cntVal),
          aprobado: sumar(acumulado.aprobado, resumen.aprobado),
          validado: sumar(acumulado.validado, resumen.validado),
          rechazado: sumar(acumulado.rechazado, resumen.rechazado),
          pendiente: sumar(acumulado.pendiente, resumen.pendiente),
        }),
        {
          area: "Totales",
          cntVal: { cnt: 0, valor: 0 },
          aprobado: { cnt: 0, valor: 0 },
          validado: { cnt: 0, valor: 0 },
          rechazado: { cnt: 0, valor: 0 },
          pendiente: { cnt: 0, valor: 0 },
        },
      ),
    [resumenes],
  );

  if (!isLoading && resumenes.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        {vacio}
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <Cabecera />

        <TableBody>
          {isLoading ? (
            <TableRow>
              <TableCell
                colSpan={6}
                className="px-3 py-8 text-center text-sm text-gray-500 dark:text-gray-400"
              >
                Consultando al servidor…
              </TableCell>
            </TableRow>
          ) : (
            resumenes.map((resumen) => (
              <FilaEstado
                key={resumen.area}
                area={resumen.area}
                resumen={resumen}
                mes={mes}
                anio={anio}
                onWfmValidado={onWfmValidado}
              />
            ))
          )}
        </TableBody>

        {!isLoading && (
          <tfoot>
            <FilaEstado area="Totales" resumen={totales} esTotal />
          </tfoot>
        )}
      </Table>
    </div>
  );
};
