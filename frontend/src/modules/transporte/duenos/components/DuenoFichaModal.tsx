// src/modules/transporte/duenos/components/DuenoFichaModal.tsx
//
// Ficha Integral de Gestión de Dueño de Vehículos (F2 · 2026-10-26):
// 1. Gestión de flota vehicular asignada (1 dueño → N vehículos: asignar y desasignar).
// 2. Editor interactivo de cuentas bancarias (agregar, editar, dar de baja y guardar).

"use client";

import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";

import Alert from "@/components/ui/alert/Alert";
import Badge from "@/components/ui/badge/Badge";
import Button from "@/components/ui/button/Button";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";
import Select from "@/components/form/Select";
import { Modal } from "@/components/ui/modal";
import { classifyError } from "@/lib/errorHandler";
import { logDevelopmentError } from "@/lib/environment";
import { transporteService } from "@/services/transporte.service";
import type {
  DatosBancariosDueno,
  DuenoDetalle,
  VehiculoDelDueno,
} from "@/types/transporte.types";

interface DuenoFichaModalProps {
  isOpen: boolean;
  duenoId: number | null;
  tabInicial?: TabFicha;
  autoAgregarCuenta?: boolean;
  onClose: () => void;
  onActualizado: () => void;
}

export type TabFicha = "vehiculos" | "bancarios";

const TIPOS_CUENTA = [
  { value: "AHORROS", label: "Cuenta de Ahorros" },
  { value: "CORRIENTE", label: "Cuenta Corriente" },
];

const BANCOS_COMUNES = [
  "BANCOLOMBIA",
  "BANCO DE BOGOTA",
  "DAVIVIENDA",
  "BBVA",
  "BANCO DE OCCIDENTE",
  "BANCO AGRARIO",
  "BANCO CAJA SOCIAL",
  "SCOTIABANK COLPATRIA",
  "BANCO POPULAR",
  "ITAU",
  "NEQUI",
  "DAVIPLATA",
];

