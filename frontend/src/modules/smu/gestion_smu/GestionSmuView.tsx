// src/modules/smu/gestion_smu/GestionSmuView.tsx
//
// Tabla de gestión y supervisión de los formularios SMU. Reutiliza el
// `DataTable` común, la paginación/búsqueda sincronizadas con la URL y el
// export CSV del módulo de Operaciones.

"use client";

import { useMemo } from "react";
import { DataTable } from "@/components/common/DataTable";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import Alert from "@/components/ui/alert/Alert";
import { useAuthStore } from "@/store/auth.store";
import { hasGestionSmuPermission } from "@/utils/permission";
import { getGestionSmuColumns } from "./columns";
import { GESTION_SMU_CONFIG } from "./constants";
import { GestionSmuToolbar } from "./GestionSmuToolbar";
import { useGestionSmuData } from "./useGestionSmuData";

const GestionSmuView = () => {
  const user = useAuthStore((state) => state.user);
  const tieneAcceso = hasGestionSmuPermission(user);

  const {
    actividades,
    filasFiltradas,
    filtros,
    cambiarFiltro,
    isLoading,
    loadError,
    globalFilter,
    setGlobalFilter,
    sorting,
    setSorting,
    pageIndex,
    setPageIndex,
    pageSize,
    setPageSize,
  } = useGestionSmuData();

  const columns = useMemo(() => getGestionSmuColumns(), []);

  if (!tieneAcceso) {
    return (
      <div className="w-full min-w-0 overflow-x-hidden">
        <PageBreadcrumb pageTitle={[...GESTION_SMU_CONFIG.breadcrumbTitles]} />
        <Alert
          variant="warning"
          title="Sin acceso a Gestión SMU"
          message="Tu área o carpeta no tiene habilitada la supervisión de formularios SMU."
        />
      </div>
    );
  }

  return (
    <div className="w-full min-w-0 overflow-x-hidden">
      <PageBreadcrumb pageTitle={[...GESTION_SMU_CONFIG.breadcrumbTitles]} />

      <div className="w-full min-w-0 overflow-x-hidden rounded-2xl border border-gray-200 bg-white px-5 py-7 xl:px-10 xl:py-12 dark:border-gray-800 dark:bg-white/3">
        <div className="mx-auto w-full max-w-157.5 text-center">
          <h3 className="text-theme-xl mb-4 font-semibold text-gray-800 sm:text-2xl dark:text-white/90">
            {GESTION_SMU_CONFIG.title}
          </h3>

          <p className="text-gray-600 dark:text-white/70">
            {GESTION_SMU_CONFIG.description}
          </p>
        </div>

        {loadError && (
          <div className="mt-6">
            <Alert
              variant="error"
              title="No fue posible cargar los formularios"
              message={loadError}
            />
          </div>
        )}

        <div className="mt-8 min-h-0 min-w-0 overflow-x-hidden md:h-112">
          <DataTable
            data={filasFiltradas}
            columns={columns}
            isLoading={isLoading}
            emptyMessage={GESTION_SMU_CONFIG.emptyMessage}
            pageSize={pageSize}
            pageSizeValue={pageSize}
            pageIndexValue={pageIndex}
            onPageChange={setPageIndex}
            onPageSizeChange={setPageSize}
            pageSizeOptions={[...GESTION_SMU_CONFIG.pageSizeOptions]}
            enableGlobalFilter
            globalFilterPlaceholder="Buscar OT, estación, cédula, responsable…"
            globalFilterValue={globalFilter}
            onGlobalFilterChange={setGlobalFilter}
            enableSorting
            sortingValue={sorting}
            onSortingChange={setSorting}
            toolbarActions={
              <GestionSmuToolbar
                filtros={filtros}
                onFiltroChange={cambiarFiltro}
                filas={filasFiltradas}
                total={actividades.length}
              />
            }
          />
        </div>
      </div>
    </div>
  );
};

export default GestionSmuView;
