// src/modules/transporte/informes/informesView.hooks.ts
//
// Estado de la pantalla de Informes (F5): periodo, interruptor "Aprobados"
// y carga de los bloques Día y Mes.
//
// POR QUÉ UN SOLO ESTADO DE PERIODO: en el legacy un único calendario
// alimentaba toda la pantalla, y de ahí que elegir un mes recolocara el día
// en el 1 (o en "hoy" si era el mes en curso). Mantener `anio`/`mes`/`dia`
// juntos hace que los dos bloques no puedan divergir: el bloque Día siempre
// cae dentro del mes que está visible en el bloque Mes.
//
// El interruptor "Aprobados" afecta SOLO al bloque Mes. Es lo que hace el
// backend —`/informes/area/` admite `solo_aprobados`, `/informes/dia/` no—
// y también el legacy, que leía el checkbox en `loadInfoDia` pero nunca lo
// usaba.

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type {
  InformeArea,
  InformeDia,
  InformeSeriesChart,
} from "@/types/transporte.types";
import { fechaISO, ultimoDiaDelMes } from "./informesView.utils";
import { useInformeDiaADia } from "./informeDiaADia.hooks";
import { useInformeMatriz } from "./informeMatriz.hooks";
import { useInformeNomina } from "./informeNomina.hooks";

/**
 * Hoy en la zona horaria del backend (`America/Bogota`), como `YYYY-MM-DD`.
 *
 * `en-CA` es el locale que produce ese orden exacto sin tener que
 * reordenar nada a mano.
 */
const hoyBogota = (): string =>
  new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Bogota",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());

