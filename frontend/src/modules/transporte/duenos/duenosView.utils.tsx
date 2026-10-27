// src/modules/transporte/duenos/duenosView.utils.tsx
//
// Definición de columnas y configuración de la tabla de Dueños de Vehículos.

import { ColumnDef } from "@tanstack/react-table";
import Badge from "@/components/ui/badge/Badge";
import type { DuenoResumen } from "@/types/transporte.types";

export const DUENOS_TABLE_CONFIG = {
  defaultPageSize: 25,
  defaultPageIndex: 0,
} as const;

interface DuenosColumnsOptions {
  onVerFicha: (dueno: DuenoResumen) => void;
  onAgregarCuenta?: (dueno: DuenoResumen) => void;
}

export const getDuenosColumns = ({
  onVerFicha,
  onAgregarCuenta,
}: DuenosColumnsOptions): ColumnDef<DuenoResumen>[] => [
  {
    id: "cedula",
    accessorKey: "cedula",
    header: "CÉDULA / NIT",
    cell: ({ row }) => (
      <span className="font-semibold text-gray-800 dark:text-white/90">
        {row.original.cedula}
      </span>
    ),
  },
  {
    id: "nombre",
    accessorKey: "nombre",
    header: "PROPIETARIO / DUEÑO",
    cell: ({ row }) => (
      <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
        {row.original.nombre}
      </span>
    ),
  },
  {
    id: "celular",
    accessorKey: "celular",
    header: "TELÉFONO / CELULAR",
    cell: ({ row }) => (
      <span className="text-sm text-gray-600 dark:text-gray-400">
        {row.original.celular || "—"}
      </span>
    ),
  },
  {
    id: "total_vehiculos",
    accessorKey: "total_vehiculos",
    header: "VEHÍCULOS ASIGNADOS",
      cell: ({ row }) => {
      const cantidad = row.original.total_vehiculos;
      return (
        <button
          type="button"
          title="Ver ficha de vehículos y cuentas bancarias"
          aria-label={`Ver ficha de ${row.original.nombre}`}
          onClick={() => onVerFicha(row.original)}
          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium transition hover:ring-2 hover:ring-brand-300 dark:hover:ring-brand-500/40 ${
            cantidad > 0
              ? "bg-brand-50 text-brand-700 dark:bg-brand-500/15 dark:text-brand-400"
              : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
          }`}
        >
          {cantidad} vehículo{cantidad === 1 ? "" : "s"}
        </button>
      );
    },
  },
  {
    id: "total_cuentas",
    accessorKey: "total_cuentas",
    header: "CUENTAS BANCARIAS",
    cell: ({ row }) => {
      const cuentas = row.original.total_cuentas;
      return (
        <button
          type="button"
          title="Agregar o gestionar cuentas bancarias de este dueño"
          aria-label={`Gestionar cuentas bancarias de ${row.original.nombre}`}
          onClick={() => onAgregarCuenta ? onAgregarCuenta(row.original) : onVerFicha(row.original)}
          className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium cursor-pointer transition hover:ring-2 hover:ring-emerald-300 dark:hover:ring-emerald-500/40 ${
            cuentas > 0
              ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:bg-emerald-500/15 dark:text-emerald-400 dark:hover:bg-emerald-500/25"
              : "bg-warning-50 text-warning-700 hover:bg-warning-100 dark:bg-warning-500/15 dark:text-warning-400 dark:hover:bg-warning-500/25"
          }`}
        >
          <span className="font-semibold">+</span>
          {cuentas > 0
            ? `${cuentas} cuenta${cuentas === 1 ? "" : "s"}`
            : "Sin cuentas · Agregar"}
        </button>
      );
    },
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
