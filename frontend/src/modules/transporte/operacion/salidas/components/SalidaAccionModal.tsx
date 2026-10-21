// src/modules/transporte/operacion/salidas/components/SalidaAccionModal.tsx
//
// Ítem L · confirmación de acciones de fila (B5/B13).
//
// Dos diálogos con la MISMA carcasa:
//   · `SalidaConfirmarModal` — aprobar / eliminar / validar (un clic).
//   · `SalidaRechazarModal`  — rechazar, que EXIGE motivo (B13).
//
// El motivo no es cosmético: el backend lo guarda en el historial y es lo
// que el conductor o el jefe ven después. Sin motivo no hay rechazo.

"use client";

import { useCallback, useEffect, useState } from "react";

import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import { Modal } from "@/components/ui/modal";
import {
  BadgeEstadoSalida,
  BotonDestructivo,
  formatearFechaCorta,
} from "../salidasView.utils";
import type { Salida } from "@/types/transporte.types";

// ---------------------------------------------------------------------------
// Carcasa común: resumen de la salida + error + botones.
// ---------------------------------------------------------------------------

interface CarcasaProps {
  /** Texto visible del encabezado; también es el `aria-labelledby`. */
  titulo: string;
  salida: Salida | null;
  errorServidor: string | null;
  enviando: boolean;
  onClose: () => void;
  /** Bloque de campos extra bajo el resumen (el motivo, por ejemplo). */
  cuerpo?: React.ReactNode;
  /** Pie derecho: el botón de confirmar, con su propia etiqueta/color. */
  children: React.ReactNode;
}

const CarcasaAccion = ({
  titulo,
  salida,
  errorServidor,
  enviando,
  onClose,
  cuerpo,
  children,
}: CarcasaProps) => {
  const idTitulo = "salida-accion-titulo";
  return (
    <Modal
      isOpen={salida !== null}
      onClose={() => {
        if (!enviando) onClose();
      }}
      className="max-w-md"
      title={idTitulo}
    >
      <div className="px-5 pt-5 pb-1 pr-16">
        <h2
          id={idTitulo}
          className="text-base font-semibold text-gray-800 dark:text-white/90"
        >
          {titulo}
        </h2>
      </div>

      <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
        {errorServidor && (
          <Alert variant="error" title="No se pudo completar" message={errorServidor} />
        )}

        {salida && (
          <div className="space-y-1.5 rounded-lg border border-gray-200 bg-gray-50 p-3 dark:border-gray-800 dark:bg-white/[0.03]">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-gray-800 dark:text-white/90">
                {salida.vehiculo_placa}
              </span>
              <BadgeEstadoSalida estado={salida.estado} />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Fecha {formatearFechaCorta(salida.fecha_salida)} ·{" "}
              {salida.conductor_detalle?.nombre ?? "Sin conductor"}
            </p>
          </div>
        )}

        {cuerpo}
      </div>

      <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
        {children}
      </div>
    </Modal>
  );
};

// ---------------------------------------------------------------------------
// Aprobar / eliminar / validar
// ---------------------------------------------------------------------------

export interface SalidaConfirmarModalProps {
  /** `null` → cerrado. */
  accion: "aprobar" | "eliminar" | "validar" | null;
  salida: Salida | null;
  enviando: boolean;
  errorServidor: string | null;
  onClose: () => void;
  onConfirmar: () => void;
}

const TEXTO: Record<
  "aprobar" | "eliminar" | "validar",
  { titulo: string; mensaje: string; boton: string }
> = {
  aprobar: {
    titulo: "Aprobar salida",
    mensaje:
      "Al aprobar, la salida pasa a estado Aprobado y queda lista para ser validada por el área de transporte.",
    boton: "Aprobar",
  },
  validar: {
    titulo: "Validar salida",
    mensaje:
      "La validación es el cierre definitivo: la salida queda en estado Validado y alimenta la liquidación del conductor.",
    boton: "Validar",
  },
  eliminar: {
    titulo: "Eliminar salida",
    mensaje:
      "La salida quedará en estado Eliminado. No se borra el registro: se conserva con su historial para trazabilidad.",
    boton: "Eliminar",
  },
};

export const SalidaConfirmarModal = ({
  accion,
  salida,
  enviando,
  errorServidor,
  onClose,
  onConfirmar,
}: SalidaConfirmarModalProps) => {
  const configuracion = accion ? TEXTO[accion] : null;
  return (
    <CarcasaAccion
      titulo={configuracion?.titulo ?? "Acción"}
      salida={salida}
      errorServidor={errorServidor}
      enviando={enviando}
      onClose={onClose}
    >
      <Button type="button" variant="outline" onClick={onClose} disabled={enviando}>
        Cancelar
      </Button>
      {accion === "eliminar" ? (
        <BotonDestructivo onClick={onConfirmar} disabled={enviando}>
          {enviando ? "Procesando..." : "Eliminar"}
        </BotonDestructivo>
      ) : (
        <Button
          type="button"
          variant="primary"
          onClick={onConfirmar}
          disabled={enviando}
        >
          {enviando ? "Procesando..." : (configuracion?.boton ?? "Confirmar")}
        </Button>
      )}
    </CarcasaAccion>
  );
};

