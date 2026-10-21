// src/modules/transporte/operacion/reporte-fotografico/components/ReporteFotoTable.tsx
//
// Tabla sobre el DataTable compartido con paginación SERVER-SIDE
// (`manualPagination`): el servidor devuelve SOLO la página pedida y `count`
// alimenta el `pageCount`.
//
// Igual que en Salidas se evitan dos trampas:
//   · NO se pasa `globalFilterValue` → TanStack volvería a filtrar en cliente
//     SOBRE la página cargada y escondería filas que el servidor sí encontró.
//   · NO se pasa `sortingValue`: la ordenación es del servidor
//     (`-fecha, -hora, -id`) y no está expuesta como parámetro.

import { useCallback } from "react";
import { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import { REPORTES_TABLE_CONFIG } from "../reporteFotoView.hooks";
import type { ReporteFotografico } from "@/types/transporte.types";

interface ReporteFotoTableProps {
  /** SOLO la página actual, tal como la devolvió el servidor. */
  reportes: ReporteFotografico[];
  columns: ColumnDef<ReporteFotografico, unknown>[];
  isLoading?: boolean;
  pageCount: number;
  pageIndex: number;
  setPageIndex: (index: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
  setVisibleRows: (rows: ReporteFotografico[]) => void;
  toolbarActions?: React.ReactNode;
}

export const ReporteFotoTable = ({
  reportes,
  columns,
  isLoading = false,
  pageCount,
  pageIndex,
  setPageIndex,
  pageSize,
  setPageSize,
  setVisibleRows,
  toolbarActions,
}: ReporteFotoTableProps) => {
  // Identidad estable: el DataTable memoiza este callback.
  const handlePageSizeChange = useCallback(
    (size: number) => {
      setPageSize(size);
      setPageIndex(0);
    },
    [setPageSize, setPageIndex],
  );

  return (
    <DataTable
      data={reportes}
      columns={columns}
      isLoading={isLoading}
      emptyMessage="No hay reportes que coincidan con los filtros."
      enablePagination
      manualPagination
      pageCount={pageCount}
      pageSize={REPORTES_TABLE_CONFIG.defaultPageSize}
      pageSizeOptions={[25, 50, 100]}
      pageIndexValue={pageIndex}
      pageSizeValue={pageSize}
      onPageChange={setPageIndex}
      onPageSizeChange={handlePageSizeChange}
      onVisibleDataChange={setVisibleRows}
      toolbarActions={toolbarActions}
    />
  );
};
