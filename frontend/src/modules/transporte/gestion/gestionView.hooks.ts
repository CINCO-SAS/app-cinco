// src/modules/transporte/gestion/gestionView.hooks.ts
//
// Hooks de lógica para el Backoffice de Salidas y Cierres por Área (F4 / B4 / B12).

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import { classifyError } from "@/lib/errorHandler";
import { transporteService } from "@/services/transporte.service";
import type { ValidacionSalida } from "@/types/transporte.types";
import { hoyISO } from "../operacion/salidas/salidasView.utils";

export function useValidacionesCierre() {
  const d = new Date();
  const [mes, setMes] = useState<number>(d.getMonth() + 1);
  const [anio, setAnio] = useState<number>(d.getFullYear());

  const [validaciones, setValidaciones] = useState<ValidacionSalida[]>([]);
  const [cargando, setCargando] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await transporteService.getValidaciones({
        mes,
        anio,
      });
      setValidaciones(data);
    } catch (err) {
      const msg = classifyError(err).message;
      setError(msg);
    } finally {
      setCargando(false);
    }
  }, [mes, anio]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  return {
    mes,
    setMes,
    anio,
    setAnio,
    validaciones,
    cargando,
    error,
    recargar: cargar,
  };
}

export function useExportarSalidas() {
  const [exportando, setExportando] = useState<boolean>(false);

  const exportar = useCallback(
    async (
      filtros: Record<string, string | number | boolean | undefined>,
      formato: "xlsx" | "csv" = "xlsx",
    ) => {
      setExportando(true);
      try {
        const blob = await transporteService.exportarSalidas({
          ...filtros,
          formato,
        });

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `gestion_salidas_${hoyISO()}.${formato}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);

        toast.success(`Exportación ${formato.toUpperCase()} generada con éxito.`);
      } catch (err) {
        const msg = classifyError(err).message;
        toast.error(`Error al exportar salidas: ${msg}`);
      } finally {
        setExportando(false);
      }
    },
    [],
  );

  return { exportar, exportando };
}
