// src/modules/transporte/informes/components/InformeGraficoAreas.tsx
//
// Gráfico "Pagos por Mes, por Área" (legacy F5-2, `loadChartInfoMonthArea`).
//
// QUÉ DATOS USA: `GET /informes/series-chart/` SIN año, es decir histórico
// completo. Es lo que el legacy realmente dibujaba: la función se llamaba
// UNA sola vez en `DOMContentLoaded`, sin parámetros, y el eje X era de
// tipo `time`. Su rótulo ("Reporte Áreas: 2024") estaba hardcodeado en el
// HTML y nunca lo actualizaba el JS, así que aquí el rótulo dice
// "Histórico" en lugar de enseñar un año inventado.
//   · No sigue al selector de periodo de la pantalla.
//   · Solo responde al botón ↻ de la barra.
//
// DOS EJES Y: el área **I&M** se paga en un orden de magnitud distinto
// (el legacy le daba 0–300 M frente a 0–90 M de las demás), así que el
// backend la marca con `yAxis: "a2"` y aquí va al eje derecho. Sin eje
// secundario, la línea de I&M aplastaría al resto del gráfico.
//
// LIBRERÍA: amCharts 5, la que trae el proyecto. El legacy usaba
// JSCharting, que NO está instalada; el backend devuelve el dato crudo
// (nombre + puntos `["<mes>/1/<año>", importe]`), no el formato de
// ninguna librería concreta, así que la traducción es de este archivo.
//
// RÓTULOS DE EJE EN HTML Y NO EN CANVAS: van encima del gráfico y
// heredan el tema claro/oscuro de la app. Ponerlos dentro de amCharts
// obligaría a posicionarlos a mano contra el lienzo, que es justo lo que
// se desajusta al redimensionar.
//
// NO SE REPLICA: el estilo de marcador de `defaultPoint` (círculo con
// contorno negro) que el backend manda solo para I&M. Es detalle
// cosmético; la distinción de I&M ya está en el eje derecho.

"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import Alert from "@/components/ui/alert/Alert";
import type { SerieInforme } from "@/types/transporte.types";
// Tipo a secas: se borra en compilación, no mete amCharts al bundle.
// Hace falta para tipar `raiz` fuera del `await import`.
import type { Root } from "@amcharts/amcharts5";
import { MESES_CORTOS } from "../informesView.utils";

/** Código del eje secundario que manda el backend para I&M. */
const EJE_SECUNDARIO = "a2";

interface FilaGrafico {
  category: string;
  value: number;
}

interface SeriePreparada {
  nombre: string;
  /** true → se dibuja contra el eje derecho. */
  secundario: boolean;
  filas: FilaGrafico[];
}

/** Salida de `preparar`: ejes listos y series listas. */
interface PreparacionGrafico {
  /** Etiquetas únicas del eje X, en orden cronológico. */
  categorias: string[];
  series: SeriePreparada[];
}

/**
 * `["<mes>/1/<año>", importe]` → `{anio, mes}`. El campo central es
 * siempre el día 1 (lo construye `InformeService.series_chart`), así que
 * solo interesan los extremos.
 */
const parsePunto = (
  etiqueta: string,
): { anio: number; mes: number } | null => {
  const partes = etiqueta.split("/");
  if (partes.length < 3) return null;
  const mes = Number(partes[0]);
  const anio = Number(partes[2]);
  if (!Number.isFinite(mes) || !Number.isFinite(anio)) return null;
  return { anio, mes };
};

/**
 * Traduce el backend a lo que necesita amCharts:
 *  · el eje X son las categorías (mes/año) ordenadas cronológicamente,
 *    tomadas de la UNIÓN de todas las series — así las que no tienen
 *    cierto mes simplemente no pintan punto ahí;
 *  · cada serie queda con su nombre y si va al eje derecho.
 */
const preparar = (series: SerieInforme[]): PreparacionGrafico => {
  const periodos = new Map<string, { anio: number; mes: number }>();

  const mapeadas = series.map((serie) => {
    const puntos = new Map<string, number>();
    for (const [etiqueta, valor] of serie.points) {
      const periodo = parsePunto(etiqueta);
      if (!periodo) continue;
      const clave = `${periodo.anio}-${periodo.mes}`;
      periodos.set(clave, periodo);
      puntos.set(clave, valor);
    }
    return { serie, puntos };
  });

  const categorias = [...periodos.values()]
    .sort((a, b) => a.anio - b.anio || a.mes - b.mes)
    .map((p) => ({
      clave: `${p.anio}-${p.mes}`,
      etiqueta: `${MESES_CORTOS[p.mes - 1] ?? p.mes} ${p.anio}`,
    }));

  // El eje X se puebla con la lista única: si se le pasaran todas las
  // filas aplanadas, cada categoría repetiría N veces (una por serie).
  return {
    categorias: categorias.map((categoria) => categoria.etiqueta),
    series: mapeadas.map(({ serie, puntos }) => ({
      nombre: serie.name,
      secundario: serie.yAxis === EJE_SECUNDARIO,
      filas: categorias.flatMap((categoria) => {
        const valor = puntos.get(categoria.clave);
        return valor === undefined
          ? []
          : [{ category: categoria.etiqueta, value: valor }];
      }),
    })),
  };
};

