// src/modules/transporte/duenos/components/DuenosTable.tsx
//
// Tabla de dueños de vehículos con acciones: Ver Ficha (Vehículos + Bancarios) y Editar.

import { useCallback } from "react";
import { ColumnDef, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import { DUENOS_TABLE_CONFIG } from "../duenosView.utils";
import type { DuenoResumen } from "@/types/transporte.types";

interface DuenosTableProps {
  duenos: DuenoResumen[];
  columns: ColumnDef<DuenoResumen, unknown>[];
  isLoading?: boolean;
  globalFilter: string;
  setGlobalFilter: (value: string) => void;
  sorting: SortingState;
  setSorting: (sorting: SortingState) => void;
  pageIndex: number;
  setPageIndex: (index: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
  visibleRows: DuenoResumen[];
  setVisibleRows: (rows: DuenoResumen[]) => void;
  toolbarActions?: React.ReactNode;
  onVerFicha: (dueno: DuenoResumen) => void;
  onEditar: (dueno: DuenoResumen) => void;
}

const BOTON_ACCION_CLASES =
  "rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 " +
  "hover:text-brand-500 dark:hover:bg-white/5 dark:hover:text-brand-400";

export const DuenosTable = ({
  duenos,
  columns,
  isLoading = false,
  globalFilter,
  setGlobalFilter,
  sorting,
  setSorting,
  pageIndex,
  setPageIndex,
  pageSize,
  setPageSize,
  visibleRows,
  setVisibleRows,
  toolbarActions,
  onVerFicha,
  onEditar,
}: DuenosTableProps) => {
  const renderRowActions = useCallback(
    (dueno: DuenoResumen) => (
      <div className="flex items-center justify-end gap-1">
        <button
          type="button"
          title="Ver ficha de vehículos y cuentas bancarias"
          aria-label={`Ver ficha de ${dueno.nombre}`}
          onClick={() => onVerFicha(dueno)}
          className="flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50 dark:text-brand-400 dark:hover:bg-brand-500/10 transition"
        >
          <svg
            className="h-3.5 w-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
            />
          </svg>
          Gestionar
        </button>

        <button
          type="button"
          title="Editar datos básicos del dueño"
          aria-label={`Editar datos de ${dueno.nombre}`}
          onClick={() => onEditar(dueno)}
          className={BOTON_ACCION_CLASES}
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
            />
          </svg>
        </button>
      </div>
    ),
    [onVerFicha, onEditar],
  );

  return (
    <DataTable
      data={duenos}
      columns={columns}
      isLoading={isLoading}
      enablePagination
      pageSize={DUENOS_TABLE_CONFIG.defaultPageSize}
      emptyMessage="No hay dueños registrados que coincidan con los filtros."
      enableGlobalFilter
      globalFilterPlaceholder="Buscar por cédula o nombre del dueño..."
      enableSorting
      enableColumnFilters
      enableColumnVisibility
      pageSizeOptions={[10, 25, 50, 100]}
      globalFilterValue={globalFilter}
      sortingValue={sorting}
      pageIndexValue={pageIndex}
      pageSizeValue={pageSize}
      onGlobalFilterChange={(value) => {
        setGlobalFilter(value);
        setPageIndex(0);
      }}
      onSortingChange={(nextSorting) => {
        setSorting(nextSorting);
        setPageIndex(0);
      }}
      onPageChange={setPageIndex}
      onPageSizeChange={(size) => {
        setPageSize(size);
        setPageIndex(0);
      }}
      onVisibleDataChange={setVisibleRows}
      renderRowActions={renderRowActions}
      toolbarActions={toolbarActions}
    />
  );
};