export const DuenoFichaModal = ({
  isOpen,
  duenoId,
  tabInicial = "vehiculos",
  autoAgregarCuenta = false,
  onClose,
  onActualizado,
}: DuenoFichaModalProps) => {
  const [tab, setTab] = useState<TabFicha>(tabInicial);
  const [dueno, setDueno] = useState<DuenoDetalle | null>(null);
  const [cargando, setCargando] = useState(false);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  // Estado para asignar vehículo
  const [nuevaPlaca, setNuevaPlaca] = useState("");
  const [asignandoVehiculo, setAsignandoVehiculo] = useState(false);
  const [errorAsignar, setErrorAsignar] = useState<string | null>(null);

  // Estado para edición de cuentas bancarias
  const [cuentas, setCuentas] = useState<Partial<DatosBancariosDueno>[]>([]);
  const [guardandoCuentas, setGuardandoCuentas] = useState(false);
  const [errorCuentas, setErrorCuentas] = useState<string | null>(null);

  const cargarFicha = useCallback(async (id: number, agregarCuentaInmediata: boolean) => {
    setCargando(true);
    setErrorServidor(null);
    try {
      const detalle = await transporteService.getDueno(id);
      setDueno(detalle);
      const cuentasBase: Partial<DatosBancariosDueno>[] = [
        ...(detalle.datos_bancarios || []),
      ];
      if (agregarCuentaInmediata) {
        cuentasBase.push({
          cedula_titular: detalle.cedula,
          nombre_titular: detalle.nombre,
          banco: "BANCOLOMBIA",
          tipo_cuenta: "AHORROS",
          numero_cuenta: "",
          activo: true,
        });
      }
      setCuentas(cuentasBase);
    } catch (err) {
      const clasificado = classifyError(err);
      setErrorServidor(clasificado.message);
      logDevelopmentError("Error cargando ficha del dueño:", err);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen && duenoId) {
      setTab(tabInicial);
      setNuevaPlaca("");
      setErrorAsignar(null);
      setErrorCuentas(null);
      void cargarFicha(duenoId, autoAgregarCuenta);
    } else {
      setDueno(null);
      setCuentas([]);
    }
  }, [isOpen, duenoId, tabInicial, autoAgregarCuenta, cargarFicha]);

  // Asignar vehículo existente por placa
  const asignarVehiculo = useCallback(async () => {
    if (!dueno || !nuevaPlaca.trim()) return;

    setAsignandoVehiculo(true);
    setErrorAsignar(null);
    try {
      const placaLimpia = nuevaPlaca.trim().toUpperCase();
      await transporteService.asignarVehiculoADueno(dueno.id, { placa: placaLimpia });
      toast.success(`Vehículo ${placaLimpia} asignado a ${dueno.nombre}.`);
      setNuevaPlaca("");
      await cargarFicha(dueno.id, false);
      onActualizado();
    } catch (err) {
      const detalle = classifyError(err);
      setErrorAsignar(detalle.message);
      logDevelopmentError("Error asignando vehículo:", err);
    } finally {
      setAsignandoVehiculo(false);
    }
  }, [dueno, nuevaPlaca, cargarFicha, onActualizado]);

  // Desasignar vehículo del dueño (sin borrar el vehículo)
  const desasignarVehiculo = useCallback(
    async (vehiculo: VehiculoDelDueno) => {
      if (!dueno) return;
      const confirmar = window.confirm(
        `¿Deseas desasignar el vehículo ${vehiculo.placa} de ${dueno.nombre}? El vehículo no se eliminará, solo quedará disponible.`,
      );
      if (!confirmar) return;

      try {
        await transporteService.quitarVehiculoDeDueno(dueno.id, vehiculo.id);
        toast.success(`Vehículo ${vehiculo.placa} desasignado.`);
        await cargarFicha(dueno.id, false);
        onActualizado();
      } catch (err) {
        const detalle = classifyError(err);
        toast.error(detalle.message);
        logDevelopmentError("Error desasignando vehículo:", err);
      }
    },
    [dueno, cargarFicha, onActualizado],
  );

  // Agregar fila de cuenta bancaria
  const agregarCuenta = useCallback(() => {
    if (!dueno) return;
    setCuentas((prev) => [
      ...prev,
      {
        cedula_titular: dueno.cedula,
        nombre_titular: dueno.nombre,
        banco: "BANCOLOMBIA",
        tipo_cuenta: "AHORROS",
        numero_cuenta: "",
        activo: true,
      },
    ]);
  }, [dueno]);

  // Actualizar campo de cuenta en memoria
  const actualizarCampoCuenta = useCallback(
    (index: number, campo: keyof DatosBancariosDueno, valor: unknown) => {
      setCuentas((prev) => {
        const copia = [...prev];
        copia[index] = { ...copia[index], [campo]: valor };
        return copia;
      });
    },
    [],
  );

  // Eliminar cuenta bancaria: la quita de la pantalla Y la da de baja en el
  // servidor (el backend conserva el registro con `activo=False` por
  // trazabilidad). Antes solo se quitaba del estado local y se perdía al
  // recargar, porque la baja solo se persistía al pulsar "Guardar".
  const eliminarCuenta = useCallback(
    async (index: number) => {
      if (!dueno) return;

      const cuenta = cuentas[index];
      const etiqueta = [cuenta?.banco, cuenta?.numero_cuenta]
        .filter(Boolean)
        .join(" ");
      const confirmar = window.confirm(
        `¿Deseas eliminar la cuenta ${etiqueta || `#${index + 1}`}? Dejará de estar activa para giros.`,
      );
      if (!confirmar) return;

      const restantes = cuentas.filter((_, i) => i !== index);
      setCuentas(restantes);

      // Si alguna cuenta restante quedó incompleta no se puede enviar la
      // lista: el backend exige que todas traigan sus datos. Se avisa y
      // queda pendiente el "Guardar" del pie de la ficha.
      const incompleta = restantes.findIndex(
        (c) => !c.numero_cuenta?.trim() || !c.banco?.trim(),
      );
      if (incompleta !== -1) {
        setErrorCuentas(
          `La cuenta #${incompleta + 1} quedó incompleta. Completa sus datos o elimínala para poder confirmar el guardado.`,
        );
        return;
      }

      setGuardandoCuentas(true);
      try {
        const guardadas = await transporteService.guardarBancariosDueno(
          dueno.id,
          restantes,
        );
        setCuentas(guardadas.filter((c) => c.activo !== false));
        setErrorCuentas(null);
        toast.success("Cuenta bancaria eliminada.");
        onActualizado();
      } catch (err) {
        const detalle = classifyError(err);
        setErrorCuentas(detalle.message);
        logDevelopmentError("Error eliminando cuenta bancaria:", err);
      } finally {
        setGuardandoCuentas(false);
      }
    },
    [dueno, cuentas, onActualizado],
  );

  // Guardar cuentas bancarias en el backend
  const guardarBancarios = useCallback(async () => {
    if (!dueno) return;

    for (let i = 0; i < cuentas.length; i++) {
      const c = cuentas[i];
      if (!c.numero_cuenta?.trim()) {
        setErrorCuentas(`La cuenta #${i + 1} no tiene número de cuenta.`);
        return;
      }
      if (!c.banco?.trim()) {
        setErrorCuentas(`La cuenta #${i + 1} no tiene banco seleccionado.`);
        return;
      }
    }

    setGuardandoCuentas(true);
    setErrorCuentas(null);
    try {
      const guardadas = await transporteService.guardarBancariosDueno(dueno.id, cuentas);
      setCuentas(guardadas);
      toast.success("Cuentas bancarias del propietario guardadas con éxito.");
      await cargarFicha(dueno.id, false);
      onActualizado();
    } catch (err) {
      const detalle = classifyError(err);
      setErrorCuentas(detalle.message);
      logDevelopmentError("Error guardando cuentas bancarias:", err);
    } finally {
      setGuardandoCuentas(false);
    }
  }, [dueno, cuentas, cargarFicha, onActualizado]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      className="max-w-4xl"
      title="dueno-ficha-titulo"
    >
      <div className="px-6 pt-6 pb-3 pr-16 border-b border-gray-200 dark:border-gray-800">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <h2
              id="dueno-ficha-titulo"
              className="text-lg font-bold text-gray-800 dark:text-white/90"
            >
              Ficha del Propietario: {dueno?.nombre || "Cargando..."}
            </h2>
            <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-gray-400">
              <span>Cédula/NIT: <strong className="text-gray-700 dark:text-gray-200">{dueno?.cedula}</strong></span>
              {dueno?.celular && (
                <span>Teléfono: <strong className="text-gray-700 dark:text-gray-200">{dueno.celular}</strong></span>
              )}
              {dueno && (
                <Badge color={dueno.activo ? "success" : "light"} size="sm">
                  {dueno.activo ? "Activo" : "Inactivo"}
                </Badge>
              )}
            </div>
          </div>

          <div className="flex rounded-lg bg-gray-100 p-1 dark:bg-gray-800 self-start">
            <button
              type="button"
              onClick={() => setTab("vehiculos")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-medium transition ${
                tab === "vehiculos"
                  ? "bg-white text-gray-900 shadow-sm font-semibold dark:bg-gray-700 dark:text-white"
                  : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
              }`}
            >
              Vehículos ({dueno?.vehiculos?.length || 0})
            </button>
            <button
              type="button"
              onClick={() => setTab("bancarios")}
              className={`rounded-md px-3.5 py-1.5 text-xs font-medium transition ${
                tab === "bancarios"
                  ? "bg-white text-gray-900 shadow-sm font-semibold dark:bg-gray-700 dark:text-white"
                  : "text-gray-600 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white"
              }`}
            >
              Cuentas Bancarias ({cuentas.length})
            </button>
          </div>
        </div>
      </div>

      <div className="max-h-[72vh] overflow-y-auto px-6 py-5">
        {cargando ? (
          <div className="p-8 text-center text-sm text-gray-500">
            Cargando información del propietario...
          </div>
        ) : errorServidor ? (
          <Alert variant="error" title="Error al cargar" message={errorServidor} />
        ) : tab === "vehiculos" ? (
          /* TAB 1: VEHÍCULOS ASIGNADOS */
          <div className="space-y-5">
            {/* Formulario de asignación de vehículo por placa */}
            <div className="rounded-xl border border-gray-200 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-gray-900/50">
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 mb-2">
                Asignar Vehículo al Propietario
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">
                Un propietario puede tener múltiples vehículos asignados (1 Dueño → N Vehículos). Ingresa la placa del vehículo existente para vincularlo.
              </p>

              {errorAsignar && (
                <div className="mb-3">
                  <Alert variant="error" title="No se pudo asignar" message={errorAsignar} />
                </div>
              )}

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <div className="w-full sm:w-64">
                  <Input
                    placeholder="Ej. ABC123"
                    className="uppercase"
                    value={nuevaPlaca}
                    onChange={(e) => {
                      setNuevaPlaca(e.target.value);
                      setErrorAsignar(null);
                    }}
                    disabled={asignandoVehiculo}
                  />
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => void asignarVehiculo()}
                  disabled={asignandoVehiculo || !nuevaPlaca.trim()}
                >
                  {asignandoVehiculo ? "Asignando..." : "+ Asignar a este Dueño"}
                </Button>
              </div>
            </div>

            {/* Listado de vehículos actuales */}
            <div>
              <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300 mb-3">
                Vehículos Asignados ({dueno?.vehiculos?.length || 0})
              </h3>

              {!dueno?.vehiculos || dueno.vehiculos.length === 0 ? (
                <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 dark:border-gray-700">
                  Este propietario aún no tiene vehículos asignados. Utiliza el formulario superior para agregar uno.
                </div>
              ) : (
                <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
                  <table className="w-full text-left text-sm text-gray-600 dark:text-gray-300">
                    <thead className="bg-gray-50 text-xs font-semibold uppercase text-gray-700 dark:bg-gray-800 dark:text-gray-300">
                      <tr>
                        <th className="px-4 py-3">PLACA</th>
                        <th className="px-4 py-3">VEHÍCULO</th>
                        <th className="px-4 py-3">TIPO</th>
                        <th className="px-4 py-3">MODELO</th>
                        <th className="px-4 py-3">ESTADO</th>
                        <th className="px-4 py-3 text-right">ACCIONES</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                      {dueno.vehiculos.map((veh) => (
                        <tr key={veh.id} className="hover:bg-gray-50/50 dark:hover:bg-white/5">
                          <td className="px-4 py-3 font-bold text-gray-900 dark:text-white">
                            {veh.placa}
                          </td>
                          <td className="px-4 py-3">
                            {veh.marca} {veh.referencia ?? ""}
                          </td>
                          <td className="px-4 py-3 text-xs text-gray-500">
                            {veh.tipo_vehiculo}
                          </td>
                          <td className="px-4 py-3 text-xs">
                            {veh.modelo_anio}
                          </td>
                          <td className="px-4 py-3">
                            <Badge color={veh.activo ? "success" : "light"} size="sm">
                              {veh.activo ? "Activo" : "Inactivo"}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              type="button"
                              onClick={() => void desasignarVehiculo(veh)}
                              className="text-xs font-medium text-error-600 hover:text-error-700 dark:text-error-400 hover:underline"
                            >
                              Desasignar
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* TAB 2: CUENTAS BANCARIAS DEL PROPIETARIO */
          <div className="space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-gray-700 dark:text-gray-300">
                  Cuentas para Giro y Liquidación
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  Los datos bancarios pertenecen al dueño. Al liquidar cualquiera de sus vehículos, el sistema utiliza estas cuentas registradas.
                </p>
              </div>

              <Button
                variant="outline"
                size="sm"
                onClick={agregarCuenta}
              >
                + Agregar Cuenta Bancaria
              </Button>
            </div>

            {errorCuentas && (
              <Alert variant="error" title="Error en cuentas" message={errorCuentas} />
            )}

            {cuentas.length === 0 ? (
              <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500 dark:border-gray-700">
                No hay cuentas bancarias registradas para este dueño. Haz clic en &quot;+ Agregar Cuenta Bancaria&quot; para ingresar los datos de giro.
              </div>
            ) : (
              <div className="space-y-3">
                {cuentas.map((cuenta, idx) => (
                  <div
                    key={cuenta.id ?? `cuenta-${idx}`}
                    className="rounded-xl border border-gray-200 bg-white p-4 shadow-theme-xs dark:border-gray-800 dark:bg-gray-850"
                  >
                    <div className="flex items-center justify-between mb-3 border-b border-gray-100 pb-2 dark:border-gray-800">
                      <span className="text-xs font-bold uppercase text-brand-600 dark:text-brand-400">
                        Cuenta Bancaria #{idx + 1}
                      </span>
                      <button
                        type="button"
                        onClick={() => void eliminarCuenta(idx)}
                        disabled={guardandoCuentas}
                        className="text-xs text-error-500 hover:text-error-700 disabled:opacity-50 dark:text-error-400"
                      >
                        Eliminar
                      </button>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <Label htmlFor={`banco-${idx}`}>Banco</Label>
                        <Select
                          options={BANCOS_COMUNES.map((b) => ({ value: b, label: b }))}
                          defaultValue={cuenta.banco ?? "BANCOLOMBIA"}
                          onChange={(val) => actualizarCampoCuenta(idx, "banco", val)}
                        />
                      </div>

                      <div>
                        <Label htmlFor={`tipo-cuenta-${idx}`}>Tipo de Cuenta</Label>
                        <Select
                          options={TIPOS_CUENTA}
                          defaultValue={cuenta.tipo_cuenta ?? "AHORROS"}
                          onChange={(val) => actualizarCampoCuenta(idx, "tipo_cuenta", val)}
                        />
                      </div>

                      <div>
                        <Label htmlFor={`num-cuenta-${idx}`}>Número de Cuenta</Label>
                        <Input
                          id={`num-cuenta-${idx}`}
                          placeholder="Número de cuenta bancaria"
                          value={cuenta.numero_cuenta ?? ""}
                          onChange={(e) =>
                            actualizarCampoCuenta(idx, "numero_cuenta", e.target.value)
                          }
                        />
                      </div>

                      <div>
                        <Label htmlFor={`titular-${idx}`}>Nombre Titular</Label>
                        <Input
                          id={`titular-${idx}`}
                          value={cuenta.nombre_titular ?? ""}
                          onChange={(e) =>
                            actualizarCampoCuenta(idx, "nombre_titular", e.target.value)
                          }
                        />
                      </div>

                      <div>
                        <Label htmlFor={`cedula-titular-${idx}`}>Cédula / NIT Titular</Label>
                        <Input
                          id={`cedula-titular-${idx}`}
                          value={cuenta.cedula_titular ?? ""}
                          onChange={(e) =>
                            actualizarCampoCuenta(idx, "cedula_titular", e.target.value)
                          }
                        />
                      </div>

                      <div className="flex items-center pt-6">
                        <label className="flex items-center gap-2 cursor-pointer text-xs text-gray-700 dark:text-gray-300">
                          <input
                            type="checkbox"
                            checked={cuenta.activo !== false}
                            onChange={(e) =>
                              actualizarCampoCuenta(idx, "activo", e.target.checked)
                            }
                            className="rounded border-gray-300 text-brand-600 focus:ring-brand-500"
                          />
                          Cuenta activa para giros
                        </label>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-gray-200 px-6 py-4 dark:border-gray-800">
        <Button
          type="button"
          variant="outline"
          onClick={onClose}
        >
          Cerrar
        </Button>

        {tab === "bancarios" && (
          <Button
            type="button"
            variant="primary"
            onClick={() => void guardarBancarios()}
            disabled={guardandoCuentas}
          >
            {guardandoCuentas ? "Guardando Cuentas..." : "Guardar Cuentas Bancarias"}
          </Button>
        )}
      </div>
    </Modal>
  );
};
