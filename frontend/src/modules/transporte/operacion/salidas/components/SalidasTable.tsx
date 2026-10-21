// src/modules/transporte/operacion/salidas/components/SalidasTable.tsx
//
// Tabla de Salidas sobre el DataTable compartido, con paginación
// SERVER-SIDE (`manualPagination`): el servidor devuelve SOLO la página pedida
// y `count` (total real del filtro) alimenta el `pageCount`.
//
// Dos apagones deliberados frente a las tablas de Conductores/Flota:
//   · NO se le pasa `globalFilterValue` → el filtro global vive en
//     `SalidasToolbar` y viaja como `?search=`. Si se pasara, TanStack
//     volvería a filtrar en cliente SOBRE la página cargada y escondería
//     filas que el servidor sí encontró.
//   · NO se pasa `sortingValue` ni se enciende `enableSorting` → el backend
//     siempre ordena por `fecha_salida desc, id desc` y no expone
//     `?ordering=`. Ordenar solo la página visible engaña: el TOTAL no
//     cuadraría con el orden que se ve.

import { useCallback } from "react";
import { ColumnDef } from "@tanstack/react-table";

import { DataTable } from "@/components/common/DataTable";
import { SALIDAS_TABLE_CONFIG } from "../salidasView.utils";
import type { Salida } from "@/types/transporte.types";

interface SalidasTableProps {
  /** SOLO la página actual, tal como la devolvió el servidor. */
  salidas: Salida[];
  columns: ColumnDef<Salida, unknown>[];
  isLoading?: boolean;
  /** `count` del servidor / page_size → nº de páginas del paginador. */
  pageCount: number;
  pageIndex: number;
  setPageIndex: (index: number) => void;
  pageSize: number;
  setPageSize: (size: number) => void;
  setVisibleRows: (rows: Salida[]) => void;
  /** Filtros de negocio; el DataTable los pinta en su barra superior. */
  toolbarActions?: React.ReactNode;
}

export const SalidasTable = ({
  salidas,
  columns,
  isLoading = false,
  pageCount,
  pageIndex,
  setPageIndex,
  pageSize,
  setPageSize,
  setVisibleRows,
  toolbarActions,
}: SalidasTableProps) => {
  // Identidad estable: el DataTable guarda este callback en un useMemo y con
  // una función anónima nueva en cada render la tabla se regeneraría.
  const handlePageSizeChange = useCallback(
    (size: number) => {
      setPageSize(size);
      setPageIndex(0);
    },
    [setPageSize, setPageIndex],
  );

  return (
    <DataTable
      data={salidas}
      columns={columns}
      isLoading={isLoading}
      emptyMessage="No hay salidas que coincidan con los filtros."
      enablePagination
      manualPagination
      pageCount={pageCount}
      pageSize={SALIDAS_TABLE_CONFIG.defaultPageSize}
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
