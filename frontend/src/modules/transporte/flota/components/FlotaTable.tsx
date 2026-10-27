import { useCallback } from "react";
import { ColumnDef, SortingState } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import { FLOTA_TABLE_CONFIG } from "../flotaView.utils";
import type { VehiculoListado } from "@/types/transporte.types";

interface FlotaTableProps {
  vehiculos: VehiculoListado[];
  columns: ColumnDef<VehiculoListado, unknown>[];
  isLoading?: boolean;
  globalFilter: string;
  setGlobalFilter: (value: string) => void;
  sorting: SortingState;
  setSorting: (sorting: SortingState) => void;
  pageIndex: number;
  setPageIndex: (index: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
  visibleRows: VehiculoListado[];
  setVisibleRows: (rows: VehiculoListado[]) => void;
  toolbarActions?: React.ReactNode;
  onEditar?: (vehiculo: VehiculoListado) => void;
  onInactivar?: (vehiculo: VehiculoListado) => void;
}

const BOTON_ACCION_CLASES =
  "rounded-md p-1.5 text-gray-400 transition-colors hover:bg-gray-100 " +
  "hover:text-brand-500 dark:hover:bg-white/5 dark:hover:text-brand-400";

export const FlotaTable = ({
  vehiculos,
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
}: FlotaTableProps) => {
  const renderRowActions = useCallback(
    (vehiculo: VehiculoListado) => (
      <div className="flex items-center justify-end gap-0.5">
        {onEditar && (
          <button
            type="button"
            title="Editar vehículo"
            aria-label={`Editar vehículo con placa ${vehiculo.placa}`}
            onClick={() => onEditar(vehiculo)}
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
        )}

        {onInactivar && vehiculo.activo && (
          <button
            type="button"
            title="Inactivar vehículo"
            aria-label={`Inactivar vehículo con placa ${vehiculo.placa}`}
            onClick={() => onInactivar(vehiculo)}
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
                d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"
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
      data={vehiculos}
      columns={columns}
      isLoading={isLoading}
      enablePagination
      pageSize={FLOTA_TABLE_CONFIG.defaultPageSize}
      emptyMessage="No hay vehículos que coincidan con los filtros."
      enableGlobalFilter
      globalFilterPlaceholder="Buscar por placa, marca o conductor..."
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
