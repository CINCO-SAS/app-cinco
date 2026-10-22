// src/modules/transporte/informes/components/InformeTablaAreas.tsx
//
// Tabla de áreas con desglose por carpetas, COMPARTIDA por los bloques
// "Transporte Día" y "Transporte Mes": los dos devuelven `AreaInforme[]`
// (un área con sus carpetas anidadas), así que no se duplica la tabla.
//
// Las carpetas se despliegan bajo su área, como hacía `formatPlusRow` del
// legacy. No se usa el `DataTable` compartido porque éste no soporta
// expansión de filas (`getExpandedRowModel` no está cableado) y tocarlo
// afectaría a las 4 pantallas que ya lo usan.
//
// COLUMNAS FRENTE AL LEGACY:
//  · Se añade "Renting": el backend lo cuenta APARTE, mientras el legacy lo
//    mezclaba dentro de "Prop".
//  · NO se pintan "Ttl_Pro" / "Ttl_Ext" (dinero propio y externo por
//    separado): el backend aún no los expone en el agregado. Es el hueco E
//    del informe F5; las columnas se recuperarán cuando existan.

import { Fragment, useState } from "react";

import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type {
  AreaInforme,
  BloqueAgregadoInforme,
  DesgloseEstadosInforme,
} from "@/types/transporte.types";
import {
  INDICADORES_ESTADO,
  formatoCOP,
  indicadorEstado,
  sumarBloques,
} from "../informesView.utils";

/** Ancho de las 7 columnas, compartido por la tabla de áreas y la de carpetas. */
const COL_SPAN = 7;

const CLASE_NUMEROS = "px-3 py-2 text-right text-sm tabular-nums";
const CLASE_TEXTO = "px-3 py-2 text-left text-sm";
const CLASE_ENCABEZADO =
  "px-3 py-2 text-xs font-semibold uppercase tracking-wide text-gray-500 " +
  "dark:text-gray-400";

/** Celdas numéricas comunes a un área y a una carpeta (mismo bloque). */
const CeldasConteo = ({ bloque }: { bloque: BloqueAgregadoInforme }) => (
  <>
    <td className={CLASE_NUMEROS}>{bloque.propios}</td>
    <td className={CLASE_NUMEROS}>{bloque.renting}</td>
    <td className={CLASE_NUMEROS}>{bloque.externos}</td>
    <td className={CLASE_NUMEROS}>{bloque.total_vehi}</td>
    <td className={`${CLASE_NUMEROS} font-medium`}>
      {formatoCOP(bloque.total_dia)}
    </td>
  </>
);

/**
 * Semáforo del bloque: compara `aprobado + validado` contra `total` del
 * mismo `arr_estado` (misma regla que la columna "Aprobado" del legacy).
 */
const Indicador = ({ estados }: { estados: DesgloseEstadosInforme }) => {
  const { clase, icono, titulo } = INDICADORES_ESTADO[indicadorEstado(estados)];
  return (
    <span
      title={titulo}
      className={`inline-flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-bold leading-none text-white ${clase}`}
    >
      {icono}
    </span>
  );
};

const Encabezado = ({ etiqueta }: { etiqueta: string }) => (
  <TableHeader className="border-b border-gray-100 bg-white dark:border-white/5 dark:bg-gray-900">
    <TableRow className="bg-white dark:bg-gray-900">
      <TableCell isHeader className={`${CLASE_ENCABEZADO} text-start`}>
        {etiqueta}
      </TableCell>
      <TableCell isHeader className={`${CLASE_ENCABEZADO} text-center`}>
        Estado
      </TableCell>
      <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
        Prop
      </TableCell>
      <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
        Renting
      </TableCell>
      <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
        Exter
      </TableCell>
      <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
        Vehículos
      </TableCell>
      <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
        Total
      </TableCell>
    </TableRow>
  </TableHeader>
);

