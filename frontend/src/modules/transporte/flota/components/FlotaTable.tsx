// src/modules/transporte/flota/components/FlotaTable.tsx
//
// Tabla de flota envolviendo el DataTable compartido, con el mismo contrato
// que `GestionActividadesTable` (estado controlado desde el hook de la vista).

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
}

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
}: FlotaTableProps) => (
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
    toolbarActions={toolbarActions}
  />
);
