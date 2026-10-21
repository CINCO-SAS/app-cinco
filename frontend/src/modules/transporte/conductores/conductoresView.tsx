// src/modules/transporte/conductores/conductoresView.tsx
//
// Vista de Conductores (F2) — catálogo de transportadores externos e internos.
//
// Deliberadamente liviana (misma gramática que Flota): filtros en una línea +
// tabla. Las altas/ediciones y la baja lógica viven en modales.

"use client";

import { useCallback, useMemo, useState } from "react";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useConductoresData } from "./conductoresView.hooks";
import { getConductoresColumns } from "./conductoresView.utils";
import { ConductoresTable } from "./components/ConductoresTable";
import { ConductoresToolbar } from "./components/ConductoresToolbar";
import { ConductorFormModal } from "./components/ConductorFormModal";
import { ConductorInactivarModal } from "./components/ConductorInactivarModal";
import type { ConductorListado } from "@/types/transporte.types";

const ConductoresView = () => {
  const {
    conductores,
    isLoading,
    loadError,
    recargar,
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
  } = useConductoresData();

  const columns = useMemo(() => getConductoresColumns(), []);

  // `null` → modal cerrado; `number` → id del conductor a editar; `0` → alta.
  const [conductorEnEdicion, setConductorEnEdicion] = useState<number | null>(null);
  const [conductorAInactivar, setConductorAInactivar] =
    useState<ConductorListado | null>(null);

  const cerrarFormulario = useCallback(() => setConductorEnEdicion(null), []);

  const onNuevo = useCallback(() => setConductorEnEdicion(0), []);

  const onEditar = useCallback((conductor: ConductorListado) => {
    setConductorEnEdicion(conductor.id);
  }, []);

  const onInactivar = useCallback((conductor: ConductorListado) => {
    setConductorAInactivar(conductor);
  }, []);

  const toolbarActions = (
    <ConductoresToolbar
      total={conductores.length}
      filtros={filtros}
      actualizarFiltro={actualizarFiltro}
      limpiarFiltros={limpiarFiltros}
      hayFiltrosActivos={hayFiltrosActivos}
      onNuevo={onNuevo}
    />
  );

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6">
      <PageBreadcrumb pageTitle={["Transporte", "Maestros", "Conductores"]} />

      {loadError && (
        <div className="mb-4">
          <Alert
            variant="error"
            title="Error al cargar los conductores"
            message={loadError}
          />
        </div>
      )}

      <ConductoresTable
        conductores={conductores}
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
        onEditar={onEditar}
        onInactivar={onInactivar}
      />

      <ConductorFormModal
        isOpen={conductorEnEdicion !== null}
        conductorId={conductorEnEdicion === 0 ? null : conductorEnEdicion}
        onClose={cerrarFormulario}
        onGuardado={recargar}
      />

      <ConductorInactivarModal
        conductor={conductorAInactivar}
        onClose={() => setConductorAInactivar(null)}
        onInactivado={recargar}
      />
    </div>
  );
};

export default ConductoresView;
