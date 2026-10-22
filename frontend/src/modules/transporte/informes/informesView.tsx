// src/modules/transporte/informes/informesView.tsx
//
// Pantalla de Informes (F5) — Tab 2 del legacy "TRANSPORTE / INFORMES".
//
// PANTALLA POR PASOS: hoy solo se entregan los bloques del PASO 2
// (Transporte Día y Transporte Mes). El resto de bloques del legacy —
// Reporte por Área, Día a Día, Área y Carpeta, Nómina, Liquidación y
// Cuenta de Cobro— van delimitados por `BloquePendiente` para que se vea
// desde ya QUÉ falta, sin inventar datos ni dejar huecos en blanco.
//
// Los KPIs van FUERA de la barra de filtros. Aquí los dos bloques ya
// enseñan su total en el pie de tabla (fila TOTALES), así que no se
// duplican en tarjetas: la información existe una sola vez.
//
// Se apila en vertical (no en 2 columnas como el legacy) porque cada tabla
// tiene 7 columnas y apretarlas en la mitad de ancho ilegibiliza el dinero.

"use client";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";

import { useInformesData } from "./informesView.hooks";
import { etiquetaFecha, etiquetaPeriodo } from "./informesView.utils";
import { InformeBloque } from "./components/InformeBloque";
import { InformeToolbar } from "./components/InformeToolbar";

/**
 * Reserva visible de un bloque del legacy que aún no se ha migrado en este
 * paso. No es una omisión accidental: deja el hueco acotado en pantalla.
 */
const BloquePendiente = ({
  titulo,
  motivo,
}: {
  titulo: string;
  motivo: string;
}) => (
  <section className="rounded-xl border border-dashed border-gray-300 bg-gray-50/60 dark:border-gray-700 dark:bg-gray-900/40">
    <header className="border-b border-dashed border-gray-300 px-4 py-3 dark:border-gray-700">
      <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400">
        {titulo}
      </h3>
    </header>
    <p className="px-4 py-5 text-sm text-gray-500 dark:text-gray-400">{motivo}</p>
  </section>
);

export const InformesView = () => {
  const {
    fecha,
    mes,
    anio,
    dia,
    maximoDia,
    hoy,
    cambiarAnio,
    cambiarMes,
    setDia,
    irAlPrimero,
    irAHoy,
    soloAprobados,
    setSoloAprobados,
    informeDia,
    informeArea,
    cargandoDia,
    cargandoArea,
    errorDia,
    errorArea,
    recargar,
  } = useInformesData();

  return (
    <div className="mx-auto max-w-screen-2xl p-4 sm:p-6">
      <PageBreadcrumb pageTitle={["Transporte", "Administración", "Informes"]} />

      {/* Filtros. Los KPIs/totalidades van fuera de aquí, en cada tabla. */}
      <div className="mb-4 rounded-xl border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900">
        <InformeToolbar
          anio={anio}
          mes={mes}
          dia={dia}
          maximoDia={maximoDia}
          hoy={hoy}
          cambiarAnio={cambiarAnio}
          cambiarMes={cambiarMes}
          setDia={setDia}
          irAlPrimero={irAlPrimero}
          irAHoy={irAHoy}
          soloAprobados={soloAprobados}
          setSoloAprobados={setSoloAprobados}
          recargar={recargar}
        />
      </div>

      <div className="flex flex-col gap-4">
        <InformeBloque
          titulo="Transporte Día"
          periodo={etiquetaFecha(fecha)}
          areas={informeDia?.areas ?? []}
          isLoading={cargandoDia}
          error={errorDia}
        />

        <InformeBloque
          titulo="Transporte Mes"
          periodo={etiquetaPeriodo(mes, anio)}
          areas={informeArea?.areas ?? []}
          isLoading={cargandoArea}
          error={errorArea}
          nota={
            soloAprobados
              ? "Solo aprobados: los TOTALES suman únicamente salidas APROBADO o VALIDADO. " +
                "El desglose de la columna Estado refleja todas las salidas."
              : undefined
          }
        />

        <BloquePendiente
          titulo="Reporte por Área"
          motivo="Paso 3 del plan de migración: se construye desde el detalle ya disponible en /salidas/, sin endpoint nuevo."
        />
        <BloquePendiente
          titulo="Día a Día"
          motivo="Paso 4 del plan: matriz día × área del mes."
        />
        <BloquePendiente
          titulo="Área y Carpeta"
          motivo="Paso 5 del plan."
        />
        <BloquePendiente
          titulo="Nómina · Liquidación · Cuenta de Cobro"
          motivo="Paso 6 del plan."
        />
      </div>
    </div>
  );
};
