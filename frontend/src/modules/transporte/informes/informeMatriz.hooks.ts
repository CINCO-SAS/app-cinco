// src/modules/transporte/informes/informeMatriz.hooks.ts
//
// Estado del bloque "Área y Carpeta" (Paso 6 del plan): la matriz
// área × meses del año (`GET /informes/areas-mes/`, F5-7).
//
// POR QUÉ SOLO DEPENDE DEL AÑO y no del periodo completo: es la forma
// TABULAR del histórico que ya dibuja el gráfico "Pagos por Mes, por Área"
// (F5-2), así que el mes y el interruptor "Solo aprobados" no aplican — el
// endpoint no los admite y el gráfico tampoco los usa. Mover el año sí
// mueve la matriz.
//
// El `tick` es el contador del ↻ global de la barra: al pulsarlo este bloque
// repite su consulta como los demás.

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { InformeAreasMes } from "@/types/transporte.types";

export const useInformeMatriz = (anio: number, tick: number) => {
  const [matriz, setMatriz] = useState<InformeAreasMes | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Identidad del guardia de respuestas fuera de orden: como `cargar` se
  // recrea al cambiar el año, el contador vive en un ref y no se reinicia.
  const peticionRef = useRef(0);

  const cargar = useCallback(async () => {
    const peticion = ++peticionRef.current;
    const esVigente = () => peticion === peticionRef.current;

    setIsLoading(true);
    setError(null);
    try {
      const resultado = await transporteService.getInformeAreasMes({ anio });
      if (!esVigente()) return;
      setMatriz(resultado);
    } catch (err) {
      if (!esVigente()) return;
      const apiError = err as ApiError;
      setError(apiError?.message ?? "No fue posible cargar la matriz del año.");
      logDevelopmentError("Error cargando la matriz área × meses:", err);
    } finally {
      if (esVigente()) setIsLoading(false);
    }
  }, [anio]);

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

  return { matriz, isLoading, error };
};
