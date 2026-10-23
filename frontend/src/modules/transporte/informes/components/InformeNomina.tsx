// src/modules/transporte/informes/components/InformeNomina.tsx
//
// Bloque "Nómina" (Paso 7): `GET /informes/nomina/` (F5-7) — el mes
// agrupado por (carpeta, placa), que es lo que se paga por carpeta.
//
// CRITERIOS DEL BACKEND, reflejados en la nota del bloque: excluye
// REPORTADO y ELIMINADO (no se paga lo pendiente ni lo borrado), retefuente
// 1 % sobre el valor base y pagador leído de los datos bancarios vigentes
// del vehículo EN SERVIDOR (CR-13), con el propietario como fallback.
//
// NO SE PINTA `centro_costo`: el backend lo devuelve vacío hasta que
// `InformeService.nomina` consuma `ParametrosService.centro_costos` (deuda
// C del informe F5, registrada en el tipo). Mejor omitir la columna a
// enseñar una que siempre está en blanco.
//
// El mes viene COMPLETO (sin paginación del servidor), así que el pie
// totales suma el mes entero y no la página visible.

import { useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import { BadgeEstadoSalida } from "../../components/EstadoSalidaBadge";
import type { FilaNominaInforme } from "@/types/transporte.types";
import { formatoCOP } from "../informesView.utils";
import {
  CLASE_NUMEROS,
  CLASE_TEXTO,
  Pagador,
  PieTotales,
  Raya,
} from "./informeCierre.utils";

const COLUMNAS: ColumnDef<FilaNominaInforme, unknown>[] = [
  {
    id: "carpeta",
    accessorKey: "carpeta",
    header: "CARPETA",
    cell: ({ row }) => (
      <span className={`${CLASE_TEXTO} font-medium text-gray-800 dark:text-white/90`}>
        {row.original.carpeta}
      </span>
    ),
  },
  {
    id: "placa",
    accessorKey: "placa",
    header: "PLACA",
    cell: ({ row }) => <span className={CLASE_NUMEROS}>{row.original.placa}</span>,
  },
  {
    id: "area",
    accessorKey: "area",
    header: "ÁREA",
    cell: ({ row }) => (
      <span className={CLASE_TEXTO}>{row.original.area || <Raya />}</span>
    ),
  },
  {
    id: "tipo_contrato",
    accessorKey: "tipo_contrato",
    header: "CONTRATO",
    cell: ({ row }) => <span className={CLASE_TEXTO}>{row.original.tipo_contrato}</span>,
  },
  {
    id: "pagador",
    header: "PAGADOR",
    enableSorting: false,
    cell: ({ row }) => (
      <Pagador
        nombre={row.original.nombre_pago}
        cedula={row.original.cedula_pago}
      />
    ),
  },
  {
    id: "total_dias",
    accessorKey: "total_dias",
    header: "DÍAS",
    cell: ({ row }) => (
      <span className={`${CLASE_NUMEROS} text-center`}>{row.original.total_dias}</span>
    ),
  },
  {
    id: "valor_dia",
    accessorKey: "valor_dia",
    header: "VALOR DÍA",
    cell: ({ row }) => (
      <span className={CLASE_NUMEROS}>{formatoCOP(row.original.valor_dia)}</span>
    ),
  },
  {
    id: "valor_base",
    accessorKey: "valor_base",
    header: "VALOR BASE",
    cell: ({ row }) => (
      <span className={CLASE_NUMEROS}>{formatoCOP(row.original.valor_base)}</span>
    ),
  },
  {
    id: "rte",
    accessorKey: "rte",
    header: "RTE 1 %",
    cell: ({ row }) => (
      <span className={`${CLASE_NUMEROS} text-amber-600 dark:text-amber-400/90`}>
        {formatoCOP(row.original.rte)}
      </span>
    ),
  },
  {
    id: "total_pagar",
    accessorKey: "total_pagar",
    header: "TOTAL A PAGAR",
    cell: ({ row }) => (
      <span className={`${CLASE_NUMEROS} font-medium text-gray-800 dark:text-white/90`}>
        {formatoCOP(row.original.total_pagar)}
      </span>
    ),
  },
  {
    id: "estado",
    accessorKey: "estado",
    header: "ESTADO",
    cell: ({ row }) => <BadgeEstadoSalida estado={row.original.estado} />,
  },
  {
    id: "consecutivo",
    accessorKey: "consecutivo",
    header: "CONSECUTIVO",
    cell: ({ row }) => (
      <span className={CLASE_NUMEROS}>{row.original.consecutivo || <Raya />}</span>
    ),
  },
];

interface InformeNominaProps {
  /** Filas del mes completo (el endpoint no pagina). */
  filas: FilaNominaInforme[];
}

export const InformeNomina = ({ filas }: InformeNominaProps) => {
  const totales = useMemo(
    () =>
      filas.reduce(
        (acumulado, fila) => ({
          base: acumulado.base + fila.valor_base,
          rte: acumulado.rte + fila.rte,
          pagar: acumulado.pagar + fila.total_pagar,
        }),
        { base: 0, rte: 0, pagar: 0 },
      ),
    [filas],
  );

  if (filas.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        No hay salidas pagables en este periodo (se excluyen reportados y
        eliminados).
      </p>
    );
  }

  return (
    <>
      <DataTable
        data={filas}
        columns={COLUMNAS}
        emptyMessage="No hay filas de nómina para este periodo."
        pageSize={25}
        pageSizeOptions={[25, 50, 100]}
      />
      <PieTotales
        etiquetas={[
          { rotulo: "Valor base", valor: totales.base },
          { rotulo: "Retefuente 1 %", valor: totales.rte },
          { rotulo: "Total a pagar", valor: totales.pagar },
        ]}
      />
    </>
  );
};