export const useInformesData = () => {
  const [hoy] = useState(hoyBogota);

  const [anio, setAnio] = useState(() => Number(hoy.slice(0, 4)));
  const [mes, setMes] = useState(() => Number(hoy.slice(5, 7)));
  const [dia, setDia] = useState(() => Number(hoy.slice(8, 10)));

  // Encendido por defecto, como el `CreateSwitch` del legacy.
  const [soloAprobados, setSoloAprobados] = useState(true);

  const [informeDia, setInformeDia] = useState<InformeDia | null>(null);
  const [informeArea, setInformeArea] = useState<InformeArea | null>(null);

  // Histórico completo: el gráfico NO sigue al selector de periodo (ver
  // `cargarSeries`), así que su estado es independiente de mes/año/día.
  const [serieChart, setSerieChart] = useState<InformeSeriesChart | null>(null);
  const [cargandoSerie, setCargandoSerie] = useState(true);
  const [errorSerie, setErrorSerie] = useState<string | null>(null);

  const [cargandoDia, setCargandoDia] = useState(true);
  const [cargandoArea, setCargandoArea] = useState(true);

  const [errorDia, setErrorDia] = useState<string | null>(null);
  const [errorArea, setErrorArea] = useState<string | null>(null);

  // Número de la última petición lanzada de cada bloque. Sirve para ignorar
  // las respuestas que llegan fuera de orden: si el usuario salta de enero a
  // diciembre, la respuesta de enero no debe pisar la de diciembre aunque
  // llegue después (se vería diciembre rotulado con los datos de enero).
  const peticionDia = useRef(0);
  const peticionArea = useRef(0);
  const peticionSerie = useRef(0);

  const maximoDia = useMemo(() => ultimoDiaDelMes(anio, mes), [anio, mes]);
  const fecha = useMemo(() => fechaISO(anio, mes, dia), [anio, mes, dia]);

  // Contador del ↻ global: los bloques que cargan sus propios datos (hoy
  // "Día a Día") se suscriben a él para repetir su consulta sin duplicar
  // callbacks en este hook.
  const [tick, setTick] = useState(0);

  // Bloque "Día a Día" (Paso 5): informe mensual paginado con filtros
  // server-side. Su estado es PROPIO porque tiene paginación y filtros que
  // no son los de la barra global.
  const diaADia = useInformeDiaADia(mes, anio, tick);

  // Bloque "Área y Carpeta" (Paso 6): matriz área × meses del año. Solo
  // depende del año (es la forma tabular del histórico del gráfico).
  const matriz = useInformeMatriz(anio, tick);

  // Bloque "Nómina · Liquidación · Cuenta de Cobro" (Paso 7): los dos
  // agregados de pago del mes en un solo hook, para que las dos tablas
  // muestren siempre el mismo periodo.
  const cierre = useInformeNomina(mes, anio, tick);

  // -------------------------------------------------------------------------
  // Cargas. Dependencias distintas a propósito: el bloque Día solo debe
  // volver a pedirse cuando cambia su FECHA, no cuando se mueve el Mes.
  // -------------------------------------------------------------------------
  const cargarDia = useCallback(async () => {
    const peticion = ++peticionDia.current;
    const esVigente = () => peticion === peticionDia.current;

    setCargandoDia(true);
    setErrorDia(null);
    try {
      const resultado = await transporteService.getInformeDia({ fecha });
      if (!esVigente()) return;
      setInformeDia(resultado);
    } catch (error) {
      if (!esVigente()) return;
      const apiError = error as ApiError;
      setErrorDia(
        apiError?.message ?? "No fue posible cargar el informe del día.",
      );
      logDevelopmentError("Error cargando informe de día:", error);
    } finally {
      // Solo la petición en curso puede apagar su propio indicador.
      if (esVigente()) setCargandoDia(false);
    }
  }, [fecha]);

  const cargarArea = useCallback(async () => {
    const peticion = ++peticionArea.current;
    const esVigente = () => peticion === peticionArea.current;

    setCargandoArea(true);
    setErrorArea(null);
    try {
      const resultado = await transporteService.getInformeArea({
        mes,
        anio,
        solo_aprobados: soloAprobados,
      });
      if (!esVigente()) return;
      setInformeArea(resultado);
    } catch (error) {
      if (!esVigente()) return;
      const apiError = error as ApiError;
      setErrorArea(
        apiError?.message ?? "No fue posible cargar el informe del mes.",
      );
      logDevelopmentError("Error cargando informe de mes:", error);
    } finally {
      if (esVigente()) setCargandoArea(false);
    }
  }, [mes, anio, soloAprobados]);

  /**
   * Series del gráfico "Pagos por Mes, por Área".
   *
   * Se pide SIN año, es decir histórico completo: es lo que el legacy
   * realmente dibujaba (`loadChartInfoMonthArea` se llamaba UNA sola vez
   * en `DOMContentLoaded` y sin parámetros, y el eje X era de tipo
   * `time`). Su rótulo decía "2024" fijo en el HTML y nunca se
   * actualizaba; aquí el rótulo dice "Histórico" para no mentir.
   *
   * Por eso no entra en las dependencias de periodo: cambiar de mes o año
   * no debe volver a pedirla.
   */
  const cargarSeries = useCallback(async () => {
    const peticion = ++peticionSerie.current;
    const esVigente = () => peticion === peticionSerie.current;

    setCargandoSerie(true);
    setErrorSerie(null);
    try {
      const resultado = await transporteService.getSeriesChart();
      if (!esVigente()) return;
      setSerieChart(resultado);
    } catch (error) {
      if (!esVigente()) return;
      const apiError = error as ApiError;
      setErrorSerie(
        apiError?.message ?? "No fue posible cargar el gráfico de áreas.",
      );
      logDevelopmentError("Error cargando series del gráfico:", error);
    } finally {
      if (esVigente()) setCargandoSerie(false);
    }
  }, []);

  useEffect(() => {
    void cargarDia();
  }, [cargarDia]);

  useEffect(() => {
    void cargarArea();
  }, [cargarArea]);

  useEffect(() => {
    void cargarSeries();
  }, [cargarSeries]);

  // -------------------------------------------------------------------------
  // Cambios de periodo. Al mover año o mes el día puede quedar fuera del
  // rango (p. ej. 31 de enero → febrero), así que se recorta.
  // -------------------------------------------------------------------------
  const cambiarAnio = useCallback(
    (nuevoAnio: number) => {
      setAnio(nuevoAnio);
      setDia((previo) => Math.min(previo, ultimoDiaDelMes(nuevoAnio, mes)));
    },
    [mes],
  );

  const cambiarMes = useCallback(
    (nuevoMes: number) => {
      setMes(nuevoMes);
      setDia((previo) => Math.min(previo, ultimoDiaDelMes(anio, nuevoMes)));
    },
    [anio],
  );

  /** Recoloca el día en el 1, como al elegir mes en el calendario legacy. */
  const irAlPrimero = useCallback(() => setDia(1), []);

  const irAHoy = useCallback(() => {
    setAnio(Number(hoy.slice(0, 4)));
    setMes(Number(hoy.slice(5, 7)));
    setDia(Number(hoy.slice(8, 10)));
  }, [hoy]);

  const recargar = useCallback(() => {
    void cargarDia();
    void cargarArea();
    void cargarSeries();
    setTick((previo) => previo + 1);
  }, [cargarDia, cargarArea, cargarSeries]);

  return {
    /** Periodo del bloque Día. */
    fecha,
    /** Periodo del bloque Mes. */
    mes,
    anio,
    dia,
    /** Último día válido del mes en curso (para limitar el selector). */
    maximoDia,
    hoy,
    cambiarAnio,
    cambiarMes,
    setDia,
    irAlPrimero,
    irAHoy,
    /** Interrupor "Aprobados": solo afecta al bloque Mes. */
    soloAprobados,
    setSoloAprobados,
    informeDia,
    informeArea,
    cargandoDia,
    cargandoArea,
    errorDia,
    errorArea,
    /** Histórico completo, independiente del periodo. */
    serieChart,
    cargandoSerie,
    errorSerie,
    /** Contador del ↻ global (bloques con carga propia). */
    tick,
    /** Bloque "Día a Día" (Paso 5): filas, filtros y paginación. */
    diaADia,
    /** Bloque "Área y Carpeta" (Paso 6): matriz área × meses del año. */
    matriz,
    /** Bloque "Nómina · Liquidación · Cuenta de Cobro" (Paso 7). */
    cierre,
    recargar,
  };
};
