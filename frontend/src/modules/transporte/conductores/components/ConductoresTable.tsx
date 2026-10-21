// src/modules/transporte/conductores/components/ConductoresTable.tsx
//
// Tabla de conductores envolviendo el DataTable compartido (mismo contrato que
// FlotaTable) + acciones por fila: editar y, solo para activos, inactivar.

import { useCallback } from "react";
import { ColumnDef, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import { CONDUCTORES_TABLE_CONFIG } from "../conductoresView.utils";
import type { ConductorListado } from "@/types/transporte.types";

interface ConductoresTableProps {
  conductores: ConductorListado[];
  columns: ColumnDef<ConductorListado, unknown>[];
  isLoading?: boolean;
  globalFilter: string;
  setGlobalFilter: (value: string) => void;
  sorting: SortingState;
  setSorting: (sorting: SortingState) => void;
  pageIndex: number;
  setPageIndex: (index: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
  visibleRows: ConductorListado[];
  setVisibleRows: (rows: ConductorListado[]) => void;
  toolbarActions?: React.ReactNode;
  onEditar: (conductor: ConductorListado) => void;
  onInactivar: (conductor: ConductorListado) => void;
}

const BOTON_ACCION_CLASES =
  "rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 " +
  "hover:text-brand-500 dark:hover:bg-white/5 dark:hover:text-brand-400";

export const ConductoresTable = ({
  conductores,
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
  onEditar,
  onInactivar,
}: ConductoresTableProps) => {
  // `useCallback` mantiene estable la identidad de `renderRowActions`, que el
  // DataTable mete en el useMemo de columnas: sin esto la tabla se regenera
  // en cada render.
  const renderRowActions = useCallback(
    (conductor: ConductorListado) => (
      <div className="flex items-center justify-end gap-0.5">
        <button
          type="button"
          title="Editar conductor"
          aria-label={`Editar a ${conductor.nombre_completo}`}
          onClick={() => onEditar(conductor)}
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

        {conductor.activo && (
          <button
            type="button"
            title="Inactivar conductor"
            aria-label={`Inactivar a ${conductor.nombre_completo}`}
            onClick={() => onInactivar(conductor)}
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
                d="M13 11H9m11 5a5 5 0 01-10 0m10 0h3M5 11h1m8 0h2M4 21a16 16 0 0116-16"
              />
            </svg>
          </button>
        )}
      </div>
    ),
    [onEditar, onInactivar],
  );

  return (
    <DataTable
      data={conductores}
      columns={columns}
      isLoading={isLoading}
      emptyMessage="No hay conductores que coincidan con los filtros."
      enablePagination
      pageSize={CONDUCTORES_TABLE_CONFIG.defaultPageSize}
      enableGlobalFilter
      globalFilterPlaceholder="Buscar por cédula, nombre o celular..."
      enableSorting
      enableColumnFilters
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
