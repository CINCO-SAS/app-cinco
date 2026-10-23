// src/modules/transporte/informes/informesView.tsx
//
// Pantalla de Informes (F5) — Tab 2 del legacy "TRANSPORTE / INFORMES".
//
// PANTALLA POR PASOS: hoy se entregan los bloques de los PASOS 2, 3, 4, 5 y 6
// (Transporte Día, Transporte Mes, Reporte Área y Reporte Áreas, el listado
// "Día a Día" y la matriz "Área y Carpeta"). Falta el PASO 7 — Nómina,
// Liquidación y Cuenta de Cobro—, delimitado por `BloquePendiente` para que
// se vea desde ya QUÉ falta, sin inventar datos ni dejar huecos en blanco.
//
// PENDIENTE FUERA DE ESTOS PASOS: el legacy añadía en la cabecera de
// "Transporte Mes" un botón de exportación y, dentro de "Reporte Área",
// un botón de Excel y un icono de refresco WFM para el área "I&M". No
// están cableados todavía (son una decisión de alcance, no un bloque).
//
// Los KPIs van FUERA de la barra de filtros. Aquí cada bloque enseña su
// total en el pie de tabla (fila TOTALES), así que no se duplican en
// tarjetas: la información existe una sola vez.
//
// Se apilan en vertical (no en columnas como el legacy) porque las tablas
// tienen 6-7 columnas y apretarlas a media anchura ilegibiliza el dinero.

"use client";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";

import { useInformesData } from "./informesView.hooks";
import { etiquetaFecha, etiquetaPeriodo } from "./informesView.utils";
import { InformeBloque } from "./components/InformeBloque";
import { InformeDiaADia } from "./components/InformeDiaADia";
import { InformeGraficoAreas } from "./components/InformeGraficoAreas";
import { InformeMatrizAnual } from "./components/InformeMatrizAnual";
import { InformeReporteArea } from "./components/InformeReporteArea";
import { InformeToolbar } from "./components/InformeToolbar";
import type {
  AreaInforme,
  AreaMatrizInforme,
  SerieInforme,
} from "@/types/transporte.types";

/**
 * Referencias ESTABLES para "aún no hay datos".
 *
 * Sin esto, `serieChart?.series ?? []` literal construiría un array nuevo
 * en cada render, `useMemo` del gráfico lo detectaría como cambio y
 * volvería a montar amCharts sin ningún motivo.
 */
const AREAS_VACIAS: AreaInforme[] = [];
const SERIES_VACIAS: SerieInforme[] = [];
const AREAS_MATRIZ_VACIAS: AreaMatrizInforme[] = [];

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
    serieChart,
    cargandoSerie,
    errorSerie,
    diaADia,
    matriz,
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
          areas={informeDia?.areas ?? AREAS_VACIAS}
          isLoading={cargandoDia}
          error={errorDia}
        />

        <InformeBloque
          titulo="Transporte Mes"
          periodo={etiquetaPeriodo(mes, anio)}
          areas={informeArea?.areas ?? AREAS_VACIAS}
          isLoading={cargandoArea}
          error={errorArea}
          nota={
            soloAprobados
              ? "Solo aprobados: los TOTALES suman únicamente salidas APROBADO o VALIDADO. " +
                "El desglose de la columna Estado refleja todas las salidas."
              : undefined
          }
        />

        {/* Mismo periodo y misma respuesta que "Transporte Mes": en el
            legacy `loadInfoArea()` construía ambos bloques en un solo
            recorrido del mismo dataset, y `arr_estado` se acumula antes
            del filtro. Por eso el interruptor NO mueve esta tabla.
            Si la petición falló ya se avisó arriba, así que aquí no se
            repite la misma alerta. */}
        {!errorArea && (
          <InformeBloque
            titulo="Reporte Área"
            periodo={etiquetaPeriodo(mes, anio)}
            isLoading={cargandoArea}
            nota="No responde al interruptor «Solo aprobados»: los estados se cuentan sobre todas las salidas del mes."
          >
            <InformeReporteArea
              areas={informeArea?.areas ?? AREAS_VACIAS}
              isLoading={cargandoArea}
            />
          </InformeBloque>
        )}

        {/* Histórico completo: NO sigue al selector de periodo (así lo
            cargaba el legacy y así lo eligió el negocio). Solo se mueve
            con el botón ↻ de la barra. */}
        <InformeBloque
          titulo="Reporte Áreas · Pagos por Mes, por Área"
          periodo="Histórico"
          isLoading={cargandoSerie}
          error={errorSerie}
          nota="Histórico completo de salidas APROBADO/VALIDADO: no sigue el selector de año ni el interruptor de arriba."
        >
          <InformeGraficoAreas
            series={serieChart?.series ?? SERIES_VACIAS}
            isLoading={cargandoSerie}
          />
        </InformeBloque>

        {/* Paso 5: el informe mensual F5-3 como listado. Su estado es
            propio (filtros + paginación server-side); el periodo y el ↻
            global sí le llegan desde la barra. */}
        <InformeBloque
          titulo="Día a Día"
          periodo={etiquetaPeriodo(mes, anio)}
          isLoading={diaADia.isLoading}
          error={diaADia.error}
          nota={
            "Salidas no eliminadas del periodo, ordenadas día a día. Estado, área, " +
            "carpeta, sede y búsqueda se filtran en el servidor; sin filtro, las " +
            "eliminadas quedan fuera."
          }
        >
          <InformeDiaADia datos={diaADia} />
        </InformeBloque>

        {/* Paso 6: la matriz área × meses, que es el mismo histórico del
            gráfico en forma de tabla. Responde SOLO al año. */}
        <InformeBloque
          titulo="Área y Carpeta"
          periodo={`AÑO ${anio}`}
          isLoading={matriz.isLoading}
          error={matriz.error}
          nota={
            "Σ total_a_pagar (valor día ± novedad) de las salidas no eliminadas, por " +
            "área y mes: la tabla del gráfico de arriba. No sigue el selector de mes " +
            "ni el interruptor «Solo aprobados», solo el año. «—» = mes sin salidas."
          }
        >
          <InformeMatrizAnual areas={matriz.matriz?.areas ?? AREAS_MATRIZ_VACIAS} />
        </InformeBloque>

        <BloquePendiente
          titulo="Nómina · Liquidación · Cuenta de Cobro"
          motivo="Paso 7 del plan."
        />
      </div>
    </div>
  );
};
