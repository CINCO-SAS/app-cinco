// src/modules/transporte/informes/informeNomina.hooks.ts
//
// Estado del cierre del mes (Paso 7 del plan): nómina y liquidación, los dos
// agregados F5-7 que resumen el periodo para pagar.
//
// POR QUÉ UN SOLO HOOK PARA LOS DOS: son el mismo mes leído con dos
// agrupaciones —(carpeta, placa) y (placa)— con los MISMOS criterios
// (excluye REPORTADO y ELIMINADO, retefuente 1 %, pagador leído en
// servidor). Pedirlos juntos ahorra un viaje y garantiza que las dos
// tablas no puedan mostrar meses distintos si el usuario cambia de periodo
// a mitad de vuelta.
//
// NO ESTÁN PAGINADOS a propósito: el servidor devuelve el mes completo (una
// fila por carpeta+placa o por vehículo) y quien pagina es el cliente, que
// ya tiene todo el arreglo en memoria.

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { InformeLiquidacion, InformeNomina } from "@/types/transporte.types";

export const useInformeNomina = (mes: number, anio: number, tick: number) => {
  const [nomina, setNomina] = useState<InformeNomina | null>(null);
  const [liquidacion, setLiquidacion] = useState<InformeLiquidacion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const peticion = useRef(0);

  const cargar = useCallback(async () => {
    const peticionId = ++peticion.current;
    const esVigente = () => peticionId === peticion.current;

    setIsLoading(true);
    setError(null);
    try {
      const [datosNomina, datosLiquidacion] = await Promise.all([
        transporteService.getInformeNomina({ mes, anio }),
        transporteService.getInformeLiquidacion({ mes, anio }),
      ]);
      if (!esVigente()) return;
      setNomina(datosNomina);
      setLiquidacion(datosLiquidacion);
    } catch (err) {
      if (!esVigente()) return;
      const apiError = err as ApiError;
      setError(
        apiError?.message ?? "No fue posible cargar la nómina y la liquidación.",
      );
      logDevelopmentError("Error cargando nómina/liquidación del mes:", err);
    } finally {
      if (esVigente()) setIsLoading(false);
    }
  }, [mes, anio]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  // ↻ global: solo cuando el tick cambia (el primer montaje ya carga arriba).
  const tickPrevio = useRef(tick);
  useEffect(() => {
    if (tickPrevio.current === tick) return;
    tickPrevio.current = tick;
    void cargar();
  }, [tick, cargar]);

  return { nomina, liquidacion, isLoading, error };
};
