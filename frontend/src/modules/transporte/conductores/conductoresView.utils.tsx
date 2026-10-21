// src/modules/transporte/conductores/conductoresView.utils.tsx
//
// Columnas, catálogos y formato de la tabla de Conductores (F2).
//
// Fuente de datos: `ConductorListSerializer` (listado compacto). El semáforo
// `estado_licencia` llega YA calculado por el servidor (§5.3) — igual que el
// SOAT/CDA en flota: nada de aritmética de fechas en el cliente.

import { ColumnDef } from "@tanstack/react-table";

import Badge from "@/components/ui/badge/Badge";
import { PuntoVigencia } from "../components/SemaforoVigencia";
import type {
  CategoriaLicencia,
  ConductorListado,
  TipoVinculacion,
} from "@/types/transporte.types";

/** Configuración de la tabla (idéntico patrón al de flota/operaciones). */
export const CONDUCTORES_TABLE_CONFIG = {
  defaultPageSize: 25,
  defaultPageIndex: 0,
} as const;

// ---------------------------------------------------------------------------
// Catálogos locales — espejo de models/choices.py. Etiquetas legibles sin
// depender de un round-trip al backend.
// ---------------------------------------------------------------------------

export const ETIQUETAS_VINCULACION: Record<TipoVinculacion, string> = {
  EXTERNO: "Externo",
  INTERNO: "Interno",
};

export const ETIQUETAS_LICENCIA: Record<CategoriaLicencia, string> = {
  B1: "B1",
  C1: "C1",
  C2: "C2",
  C3: "C3",
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

// ---------------------------------------------------------------------------
// Columnas
// ---------------------------------------------------------------------------

export const getConductoresColumns = (): ColumnDef<ConductorListado>[] => [
  {
    id: "cedula",
    accessorKey: "cedula",
    header: "CÉDULA",
    cell: ({ row }) => (
      <span className="font-medium text-gray-800 dark:text-white/90">
        {row.original.cedula}
      </span>
    ),
  },
  {
    id: "nombre_completo",
    accessorKey: "nombre_completo",
    header: "NOMBRE",
    cell: ({ row }) => (
      <span className="text-sm text-gray-700 dark:text-gray-300">
        {row.original.nombre_completo}
      </span>
    ),
  },
  {
    id: "celular",
    accessorKey: "celular",
    header: "CELULAR",
    cell: ({ row }) => (
      <span className="whitespace-nowrap text-sm tabular-nums text-gray-600 dark:text-gray-400">
        {row.original.celular || "—"}
      </span>
    ),
  },
  {
    id: "tipo_vinculacion",
    accessorKey: "tipo_vinculacion",
    header: "VÍNCULO",
    filterFn: "equals",
    cell: ({ row }) => {
      const tipo = row.original.tipo_vinculacion;
      return (
        <Badge color={tipo === "INTERNO" ? "primary" : "light"} size="sm">
          {ETIQUETAS_VINCULACION[tipo] ?? tipo}
        </Badge>
      );
    },
  },
  {
    id: "licencia",
    header: "LICENCIA",
    enableSorting: false,
    cell: ({ row }) => (
      <div className="flex items-center gap-1.5">
        <PuntoVigencia estado={row.original.estado_licencia} />
        <span className="text-sm text-gray-600 dark:text-gray-400">
          {row.original.licencia_categoria ?? "—"} ·{" "}
          {formatearFecha(row.original.licencia_vencimiento)}
        </span>
      </div>
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
