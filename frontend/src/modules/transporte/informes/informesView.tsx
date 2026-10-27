// src/modules/transporte/informes/informesView.tsx
//
// Pantalla de Informes (F5) — Tab 2 del legacy "TRANSPORTE / INFORMES".
//
// PANTALLA POR PASOS: se entregan COMPLETOS los PASOS 2 a 7 — Transporte
// Día, Transporte Mes, Reporte Área y Reporte Áreas, el listado "Día a
// Día", la matriz "Área y Carpeta" y el cierre del mes (Nómina,
// Liquidación y Cuenta de Cobro). Con el Paso 7 ya no queda ningún
// `BloquePendiente` en la pantalla: el componente se retiró al no tener
// reservas que marcar.
//
// PENDIENTE FUERA DE ESTOS PASOS: dentro de "Reporte Área" el legacy
// añadía un botón de Excel y un icono de refresco WFM para el área "I&M".
// El botón Excel (↓ Excel) YA ESTÁ CABLEADO via `InformeExportarReporteArea`
// (exporta el resumen de estados por área como CSV con BOM UTF-8).
// Pendiente: el refresco WFM (`POST /wfm/validar/`) — escribe validaciones,
// requiere permiso explícito y confirmación del usuario.
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
import { InformeCuentaCobro } from "./components/InformeCuentaCobro";
import { InformeDiaADia } from "./components/InformeDiaADia";
import { InformeExportarMes } from "./components/InformeExportarMes";
import { InformeExportarReporteArea } from "./components/InformeExportarReporteArea";
import { InformeGraficoAreas } from "./components/InformeGraficoAreas";
import { InformeLiquidacion } from "./components/InformeLiquidacion";
import { InformeMatrizAnual } from "./components/InformeMatrizAnual";
import { InformeNomina } from "./components/InformeNomina";
import { InformeReporteArea } from "./components/InformeReporteArea";
import { InformeToolbar } from "./components/InformeToolbar";
import type {
  AreaInforme,
  AreaMatrizInforme,
  FilaLiquidacionInforme,
  FilaNominaInforme,
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
const FILAS_NOMINA_VACIAS: FilaNominaInforme[] = [];
const FILAS_LIQUIDACION_VACIAS: FilaLiquidacionInforme[] = [];

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
    cierre,
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
          acciones={<InformeExportarMes mes={mes} anio={anio} />}
          areas={informeArea?.areas ?? AREAS_VACIAS}
          isLoading={cargandoArea}
          error={errorArea}
          nota={
            [
              soloAprobados
                ? "Solo aprobados: los TOTALES suman únicamente salidas APROBADO o VALIDADO. " +
                  "El desglose de la columna Estado refleja todas las salidas."
                : undefined,
              "El archivo exportado trae TODAS las salidas del mes excepto las eliminadas: " +
                "el interruptor «Solo aprobados» es de la tabla, no del export.",
            ]
              .filter(Boolean)
              .join(" ")
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
            acciones={
              <InformeExportarReporteArea
                areas={informeArea?.areas ?? AREAS_VACIAS}
                mes={mes}
                anio={anio}
                periodo={etiquetaPeriodo(mes, anio)}
              />
            }
            isLoading={cargandoArea}
            nota="No responde al interruptor «Solo aprobados»: los estados se cuentan sobre todas las salidas del mes."
          >
            <InformeReporteArea
              areas={informeArea?.areas ?? AREAS_VACIAS}
              isLoading={cargandoArea}
              mes={mes}
              anio={anio}
              onWfmValidado={recargar}
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

        {/* Paso 7: el cierre del mes en tres bloques con distinta forma de
            lectura — nómina (por carpeta), liquidación (por vehículo) y la
            cuenta de cobro imprimible. Los dos primeros comparten los
            mismos criterios de pago; la cuenta de cobro es un documento,
            no una tabla. */}
        <InformeBloque
          titulo="Nómina"
          periodo={etiquetaPeriodo(mes, anio)}
          isLoading={cierre.isLoading}
          error={cierre.error}
          nota={
            "Mes agrupado por (carpeta, placa). Excluye REPORTADO y ELIMINADO: no se " +
            "paga lo pendiente ni lo borrado. Retefuente 1 % sobre el valor base; el " +
            "pagador sale de los datos bancarios vigentes del vehículo en el servidor " +
            "(sin dato, el propietario). El centro de costos llegará cuando el " +
            "backend consuma B11 (deuda C del informe F5), hoy vacío en el origen."
          }
        >
          <InformeNomina filas={cierre.nomina?.filas ?? FILAS_NOMINA_VACIAS} />
        </InformeBloque>

        <InformeBloque
          titulo="Liquidación"
          periodo={etiquetaPeriodo(mes, anio)}
          isLoading={cierre.isLoading}
          error={cierre.error}
          nota={
            "El mismo mes, una fila por vehículo (lo que se paga por propietario). " +
            "Mismos criterios que la nómina: excluye REPORTADO y ELIMINADO y aplica " +
            "retefuente 1 % (a pagar = valor base − rete). La cuenta llega resuelta " +
            "en servidor desde los datos bancarios vigentes (CR-13)."
          }
        >
          <InformeLiquidacion
            filas={cierre.liquidacion?.filas ?? FILAS_LIQUIDACION_VACIAS}
          />
        </InformeBloque>

        <InformeBloque
          titulo="Cuenta de Cobro"
          periodo={etiquetaPeriodo(mes, anio)}
          isLoading={cierre.isLoading}
          error={cierre.error}
          nota={
            "Documento imprimible del alquiler del vehículo: se abre en pestaña nueva " +
            "para imprimir a PDF. El importe, el pagador y el consecutivo se calculan " +
            "EN SERVIDOR desde las salidas del mes (F5-1) — el legacy los leía de " +
            "campos ocultos del formulario, manipulables desde el navegador."
          }
        >
          <InformeCuentaCobro
            mes={mes}
            anio={anio}
            vehiculos={cierre.liquidacion?.filas ?? FILAS_LIQUIDACION_VACIAS}
          />
        </InformeBloque>
      </div>
    </div>
  );
};