/** Tabla anidada de carpetas de UN área (solo visible al expandir). */
const TablaCarpetas = ({ carpetas }: { carpetas: AreaInforme["carpetas"] }) => (
  <Table className="border-t border-gray-100 dark:border-white/5">
    <TableHeader className="bg-gray-50 dark:bg-gray-800/50">
      <TableRow className="bg-gray-50 dark:bg-gray-800/50">
        <TableCell isHeader className={`${CLASE_ENCABEZADO} text-start pl-8`}>
          Carpeta
        </TableCell>
        <TableCell isHeader className={`${CLASE_ENCABEZADO} text-center`}>
          Estado
        </TableCell>
        <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
          Prop
        </TableCell>
        <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
          Renting
        </TableCell>
        <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
          Exter
        </TableCell>
        <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
          Vehículos
        </TableCell>
        <TableCell isHeader className={`${CLASE_ENCABEZADO} text-right`}>
          Total
        </TableCell>
      </TableRow>
    </TableHeader>
    <TableBody>
      {carpetas.map((carpeta) => (
        <TableRow
          key={carpeta.carpeta}
          className="border-b border-gray-100 last:border-0 dark:border-white/5"
        >
          <TableCell className={`${CLASE_TEXTO} pl-8`}>{carpeta.carpeta}</TableCell>
          <td className={`${CLASE_NUMEROS} text-center`}>
            <Indicador estados={carpeta.arr_estado} />
          </td>
          <CeldasConteo bloque={carpeta} />
        </TableRow>
      ))}
    </TableBody>
  </Table>
);

interface InformeTablaAreasProps {
  areas: AreaInforme[];
  /** Rótulo de la primera columna: "Área" en el bloque Mes, "Área" en Día. */
  etiquetaPrimeraColumna?: string;
  isLoading?: boolean;
  /** Mensaje cuando el período no tiene salidas. */
  vacio?: string;
}

export const InformeTablaAreas = ({
  areas,
  etiquetaPrimeraColumna = "Área",
  isLoading = false,
  vacio = "No hay salidas registradas en este período.",
}: InformeTablaAreasProps) => {
  const [areaExpandida, setAreaExpandida] = useState<string | null>(null);

  if (!isLoading && areas.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        {vacio}
      </p>
    );
  }

  const totales = sumarBloques(areas);

  return (
    // UN solo <Table> envuelve todo: <thead>/<tbody>/<tfoot> solo son
    // válidos dentro de un <table>. Hay varios <tbody> (uno por área) para
    // que la fila de carpetas quede justo debajo de su área; es HTML válido
    // y es lo que hace el navegador al expandir un grupo.
    <div className="overflow-x-auto">
      <Table>
        <Encabezado etiqueta={etiquetaPrimeraColumna} />

        {isLoading ? (
          <TableBody>
            <TableRow>
              <TableCell colSpan={COL_SPAN} className="px-3 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
                Consultando al servidor…
              </TableCell>
            </TableRow>
          </TableBody>
        ) : (
          areas.map((area) => {
            const expandida = areaExpandida === area.area;
            return (
              <Fragment key={area.area}>
                <TableBody>
                  <TableRow
                    onClick={() => setAreaExpandida(expandida ? null : area.area)}
                    className={`cursor-pointer border-b border-gray-100 transition-colors hover:bg-gray-50 dark:border-white/5 dark:hover:bg-gray-800/40 ${
                      expandida ? "bg-gray-50 dark:bg-gray-800/40" : ""
                    }`}
                  >
                    <TableCell className={`${CLASE_TEXTO} font-medium`}>
                      <span className="flex items-center gap-1.5">
                        <span
                          aria-hidden
                          className={`text-xs text-gray-400 transition-transform ${
                            expandida ? "rotate-90" : ""
                          }`}
                        >
                          ▸
                        </span>
                        {area.area}
                      </span>
                    </TableCell>
                    <td className={`${CLASE_NUMEROS} text-center`}>
                      <Indicador estados={area.arr_estado} />
                    </td>
                    <CeldasConteo bloque={area} />
                  </TableRow>
                </TableBody>

                {expandida && area.carpetas.length > 0 && (
                  <TableBody>
                    <TableRow>
                      <TableCell
                        colSpan={COL_SPAN}
                        className="bg-gray-50/60 p-0 dark:bg-gray-800/20"
                      >
                        <TablaCarpetas carpetas={area.carpetas} />
                      </TableCell>
                    </TableRow>
                  </TableBody>
                )}
              </Fragment>
            );
          })
        )}

        {/* El pie solo se pinta con datos estables: si no, quedaría
            sumando el periodo ANTERIOR mientras carga el nuevo. */}
        {!isLoading && (
          <tfoot>
            <tr className="border-t border-gray-200 bg-gray-50 dark:border-white/10 dark:bg-gray-800/50">
              <th
                className={`${CLASE_TEXTO} text-left font-semibold text-gray-700 dark:text-gray-200`}
              >
                TOTALES:
              </th>
              <th className={`${CLASE_NUMEROS} text-center`} />
              <CeldasConteo bloque={totales} />
            </tr>
          </tfoot>
        )}
      </Table>
    </div>
  );
};