// ---------------------------------------------------------------------------
// Rechazar con motivo (B13)
// ---------------------------------------------------------------------------

export interface SalidaRechazarModalProps {
  /** `null` → cerrado. */
  salida: Salida | null;
  enviando: boolean;
  errorServidor: string | null;
  onClose: () => void;
  /** Devuelve `true` si la petición falló (el diálogo se queda abierto). */
  onRechazar: (motivo: string) => Promise<boolean>;
}

export const SalidaRechazarModal = ({
  salida,
  enviando,
  errorServidor,
  onClose,
  onRechazar,
}: SalidaRechazarModalProps) => {
  const abierto = salida !== null;
  const [motivo, setMotivo] = useState("");
  const [errorMotivo, setErrorMotivo] = useState<string | null>(null);

  useEffect(() => {
    if (abierto) {
      setMotivo("");
      setErrorMotivo(null);
    }
  }, [abierto, salida?.id]);

  const confirmar = useCallback(async () => {
    const limpio = motivo.trim();
    if (!limpio) {
      setErrorMotivo("El motivo del rechazo es obligatorio.");
      return;
    }
    // Si falla, el diálogo se queda abierto con el error del servidor.
    const fallo = await onRechazar(limpio);
    if (!fallo) setMotivo("");
  }, [motivo, onRechazar]);

  return (
    <CarcasaAccion
      titulo="Rechazar salida"
      salida={salida}
      errorServidor={errorServidor}
      enviando={enviando}
      onClose={onClose}
      cuerpo={
        <div>
          <Label htmlFor="salida-rechazo-motivo">
            Motivo del rechazo <span className="text-error-500">*</span>
          </Label>
          <Input
            id="salida-rechazo-motivo"
            type="text"
            value={motivo}
            onChange={(e) => {
              setMotivo(e.target.value);
              setErrorMotivo(null);
            }}
            disabled={enviando}
            error={Boolean(errorMotivo)}
            hint={errorMotivo ?? undefined}
            placeholder="Ej. El conductor no reportó el kilometraje de salida"
          />
        </div>
      }
    >
      <Button type="button" variant="outline" onClick={onClose} disabled={enviando}>
        Cancelar
      </Button>
      <BotonDestructivo onClick={() => void confirmar()} disabled={enviando}>
        {enviando ? "Rechazando..." : "Rechazar"}
      </BotonDestructivo>
    </CarcasaAccion>
  );
};

// ---------------------------------------------------------------------------
// Aprobar en lote (B12)
// ---------------------------------------------------------------------------

export interface SalidaAprobarLoteModalProps {
  /** Cantidad de filas seleccionadas; `null`/0 = cerrado. */
  cantidad: number | null;
  enviando: boolean;
  errorServidor: string | null;
  onClose: () => void;
  /** Devuelve `true` si la petición falló (el diálogo se queda abierto). */
  onConfirmar: () => Promise<boolean>;
}

/**
 * `POST /salidas/aprobar-lote/` corre en UNA transacción con `select_for_update`:
 * si una sola fila no está en REPORTADO o el usuario no la puede gestionar,
 * responde 400 y NO aprueba NINGUNA. Por eso el diálogo lo avisa de forma
 * explícita — el usuario debe revisar la selección antes de confirmar.
 */
export const SalidaAprobarLoteModal = ({
  cantidad,
  enviando,
  errorServidor,
  onClose,
  onConfirmar,
}: SalidaAprobarLoteModalProps) => {
  const abierto = Boolean(cantidad && cantidad > 0);
  return (
    <Modal
      isOpen={abierto}
      onClose={() => {
        if (!enviando) onClose();
      }}
      className="max-w-md"
      title="salida-lote-titulo"
    >
      <div className="px-5 pt-5 pb-1 pr-16">
        <h2
          id="salida-lote-titulo"
          className="text-base font-semibold text-gray-800 dark:text-white/90"
        >
          Aprobar en lote
        </h2>
      </div>

      <div className="max-h-[70vh] space-y-4 overflow-y-auto px-5 pt-4 pb-2">
        {errorServidor && (
          <Alert variant="error" title="No se pudo aprobar" message={errorServidor} />
        )}
        <p className="text-sm text-gray-600 dark:text-gray-300">
          Vas a aprobar{" "}
          <span className="font-semibold text-gray-800 dark:text-white/90">
            {cantidad ?? 0} salida(s)
          </span>{" "}
          seleccionadas.
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          La operación es única: si alguna de las filas no está en estado
          Reportado o no te corresponde gestionar, no se aprueba ninguna y se
          mostrará el motivo.
        </p>
      </div>

      <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-5 py-4 dark:border-gray-800">
        <Button type="button" variant="outline" onClick={onClose} disabled={enviando}>
          Cancelar
        </Button>
        <Button
          type="button"
          variant="primary"
          onClick={() => void onConfirmar()}
          disabled={enviando}
        >
          {enviando ? "Aprobando..." : "Aprobar seleccionadas"}
        </Button>
      </div>
    </Modal>
  );
};
