// src/modules/transporte/flota/flotaView.tsx
//
// Vista de Flota Vehicular — T1 del módulo Transporte.
//
// Muestra el catálogo de flota con el semáforo SOAT/CDA calculado en
// servidor (E1) y los filtros de gestión (contrato, estado, vigencia).

"use client";

import { useMemo } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useFlotaData } from "./flotaView.hooks";
import { getFlotaColumns } from "./flotaView.utils";
import { FlotaTable } from "./components/FlotaTable";
import { FlotaToolbar } from "./components/FlotaToolbar";

const FlotaView = () => {
  const {
    vehiculos,
    resumen,
    isLoading,
    loadError,
    filtros,
    actualizarFiltro,
    limpiarFiltros,
    hayFiltrosActivos,
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
  } = useFlotaData();

  const columns = useMemo(() => getFlotaColumns(), []);

  const toolbarActions = (
    <FlotaToolbar
      resumen={resumen}
      filtros={filtros}
      actualizarFiltro={actualizarFiltro}
      limpiarFiltros={limpiarFiltros}
      hayFiltrosActivos={hayFiltrosActivos}
    />
  );

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6">
      <PageBreadcrumb pageTitle={["Transporte", "Flota Vehicular"]} />

      <div className="mb-4 flex flex-col gap-3">
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Catálogo de flota automotor (4+ ruedas). El semáforo SOAT/CDA se
          calcula en servidor con la regla: vigente &gt; 60 días, por vencer
          31–60, vencida ≤ 30.
        </p>

        {loadError && (
          <Alert
            variant="error"
            title="Error al cargar la flota"
            message={loadError}
          />
        )}
      </div>

      <FlotaTable
        vehiculos={vehiculos}
        columns={columns}
        isLoading={isLoading}
        globalFilter={globalFilter}
        setGlobalFilter={setGlobalFilter}
        sorting={sorting}
        setSorting={setSorting}
        pageIndex={pageIndex}
        setPageIndex={setPageIndex}
        pageSize={pageSize}
        setPageSize={setPageSize}
        visibleRows={visibleRows}
        setVisibleRows={setVisibleRows}
        toolbarActions={toolbarActions}
      />
    </div>
  );
};

export default FlotaView;
