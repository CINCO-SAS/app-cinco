// src/modules/transporte/informes/components/InformeLiquidacion.tsx
//
// Bloque "Liquidación" (Paso 7): `GET /informes/liquidacion/` (F5-7) — el
// mismo mes que la nómina pero agrupado por PLACA (una fila por vehículo),
// que es lo que se paga por propietario.
//
// CRITERIOS DEL BACKEND, reflejados en la nota del bloque: excluye
// REPORTADO y ELIMINADO (como la nómina), retefuente 1 % sobre el valor
// base y `pagar = valor_base − rte`. El pagador y la CUENTA llegan
// resueltos EN SERVIDOR desde los datos bancarios vigentes del vehículo
// (CR-13), con el propietario como fallback del nombre.
//
// La columna "CUENTA" junta banco · tipo · número en una sola celda: son
// tres campos cortos que en tres columnas separadas empujarían el resto de
// importes fuera de pantalla sin añadir lectura.
//
// El mes viene COMPLETO (sin paginación del servidor), así que el pie
// totales suma el mes entero y no la página visible.

import { useMemo } from "react";
import { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import type { FilaLiquidacionInforme } from "@/types/transporte.types";
import { formatoCOP } from "../informesView.utils";
import {
  CLASE_NUMEROS,
  CLASE_TEXTO,
  Pagador,
  PieTotales,
  Raya,
} from "./informeCierre.utils";

const COLUMNAS: ColumnDef<FilaLiquidacionInforme, unknown>[] = [
  {
    id: "placa",
    accessorKey: "placa",
    header: "PLACA",
    cell: ({ row }) => (
      <span className={`${CLASE_NUMEROS} font-medium text-gray-800 dark:text-white/90`}>
        {row.original.placa}
      </span>
    ),
  },
  {
    id: "propietario",
    accessorKey: "propietario",
    header: "PROPIETARIO",
    cell: ({ row }) => <span className={CLASE_TEXTO}>{row.original.propietario}</span>,
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
    id: "pagar",
    accessorKey: "pagar",
    header: "A PAGAR",
    cell: ({ row }) => (
      <span className={`${CLASE_NUMEROS} font-medium text-gray-800 dark:text-white/90`}>
        {formatoCOP(row.original.pagar)}
      </span>
    ),
  },
  {
    // Banco · tipo · número en una celda (tres campos cortos que en tres
    // columnas empujarían los importes fuera de pantalla).
    id: "cuenta",
    header: "CUENTA",
    enableSorting: false,
    cell: ({ row }) => {
      const { banco, tipo_cuenta, cuenta_pago } = row.original;
      if (!cuenta_pago) return <Raya />;
      return (
        <div className="flex flex-col text-sm text-gray-600 dark:text-gray-400">
          <span>
            {tipo_cuenta} {banco}
          </span>
          <span className="text-xs tabular-nums text-gray-400 dark:text-gray-500">
            {cuenta_pago}
          </span>
        </div>
      );
    },
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

interface InformeLiquidacionProps {
  /** Filas del mes completo (el endpoint no pagina). */
  filas: FilaLiquidacionInforme[];
}

export const InformeLiquidacion = ({ filas }: InformeLiquidacionProps) => {
  const totales = useMemo(
    () =>
      filas.reduce(
        (acumulado, fila) => ({
          base: acumulado.base + fila.valor_base,
          rte: acumulado.rte + fila.rte,
          pagar: acumulado.pagar + fila.pagar,
        }),
        { base: 0, rte: 0, pagar: 0 },
      ),
    [filas],
  );

  if (filas.length === 0) {
    return (
      <p className="px-4 py-8 text-center text-sm text-gray-500 dark:text-gray-400">
        No hay vehículos con salidas pagables en este periodo (se excluyen
        reportados y eliminados).
      </p>
    );
  }

  return (
    <>
      <DataTable
        data={filas}
        columns={COLUMNAS}
        emptyMessage="No hay vehículos para liquidar en este periodo."
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
