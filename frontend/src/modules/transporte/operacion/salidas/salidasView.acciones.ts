// src/modules/transporte/operacion/salidas/salidasView.acciones.ts
//
// Ítem L · acciones de fila de Salidas (B5/B6/B7/B12/B13/B15).
//
// El backend NO expone `PUT /salidas/{id}`: la salida no se "edita", se
// TRANSFORMA por una máquina de estados (D-A11):
//
//     REPORTADO ──aprobar──▶ APROBADO ──validar──▶ VALIDADO
//         │                      │
//         ├──rechazar──▶ RECHAZADO      (con motivo obligatorio)
//         └──eliminar──▶ ELIMINADO
//
// Todo eso son `POST` a acciones nombradas, no un CRUD genérico. Este hook
// centraliza cuál está en curso y sobre qué filas, para que la vista solo
// pinte botones y el botón sepa qué pedir.
//
// B15 (`puede_gestionar`): el SERVIDOR decide quién puede hacer qué. El front
// no re-implementa permisos, solo oculta lo que el backend rechazaría, y si
// aun así llega un 403 se muestra tal cual (classifyError).

import { useCallback, useMemo, useState } from "react";
import { toast } from "sonner";

import { classifyError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type { Salida } from "@/types/transporte.types";

/** Acciones que piden un solo paso de confirmación (sin formulario). */
export type AccionSimple =
  | "aprobar"
  | "eliminar"
  | "validar";

/** Diálogos modales abiertos. `null` = cerrado. */
export interface DialogoAcciones {
  /** Confirmación de aprobar/eliminar (con `Salida` para mostrar el resumen). */
  confirmar: { accion: AccionSimple; salida: Salida } | null;
  /** Rechazo: exige `motivo` (B13). */
  rechazar: Salida | null;
  /** Novedad ADICIONAL/DESCUENTO (B6/B7). */
  novedad: Salida | null;
  /** Historial de estados (solo lectura). */
  historial: Salida | null;
  /** Aprobación por lote (B12): `true` = abierto, `null` = cerrado. */
  lote: boolean | null;
}

const DIALOGOS_CERRADOS: DialogoAcciones = {
  confirmar: null,
  rechazar: null,
  novedad: null,
  historial: null,
  lote: null,
};

export const useSalidasAcciones = (onCambio: () => void) => {
  // Selección SOLO de la página visible. Se limpia al cambiar de página para
  // no arrastrar ids que ya no están en pantalla (el usuario creería aprobar
  // lo que ve y aprobaría lo que no).
  const [seleccion, setSeleccion] = useState<Set<number>>(new Set());
  const [dialogo, setDialogo] = useState<DialogoAcciones>(DIALOGOS_CERRADOS);
  const [enviando, setEnviando] = useState(false);
  // Último error de acción, para pintarlo DENTRO del diálogo abierto. El
  // `toast` solo sirve para confirmar éxito: un error dentro de un modal
  // debe quedarse a la vista mientras el usuario lo lee y reintenta.
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const alternarFila = useCallback((id: number) => {
    setSeleccion((prev) => {
      const siguiente = new Set(prev);
      if (siguiente.has(id)) siguiente.delete(id);
      else siguiente.add(id);
      return siguiente;
    });
  }, []);

  const alternarPagina = useCallback((ids: number[], marcar: boolean) => {
    setSeleccion((prev) => {
      const siguiente = new Set(prev);
      for (const id of ids) {
        if (marcar) siguiente.add(id);
        else siguiente.delete(id);
      }
      return siguiente;
    });
  }, []);

  const limpiarSeleccion = useCallback(() => setSeleccion(new Set()), []);

  const cerrarDialogo = useCallback(() => {
    setDialogo(DIALOGOS_CERRADOS);
    setErrorAccion(null);
  }, []);

  // Aperturas estables: si fueran funciones anónimas del `useMemo`, cada
  // clic en una casilla cambiaría la identidad de `acciones` y TanStack
  // reconstruiría las 13 columnas de la tabla.
  const abrirConfirmar = useCallback(
    (accion: AccionSimple, salida: Salida) => {
      setErrorAccion(null);
      setDialogo({ ...DIALOGOS_CERRADOS, confirmar: { accion, salida } });
    },
    [],
  );
  const abrirRechazar = useCallback((salida: Salida) => {
    setErrorAccion(null);
    setDialogo({ ...DIALOGOS_CERRADOS, rechazar: salida });
  }, []);
  const abrirNovedad = useCallback((salida: Salida) => {
    setErrorAccion(null);
    setDialogo({ ...DIALOGOS_CERRADOS, novedad: salida });
  }, []);
  const abrirHistorial = useCallback((salida: Salida) => {
    setErrorAccion(null);
    setDialogo({ ...DIALOGOS_CERRADOS, historial: salida });
  }, []);
  const abrirLote = useCallback(() => {
    setErrorAccion(null);
    setDialogo({ ...DIALOGOS_CERRADOS, lote: true });
  }, []);

  /**
   * Ejecuta la acción y, si algo salió mal, devuelve `true` (la UI conserva el
   * diálogo abierto mostrando el error) en vez de cerrarlo en silencio.
   */
  const ejecutar = useCallback(
    async (
      titulo: string,
      accion: () => Promise<unknown>,
      exito: string,
    ): Promise<boolean> => {
      setEnviando(true);
      setErrorAccion(null);
      try {
        await accion();
        toast.success(exito);
        onCambio();
        return false;
      } catch (error) {
        const detalle = classifyError(error);
        setErrorAccion(detalle.message);
        toast.error(`${titulo}: ${detalle.message}`);
        logDevelopmentError(`Error en acción de salidas (${titulo}):`, error);
        return true;
      } finally {
        setEnviando(false);
      }
    },
    [onCambio],
  );

  // --- Acciones simples (una fila) ---------------------------------------
  const confirmarAccionSimple = useCallback(async (): Promise<boolean> => {
    const pendiente = dialogo.confirmar;
    if (!pendiente) return false;
    const { accion, salida } = pendiente;
    const placa = salida.vehiculo_placa;

    if (accion === "aprobar") {
      return ejecutar(
        "Aprobar salida",
        () => transporteService.aprobarSalida(salida.id),
        `Salida de ${placa} aprobada.`,
      );
    }
    if (accion === "validar") {
      return ejecutar(
        "Validar salida",
        () => transporteService.validarSalida(salida.id),
        `Salida de ${placa} validada.`,
      );
    }
    return ejecutar(
      "Eliminar salida",
      () => transporteService.eliminarSalida(salida.id),
      `Salida de ${placa} eliminada.`,
    );
  }, [dialogo.confirmar, ejecutar]);

  const rechazar = useCallback(
    async (motivo: string): Promise<boolean> => {
      const salida = dialogo.rechazar;
      if (!salida) return false;
      return ejecutar(
        "Rechazar salida",
        () => transporteService.rechazarSalida(salida.id, motivo),
        `Salida de ${salida.vehiculo_placa} rechazada.`,
      );
    },
    [dialogo.rechazar, ejecutar],
  );

  const guardarNovedad = useCallback(
    async (payload: {
      tipo: string;
      valor: string;
      descripcion: string;
    }): Promise<boolean> => {
      const salida = dialogo.novedad;
      if (!salida) return false;
      return ejecutar(
        "Registrar novedad",
        () => transporteService.guardarNovedad(salida.id, payload),
        `Novedad registrada en la salida de ${salida.vehiculo_placa}.`,
      );
    },
    [dialogo.novedad, ejecutar],
  );

  /** B7: quitar la novedad (la regla es una por salida, así que no hay PUT). */
  const eliminarNovedad = useCallback(async (): Promise<boolean> => {
    const salida = dialogo.novedad;
    if (!salida) return false;
    return ejecutar(
      "Quitar novedad",
      () => transporteService.eliminarNovedad(salida.id),
      `Novedad quitada de la salida de ${salida.vehiculo_placa}.`,
    );
  }, [dialogo.novedad, ejecutar]);

  // --- Acción por lote (B12) ---------------------------------------------
  /**
   * `aprobar-lote` acepta N ids en UN solo `POST`. Si el backend rechaza
   * alguno (por estado o permiso) responde 400 y NO aprueba ninguno: es
   * transaccional. Por eso el diálogo muestra el recuento exacto.
   */
  const aprobarLote = useCallback(async (): Promise<boolean> => {
    const ids = [...seleccion];
    if (ids.length === 0) return false;
    const fallo = await ejecutar(
      "Aprobar en lote",
      () => transporteService.aprobarLote(ids),
      `${ids.length} salida(s) aprobada(s).`,
    );
    // Aprobadas, ya no tienen sentido seleccionadas.
    if (!fallo) setSeleccion(new Set());
    return fallo;
  }, [seleccion, ejecutar]);

  return useMemo(
    () => ({
      seleccion,
      seleccionCantidad: seleccion.size,
      dialogo,
      enviando,
      errorAccion,
      alternarFila,
      alternarPagina,
      limpiarSeleccion,
      cerrarDialogo,
      abrirConfirmar,
      abrirRechazar,
      abrirNovedad,
      abrirHistorial,
      abrirLote,
      confirmarAccionSimple,
      rechazar,
      guardarNovedad,
      eliminarNovedad,
      aprobarLote,
    }),
    [
      seleccion,
      dialogo,
      enviando,
      errorAccion,
      alternarFila,
      alternarPagina,
      limpiarSeleccion,
      cerrarDialogo,
      abrirConfirmar,
      abrirRechazar,
      abrirNovedad,
      abrirHistorial,
      abrirLote,
      confirmarAccionSimple,
      rechazar,
      guardarNovedad,
      eliminarNovedad,
      aprobarLote,
    ],
  );
};
