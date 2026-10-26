// src/modules/transporte/planillas/planillasView.hooks.ts
//
// Hook de lógica para la consulta, generación e impresión de la
// Planilla Oficial de Salida F-104 (F5-6 / S5 / CR-11).

import { useCallback, useState } from "react";
import { toast } from "sonner";

import { classifyError } from "@/lib/errorHandler";
import { transporteService } from "@/services/transporte.service";
import type {
  AlcancePlanilla,
  PlanillaData,
  VehiculoPlanilla,
} from "@/types/transporte.types";

const hoy = (): string => {
  const d = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
};

export function usePlanillasState() {
  const [fecha, setFecha] = useState<string>(hoy());
  const [alcance, setAlcance] = useState<AlcancePlanilla>("TODAS");
  const [placa, setPlaca] = useState<string>("");

  const [planilla, setPlanilla] = useState<PlanillaData | null>(null);
  const [cargando, setCargando] = useState<boolean>(false);
  const [imprimiendo, setImprimiendo] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Consulta / Generación estructurada de la planilla
  const consultar = useCallback(async () => {
    const placaFinal = placa.trim().toUpperCase();
    if (alcance === "PLACA" && !placaFinal) {
      setError("Debe ingresar la placa del vehículo cuando el alcance es por placa.");
      return;
    }

    setCargando(true);
    setError(null);

    try {
      const data = await transporteService.generarPlanilla({
        fecha,
        alcance,
        placa: alcance === "PLACA" ? placaFinal : undefined,
      });

      setPlanilla(data);
    } catch (err) {
      const msg = classifyError(err).message;
      setError(msg);
    } finally {
      setCargando(false);
    }
  }, [fecha, alcance, placa]);

  // Genera el HTML oficial F-104 y abre diálogo de impresión
  const imprimirFormato = useCallback(
    async (alcanceCustom?: AlcancePlanilla, placaCustom?: string) => {
      const alcanceFinal = alcanceCustom ?? alcance;
      const placaFinal = (placaCustom ?? placa).trim().toUpperCase();

      if (alcanceFinal === "PLACA" && !placaFinal) {
        toast.error("Debe especificar la placa a imprimir.");
        return;
      }

      setImprimiendo(true);

      try {
        const html = await transporteService.getFormatoPlanilla({
          fecha,
          alcance: alcanceFinal,
          placa: alcanceFinal === "PLACA" ? placaFinal : undefined,
        });

        if (!html) {
          throw new Error("El servidor no retornó el formato HTML de la planilla.");
        }

        // Abre una pestaña limpia con el documento F-104 listo para impresión
        const ventana = window.open("", "_blank");
        if (!ventana) {
          toast.warning(
            "El navegador bloqueó la ventana emergente. Por favor permita popups para imprimir.",
          );
          return;
        }

        ventana.document.open();
        ventana.document.write(html);
        ventana.document.close();

        // Espera breve para renderizado de fuentes y estilos antes del print
        setTimeout(() => {
          try {
            ventana.focus();
            ventana.print();
          } catch {
            // Si el navegador no permite el trigger automático, el usuario tiene el botón de imprimir en el visor
          }
        }, 500);

        toast.success("Formato oficial F-104 preparado para impresión.");
      } catch (err) {
        const msg = classifyError(err).message;
        toast.error(`Error al generar formato físico: ${msg}`);
      } finally {
        setImprimiendo(false);
      }
    },
    [fecha, alcance, placa],
  );

  return {
    fecha,
    setFecha,
    alcance,
    setAlcance,
    placa,
    setPlaca,
    planilla,
    cargando,
    imprimiendo,
    error,
    consultar,
    imprimirFormato,
  };
}