interface InformeGraficoAreasProps {
  series: SerieInforme[];
  isLoading?: boolean;
  // OJO: el error de RED no se mira aquí, lo gestiona `InformeBloque`
  // igual que en el resto de bloques. Este componente solo cubre su
  // propio fallo de renderizado (`fallo`).
}

export const InformeGraficoAreas = ({
  series,
  isLoading = false,
}: InformeGraficoAreasProps) => {
  const contenedor = useRef<HTMLDivElement | null>(null);
  const [fallo, setFallo] = useState("");

  // Recalculado fuera del `useEffect` para que los datos estén listos y
  // ordenados antes de tocar amCharts, y para que el efecto dependa de un
  // valor estable.
  const preparacion = useMemo(() => preparar(series), [series]);
  const seriesPreparadas = preparacion.series;

  // Un solo eje por lado: la izquierda para las áreas normales, la
  // derecha (`opposite`) para I&M.
  const haySecundaria = seriesPreparadas.some((serie) => serie.secundario);

  useEffect(() => {
    if (!contenedor.current || seriesPreparadas.length === 0) return;

    let raiz: Root | null = null;
    let montado = true;

    const dibujar = async () => {
      try {
        setFallo("");
        const am5 = await import("@amcharts/amcharts5");
        const am5xy = await import("@amcharts/amcharts5/xy");
        const am5Animated = await import(
          "@amcharts/amcharts5/themes/Animated"
        );

        if (!montado || !contenedor.current) return;

        raiz = am5.Root.new(contenedor.current);
        // Mismo tema que el resto de gráficos del proyecto. Animated
        // hereda de la tema por defecto, que es la que asigna colores a
        // cada serie y tipografía a los ejes.
        raiz.setThemes([am5Animated.default.new(raiz)]);

        const grafico = raiz.container.children.push(
          am5xy.XYChart.new(raiz, {
            panX: false,
            panY: false,
            wheelX: "none",
            wheelY: "none",
            layout: raiz.verticalLayout,
          }),
        );

        const ejeX = grafico.xAxes.push(
          am5xy.CategoryAxis.new(raiz, {
            categoryField: "category",
            renderer: am5xy.AxisRendererX.new(raiz, {
              minGridDistance: 40,
            }),
          }),
        );
        ejeX.data.setAll(
          preparacion.categorias.map((category) => ({ category })),
        );

        const ejeIzquierdo = grafico.yAxes.push(
          am5xy.ValueAxis.new(raiz, {
            min: 0,
            renderer: am5xy.AxisRendererY.new(raiz, {}),
          }),
        );

        const ejeDerecho = haySecundaria
          ? grafico.yAxes.push(
              am5xy.ValueAxis.new(raiz, {
                min: 0,
                // Dibuja el eje al lado derecho del área de trazado.
                renderer: am5xy.AxisRendererY.new(raiz, { opposite: true }),
              }),
            )
          : undefined;

        for (const preparada of seriesPreparadas) {
          const serie = am5xy.LineSeries.new(raiz, {
            name: preparada.nombre,
            xAxis: ejeX,
            yAxis:
              preparada.secundario && ejeDerecho ? ejeDerecho : ejeIzquierdo,
            valueYField: "value",
            categoryXField: "category",
            tooltip: am5.Tooltip.new(raiz, {
              labelText: `${preparada.nombre}: {valueY}`,
            }),
          });
          serie.strokes.template.setAll({ strokeWidth: 2 });
          // Sin marcadores por punto: en amCharts 5 van por `bullets` y es
          // detalle cosmético (ver cabecera del archivo). El tooltip de la
          // serie sí está activo.
          grafico.series.push(serie);
          serie.data.setAll(preparada.filas);
        }

        const leyenda = grafico.children.push(
          am5.Legend.new(raiz, {
            centerX: am5.percent(50),
            x: am5.percent(50),
            layout: raiz.horizontalLayout,
          }),
        );
        leyenda.data.setAll(grafico.series.values);
      } catch (error) {
        if (!montado) return;
        setFallo("No se pudo dibujar el gráfico en este momento.");
        // eslint-disable-next-line no-console -- diagnóstico en desarrollo
        console.error("Error dibujando el gráfico de áreas:", error);
      }
    };

    void dibujar();

    return () => {
      montado = false;
      raiz?.dispose();
    };
  }, [preparacion, seriesPreparadas, haySecundaria]);

  if (fallo) {
    return (
      <Alert variant="error" title="Gráfico no disponible" message={fallo} />
    );
  }

  if (isLoading) {
    return (
      <p className="px-4 py-16 text-center text-sm text-gray-500 dark:text-gray-400">
        Consultando al servidor…
      </p>
    );
  }

  if (seriesPreparadas.length === 0) {
    return (
      <p className="px-4 py-16 text-center text-sm text-gray-500 dark:text-gray-400">
        No hay salidas aprobadas ni validadas en el histórico.
      </p>
    );
  }

  return (
    <div>
      {/* Qué mide cada eje Y. Izquierda = series sin marcar; derecha = I&M */}
      <div className="mb-1 flex flex-wrap justify-between gap-2 px-1 text-[11px] font-medium text-gray-500 dark:text-gray-400">
        <span>Eje izquierdo · Otras Áreas</span>
        {haySecundaria && <span>Eje derecho · I&amp;M</span>}
      </div>

      <div className="h-[400px] w-full overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-950">
        <div ref={contenedor} className="h-full w-full" />
      </div>
    </div>
  );
};
