// src/modules/transporte/flota/flotaView.utils.tsx
//
// Definición de columnas y configuración de la tabla de Flota Vehicular.
//
// Fuente de datos: `VehiculoListSerializer` (listado compacto). Los estados
// SOAT/CDA llegan YA calculados por el servidor (E1: nada de aritmética de
// fechas en el cliente).

import { ColumnDef } from "@tanstack/react-table";

import Badge from "@/components/ui/badge/Badge";
import { PuntoVigencia } from "../components/SemaforoVigencia";
import type {
  TipoContrato,
  TipoVehiculo,
  VehiculoListado,
} from "@/types/transporte.types";

/** Configuración de la tabla (idéntico patrón al de operaciones). */
export const FLOTA_TABLE_CONFIG = {
  defaultPageSize: 25,
  defaultPageIndex: 0,
} as const;

// ---------------------------------------------------------------------------
// Catálogos locales — espejo de models/choices.py. Etiquetas legibles sin
// depender de un round-trip al backend.
// ---------------------------------------------------------------------------

export const ETIQUETAS_TIPO_VEHICULO: Record<TipoVehiculo, string> = {
  CAMIONETA: "Camioneta",
  FURGON: "Furgón",
  VANS_CARGA: "Vans de carga",
  VANS_PASAJEROS: "Vans de pasajeros",
};

export const ETIQUETAS_TIPO_CONTRATO: Record<TipoContrato, string> = {
  PROPIO: "Propio",
  EXTERNO: "Externo",
  RENTING: "Renting",
};

// ---------------------------------------------------------------------------
// Utilidades de formato
// ---------------------------------------------------------------------------

/** `YYYY-MM-DD` → `dd/mm/yyyy`; evita el desfase horario de `new Date()`. */
export const formatearFecha = (valor?: string | null): string => {
  if (!valor) return "—";
  const [anio, mes, dia] = valor.slice(0, 10).split("-");
  if (!anio || !mes || !dia) return valor;
  return `${dia}/${mes}/${anio}`;
};

/** `1234567.89` → `$ 1.234.568` (sin decimales; el legacy redondeaba). */
export const formatearMoneda = (valor?: string | number | null): string => {
  if (valor === null || valor === undefined || valor === "") return "$ 0";
  const numero = typeof valor === "string" ? Number(valor) : valor;
  if (Number.isNaN(numero)) return "$ 0";
  return new Intl.NumberFormat("es-CO", {
    style: "currency",
    currency: "COP",
    maximumFractionDigits: 0,
  }).format(numero);
};

// ---------------------------------------------------------------------------
// Columnas
// ---------------------------------------------------------------------------

export const getFlotaColumns = (): ColumnDef<VehiculoListado>[] => [
  {
    id: "placa",
    accessorKey: "placa",
    header: "PLACA",
    cell: ({ row }) => (
      <span className="font-medium text-gray-800 dark:text-white/90">
        {row.original.placa}
      </span>
    ),
  },
  {
    id: "vehiculo",
    header: "VEHÍCULO",
    enableColumnFilter: false,
    cell: ({ row }) => {
      const { marca, referencia, modelo_anio } = row.original;
      return (
        <div className="flex flex-col">
          <span className="text-sm text-gray-700 dark:text-gray-300">
            {marca} {referencia ?? ""}
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500">
            {modelo_anio}
          </span>
        </div>
      );
    },
  },
  {
    id: "tipo_vehiculo",
    accessorKey: "tipo_vehiculo",
    header: "TIPO",
    filterFn: "equals",
    cell: ({ row }) => (
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {ETIQUETAS_TIPO_VEHICULO[row.original.tipo_vehiculo] ??
          row.original.tipo_vehiculo}
      </span>
    ),
  },
  {
    id: "tipo_contrato",
    accessorKey: "tipo_contrato",
    header: "CONTRATO",
    filterFn: "equals",
    cell: ({ row }) => {
      const tipo = row.original.tipo_contrato;
      const color =
        tipo === "PROPIO" ? "primary" : tipo === "RENTING" ? "info" : "light";
      return (
        <Badge color={color} size="sm">
          {ETIQUETAS_TIPO_CONTRATO[tipo] ?? tipo}
        </Badge>
      );
    },
  },
  {
    id: "ciudad_operacion",
    accessorKey: "ciudad_operacion",
    header: "CIUDAD",
    cell: ({ row }) => (
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {row.original.ciudad_operacion ?? "—"}
      </span>
    ),
  },
  {
    id: "estado_soat",
    accessorKey: "estado_soat",
    header: "SOAT",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex items-center gap-1.5">
        <PuntoVigencia estado={row.original.estado_soat} />
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatearFecha(row.original.fecha_soat)}
        </span>
      </div>
    ),
  },
  {
    id: "estado_cda",
    accessorKey: "estado_cda",
    header: "CDA",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex items-center gap-1.5">
        <PuntoVigencia estado={row.original.estado_cda} />
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {formatearFecha(row.original.fecha_cda)}
        </span>
      </div>
    ),
  },
  {
    id: "valor_dia_base",
    accessorKey: "valor_dia_base",
    header: "VALOR DÍA",
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-sm tabular-nums text-gray-700 dark:text-gray-300">
        {formatearMoneda(row.original.valor_dia_base)}
      </span>
    ),
  },
  {
    id: "activo",
    accessorKey: "activo",
    header: "ESTADO",
    filterFn: "equals",
    cell: ({ row }) =>
      row.original.activo ? (
        <Badge color="success" size="sm">
          Activo
        </Badge>
      ) : (
        <Badge color="light" size="sm">
          Inactivo
        </Badge>
      ),
  },
];
