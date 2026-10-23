// src/modules/transporte/informes/components/InformeMatrizAnual.tsx
//
// Bloque "Área y Carpeta" (Paso 6 del plan): la matriz área × meses del año
// (`GET /informes/areas-mes/`, F5-7) en forma de TABLA.
//
// Es la forma tabular del histórico que el bloque de arriba dibuja como
// gráfico "Pagos por Mes, por Área" (F5-2): mismos datos, otra lectura — la
// tabla permite comparar importes exactos mes a mes, que en un gráfico solo
// se estiman a ojo. De ahí que tampoco responda al mes ni al interruptor
// "Solo aprobados": el endpoint acumula el año completo sin ese filtro.
//
// Celda vacía = "—" y no "$ 0": un mes sin salidas no es lo mismo que un mes
// con salidas de valor cero, y pintar ceros sugiere actividad donde no la
// hay. El título de cada celda (tooltip) añade los vehículos del mes, que es
// lo único que la cifra sola no dice.

import { useMemo } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { AreaMatrizInforme, MesAreaInforme } from "@/types/transporte.types";
import { MESES_CORTOS, formatoCOP } from "../informesView.utils";

const CLASE_NUMEROS = "px-2 py-2 text-right text-sm tabular-nums";
const CLASE_TEXTO = "px-3 py-2 text-left text-sm";
const CLASE_ENCABEZADO =
  "px-2 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500 " +
  "dark:text-gray-400";

/** Importe del mes 1-12 de un área; `undefined` si ese mes no tuvo salidas. */
const datoDelMes = (
  meses: MesAreaInforme[],
  mes: number,
): MesAreaInforme | undefined => meses.find((dato) => dato.mes === mes);

/** Σ de todos los meses con datos de un área. */
const totalDelAnio = (meses: MesAreaInforme[]): number =>
  meses.reduce((acumulado, dato) => acumulado + dato.total_dia, 0);

const CeldaMes = ({ dato }: { dato?: MesAreaInforme }) => {
  if (!dato) {
    return <td className={`${CLASE_NUMEROS} text-gray-300 dark:text-gray-700`}>—</td>;
  }
  return (
    <td
      className={CLASE_NUMEROS}
      title={`${dato.total_vehi} ${dato.total_vehi === 1 ? "vehículo" : "vehículos"}`}
    >
      {formatoCOP(dato.total_dia)}
    </td>
  );
};

interface InformeMatrizAnualProps {
  /** Salida de `useInformeMatriz`. */
  areas: AreaMatrizInforme[];
}

export const InformeMatrizAnual = ({ areas }: InformeMatrizAnualProps) => {
  // Totales por mes (columna inferior): se recalculan solo cuando cambian
  // las áreas, no en cada render.
  const totalesPorMes = useMemo(() => {
    const acumulado = new Array<number>(12).fill(0);
    for (const area of areas) {
      for (const dato of area.meses) {
        acumulado[dato.mes - 1] += dato.total_dia;
      }
    }
    return acumulado;
  }, [areas]);

  if (areas.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        No hay salidas registradas en este año.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader className="bg-white dark:bg-gray-900">
          <TableRow className="bg-white dark:bg-gray-900">
            <TableCell isHeader className={`${CLASE_ENCABEZADO} text-start`}>
              Área
            </TableCell>
            {MESES_CORTOS.map((nombre) => (
              <TableCell
                isHeader
                key={nombre}
                className={`${CLASE_ENCABEZADO} text-right`}
              >
                {nombre}
              </TableCell>
            ))}
            <TableCell
              isHeader
              className={`${CLASE_ENCABEZADO} border-l border-gray-100 text-right dark:border-white/5`}
            >
              Total
            </TableCell>
          </TableRow>
        </TableHeader>

        <TableBody>
          {areas.map((area) => (
            <TableRow
              key={area.area}
              className="border-b border-gray-100 last:border-0 dark:border-white/5"
            >
              <TableCell className={`${CLASE_TEXTO} font-medium`}>
                {area.area}
              </TableCell>
              {MESES_CORTOS.map((_, indice) => (
                <CeldaMes
                  key={indice}
                  dato={datoDelMes(area.meses, indice + 1)}
                />
              ))}
              <td
                className={`${CLASE_NUMEROS} border-l border-gray-100 font-medium text-gray-800 dark:border-white/5 dark:text-white/90`}
              >
                {formatoCOP(totalDelAnio(area.meses))}
              </td>
            </TableRow>
          ))}
        </TableBody>

        {/* Pie con el total por mes: la fila que se compara contra el
            gráfico de arriba. */}
        <tfoot>
          <tr className="border-t border-gray-200 bg-gray-50 dark:border-white/10 dark:bg-gray-800/50">
            <th className={`${CLASE_TEXTO} font-semibold text-gray-700 dark:text-gray-200`}>
              TOTAL:
            </th>
            {totalesPorMes.map((total, indice) => (
              <th
                key={indice}
                className={`${CLASE_NUMEROS} font-semibold text-gray-700 dark:text-gray-200`}
              >
                {total > 0 ? formatoCOP(total) : "—"}
              </th>
            ))}
            <th
              className={`${CLASE_NUMEROS} border-l border-gray-200 font-semibold text-gray-700 dark:border-white/10 dark:text-gray-200`}
            >
              {formatoCOP(totalesPorMes.reduce((a, b) => a + b, 0))}
            </th>
          </tr>
        </tfoot>
      </Table>
    </div>
  );
};
