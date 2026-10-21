import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
} from "@tanstack/react-table";
import { ReactNode } from "react";

interface DataTableProps<TData> {
  data: TData[];
  columns: ColumnDef<TData>[];

  isLoading?: boolean;
  emptyMessage?: string;

  enablePagination?: boolean;
  pageSize?: number;

  /**
   * La paginación la resuelve el SERVIDOR (una página de datos a la vez) en
   * vez de paginar en cliente. Imprescindible en listados grandes —salidas
   * tiene ~250 mil filas— donde traerlo todo no es una opción.
   *
   * Si está activo, el DataTable NO aplica `getPaginationRowModel` (si no
   * paginaría dos veces) y el paginador usa `pageCount` en vez de contar
   * filas que ya son solo la página actual.
   *
   * En este modo conviene apagar `enableGlobalFilter`: el filtrado global
   * del cliente solo vería la página cargada. La búsqueda debe ir al
   * servidor, que es quien conoce las ~250 mil filas.
   */
  manualPagination?: boolean;
  /** Nº total de páginas que reportó el servidor. Requiere `manualPagination`. */
  pageCount?: number;

  enableGlobalFilter?: boolean;
  enableColumnFilters?: boolean;
  enableSorting?: boolean;
  enableColumnVisibility?: boolean;

  globalFilterPlaceholder?: string;
  enablePageSizeSelector?: boolean;
  pageSizeOptions?: number[];

  initialGlobalFilter?: string;
  initialColumnFilters?: ColumnFiltersState;
  initialSorting?: SortingState;
  initialColumnVisibility?: VisibilityState;

  globalFilterValue?: string;
  columnFiltersValue?: ColumnFiltersState;
  sortingValue?: SortingState;
  columnVisibilityValue?: VisibilityState;
  pageIndexValue?: number;
  pageSizeValue?: number;

  onGlobalFilterChange?: (value: string) => void;
  onColumnFiltersChange?: (filters: ColumnFiltersState) => void;
  onSortingChange?: (sorting: SortingState) => void;
  onColumnVisibilityChange?: (visibility: VisibilityState) => void;
  onPageChange?: (pageIndex: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  onVisibleDataChange?: (rows: TData[]) => void;

  onRowClick?: (row: TData) => void;
  renderRowActions?: (row: TData) => ReactNode;
  toolbarActions?: ReactNode;
}

export type { DataTableProps };
