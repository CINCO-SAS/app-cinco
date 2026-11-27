"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  AlertCircle,
  Calendar,
  Clock,
  FileSpreadsheet,
  Hash,
  Info,
  RefreshCw,
  Search,
  User,
  Wrench,
  X,
} from "lucide-react";
import { toast } from "sonner";
import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import { incidenteService } from "./services/incidente.service";
import { IncidenteBusquedaResponse, IncidenteFuente } from "./types";

const INC_REGEX = /^[A-Z0-9_-]+$/;

function formatFechaCreacion(isoString: string | null): string {
  if (!isoString) return "Sin fecha registrada";
  const parsed = new Date(isoString);
  if (Number.isNaN(parsed.getTime())) return isoString;
  return new Intl.DateTimeFormat("es-CO", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(parsed);
}

function formatAntiguedad(minutos: number, refreshed: boolean): string {
  if (refreshed || minutos <= 0) return "Consultado hace menos de 1 min";
  if (minutos === 1) return "Consultado hace 1 min";
  if (minutos < 60) return `Consultado hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  return horas === 1 ? "Consultado hace 1 hora" : `Consultado hace ${horas} horas`;
}

function getEstadoBadgeClass(estado: string): string {
  const upper = (estado || "").trim().toUpperCase();
  if (upper.includes("CERRAD") || upper.includes("RESUELT") || upper.includes("COMPLET")) {
    return "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-800";
  }
  if (upper.includes("PROGRAM") || upper.includes("PROCES") || upper.includes("ASIGN")) {
    return "bg-brand-50 text-brand-700 border-brand-200 dark:bg-brand-950/40 dark:text-brand-300 dark:border-brand-800";
  }
  if (upper.includes("CANCEL") || upper.includes("RECHAZ") || upper.includes("VENCID")) {
    return "bg-red-50 text-red-700 border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800";
  }
  return "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800";
}

export const IncidentesView: React.FC = () => {
  const [fuentes, setFuentes] = useState<IncidenteFuente[]>([]);
  const [fuenteSeleccionada, setFuenteSeleccionada] = useState<string>("");
  const [isLoadingFuentes, setIsLoadingFuentes] = useState(true);

  const [incInput, setIncInput] = useState("");
  const [ultimoIncBuscado, setUltimoIncBuscado] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const [resultado, setResultado] = useState<IncidenteBusquedaResponse | null>(null);
  const [notFoundInfo, setNotFoundInfo] = useState<IncidenteBusquedaResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const cargarFuentes = async () => {
      setIsLoadingFuentes(true);
      try {
        const items = await incidenteService.listarFuentes();
        if (!active) return;
        setFuentes(items);
        const primeraHabilitada = items.find((f) => f.habilitado);
        if (primeraHabilitada) {
          setFuenteSeleccionada(primeraHabilitada.key);
        } else if (items[0]) {
          setFuenteSeleccionada(items[0].key);
        }
      } catch {
        if (active) {
          toast.error("No se pudo cargar el listado de archivos de SharePoint.");
        }
      } finally {
        if (active) setIsLoadingFuentes(false);
      }
    };
    cargarFuentes();
    return () => {
      active = false;
    };
  }, []);

  const fuenteActual = useMemo(
    () => fuentes.find((f) => f.key === fuenteSeleccionada),
    [fuentes, fuenteSeleccionada],
  );

  const ejecutarBusqueda = async (incRaw: string, refresh = false) => {
    const incClean = incRaw.trim().toUpperCase();
    if (!incClean) {
      toast.warning("Ingresa un código de incidente (INC) para consultar.");
      return;
    }
    if (incClean.length > 40 || !INC_REGEX.test(incClean)) {
      toast.error("El código INC solo puede contener letras, números, guiones (-) o guiones bajos (_).");
      return;
    }
    if (fuenteActual && !fuenteActual.habilitado) {
      toast.warning(`El archivo "${fuenteActual.label}" aún no está habilitado.`);
      return;
    }

    setIncInput(incClean);
    setUltimoIncBuscado(incClean);
    setErrorMsg(null);
    setNotFoundInfo(null);
    if (refresh) {
      setIsRefreshing(true);
    } else {
      setIsSearching(true);
    }

    try {
      const data = await incidenteService.buscarPorInc({
        inc: incClean,
        fuente: fuenteSeleccionada || undefined,
        refresh,
      });
      setResultado(data);
      if (refresh) {
        if (data.cooldown_active) {
          toast.info(
            `Los datos se actualizaron hace poco. Espera unos segundos antes de volver a refrescar.`,
          );
        } else {
          toast.success("Datos actualizados desde SharePoint.");
        }
      }
    } catch (err: any) {
      const statusCode = err?.response?.status;
      const respData = err?.response?.data as IncidenteBusquedaResponse | undefined;

      if (statusCode === 404 && respData) {
        setResultado(null);
        setNotFoundInfo(respData);
        if (refresh && respData.cooldown_active) {
          toast.info("Los datos se actualizaron hace poco; el INC sigue sin aparecer.");
        }
      } else {
        setResultado(null);
        const detail =
          respData?.detail ||
          err?.message ||
          "No fue posible consultar el incidente en SharePoint.";
        setErrorMsg(detail);
        toast.error(detail);
      }
    } finally {
      setIsSearching(false);
      setIsRefreshing(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    ejecutarBusqueda(incInput, false);
  };

  const handleLimpiar = () => {
    setIncInput("");
    setUltimoIncBuscado("");
    setResultado(null);
    setNotFoundInfo(null);
    setErrorMsg(null);
  };

  const handleCambioFuente = (nuevaFuente: string) => {
    setFuenteSeleccionada(nuevaFuente);
    setResultado(null);
    setNotFoundInfo(null);
    setErrorMsg(null);
  };

  const principal = resultado?.principal;
  const metaActual = resultado || notFoundInfo;

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle={["Operaciones", "Incidentes"]} />

      {/* Buscador principal */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-xs dark:border-gray-800 dark:bg-gray-900">
        <div className="mb-5">
          <h2 className="text-base font-bold text-gray-900 dark:text-white">
            Consulta de Incidentes en SharePoint
          </h2>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Selecciona el archivo Excel y digita el código{" "}
            <span className="font-semibold text-gray-700 dark:text-gray-300">INC</span>{" "}
            para consultar.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-12 md:items-end">
          {/* Selector de archivo Excel */}
          <div className="md:col-span-5">
            <label
              htmlFor="incidente-fuente-select"
              className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300"
            >
              <FileSpreadsheet className="h-3.5 w-3.5 text-brand-500" />
              Archivo a consultar
            </label>
            <select
              id="incidente-fuente-select"
              value={fuenteSeleccionada}
              onChange={(e) => handleCambioFuente(e.target.value)}
              disabled={isLoadingFuentes || isSearching || isRefreshing}
              className="h-[42px] w-full rounded-xl border border-gray-300 bg-white px-3.5 text-sm font-medium text-gray-800 shadow-xs transition-colors focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-white"
            >
              {isLoadingFuentes ? (
                <option value="">Cargando archivos...</option>
              ) : (
                fuentes.map((f) => (
                  <option key={f.key} value={f.key} disabled={!f.habilitado}>
                    {f.label}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Buscador único de INC */}
          <div className="md:col-span-5">
            <label
              htmlFor="incidente-buscador-input"
              className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-300"
            >
              <Hash className="h-3.5 w-3.5 text-brand-500" />
              INC
            </label>
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                id="incidente-buscador-input"
                type="text"
                value={incInput}
                onChange={(e) => setIncInput(e.target.value.toUpperCase())}
                placeholder="Ej: INC012345"
                maxLength={40}
                autoComplete="off"
                className="h-[42px] w-full rounded-xl border border-gray-300 bg-white pr-9 pl-10 text-sm font-medium uppercase text-gray-900 placeholder:normal-case placeholder:text-gray-400 shadow-xs transition-colors focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 focus:outline-hidden dark:border-gray-700 dark:bg-gray-800 dark:text-white"
              />
              {incInput && (
                <button
                  type="button"
                  onClick={handleLimpiar}
                  title="Limpiar búsqueda"
                  className="absolute top-1/2 right-2.5 -translate-y-1/2 rounded-full p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>

          {/* Botón de búsqueda */}
          <div className="flex items-center md:col-span-2">
            <button
              type="submit"
              disabled={isSearching || isRefreshing || isLoadingFuentes || !fuenteActual?.habilitado}
              className="inline-flex h-[42px] w-full items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 text-sm font-semibold text-white shadow-xs transition-colors hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <Search className={`h-4 w-4 ${isSearching ? "animate-pulse" : ""}`} />
              {isSearching ? "Buscando..." : "Buscar"}
            </button>
          </div>
        </form>
      </div>

      {/* Estado de carga */}
      {isSearching && (
        <div className="flex items-center gap-3 rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-600 shadow-xs dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300">
          <RefreshCw className="h-5 w-5 animate-spin text-brand-500" />
          <span>Consultando información del incidente en SharePoint...</span>
        </div>
      )}

      {/* Error */}
      {!isSearching && errorMsg && (
        <div className="flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50/70 p-5 text-sm text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <p className="font-semibold">No se pudo completar la consulta</p>
            <p className="mt-0.5 text-xs opacity-90">{errorMsg}</p>
          </div>
        </div>
      )}

      {/* No encontrado (404) */}
      {!isSearching && notFoundInfo && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50/60 p-6 shadow-xs dark:border-amber-900/50 dark:bg-amber-950/20">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
            <div className="flex items-start gap-3">
              <Info className="mt-0.5 h-5 w-5 shrink-0 text-amber-600 dark:text-amber-400" />
              <div>
                <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                  Incidente no encontrado
                </h3>
                <p className="mt-1 text-xs text-gray-600 dark:text-gray-300">
                  No se encontró el código{" "}
                  <span className="font-mono font-bold">{notFoundInfo.inc}</span> en{" "}
                  <span className="font-semibold">{notFoundInfo.fuente.label}</span>.
                </p>
                <p className="mt-1 text-[11px] text-gray-500 dark:text-gray-400">
                  {formatAntiguedad(notFoundInfo.antiguedad_minutos, notFoundInfo.refreshed)}
                  {notFoundInfo.stale ? " (copia de respaldo por intermitencia en SharePoint)" : ""}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => ejecutarBusqueda(ultimoIncBuscado || incInput, true)}
              disabled={isRefreshing}
              className="inline-flex items-center gap-1.5 self-start rounded-lg border border-amber-300 bg-white px-3 py-1.5 text-xs font-semibold text-amber-800 transition-colors hover:bg-amber-50 disabled:opacity-60 dark:border-amber-800 dark:bg-gray-900 dark:text-amber-300"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
              {isRefreshing ? "Actualizando..." : "Actualizar desde SharePoint"}
            </button>
          </div>
        </div>
      )}

      {/* Resultado encontrado */}
      {!isSearching && principal && metaActual && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-xs dark:border-gray-800 dark:bg-gray-900">
            {/* Cabecera del resultado */}
            <div className="flex flex-col justify-between gap-4 border-b border-gray-100 pb-4 sm:flex-row sm:items-center dark:border-gray-800">
              <div>
                <div className="flex flex-wrap items-center gap-2.5">
                  <span className="font-mono text-lg font-bold text-gray-900 dark:text-white">
                    {principal.inc}
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-500 dark:text-gray-400">
                  <span className="inline-flex items-center gap-1">
                    <FileSpreadsheet className="h-3.5 w-3.5" />
                    {metaActual.fuente.label}
                  </span>
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    {formatAntiguedad(metaActual.antiguedad_minutos, metaActual.refreshed)}
                  </span>
                  {metaActual.stale && (
                    <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-medium text-amber-800 dark:bg-amber-950/60 dark:text-amber-300">
                      Datos en respaldo (SharePoint no respondió)
                    </span>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => ejecutarBusqueda(ultimoIncBuscado || principal.inc, true)}
                disabled={isRefreshing}
                className="inline-flex items-center gap-1.5 self-start rounded-xl border border-gray-300 bg-white px-3.5 py-2 text-xs font-semibold text-gray-700 shadow-xs transition-colors hover:bg-gray-50 disabled:opacity-60 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-brand-500" : ""}`} />
                {isRefreshing ? "Actualizando..." : "Actualizar"}
              </button>
            </div>

            {/* Si hay múltiples coincidencias, mostrar directamente la tabla; si es única, tarjetas */}
            {metaActual.coincidencias.length > 1 ? (
              <div className="mt-4 space-y-4">
                <div className="flex items-center gap-2 rounded-xl border border-brand-200 bg-brand-50/70 px-3.5 py-2.5 text-xs text-brand-800 dark:border-brand-900/50 dark:bg-brand-950/30 dark:text-brand-300">
                  <Info className="h-4 w-4 shrink-0" />
                  <span>
                    Se encontraron <strong>{metaActual.coincidencias.length}</strong> registros con este INC en la tabla.
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200 text-left text-xs dark:divide-gray-800">
                    <thead>
                      <tr className="text-gray-500 dark:text-gray-400">
                        <th className="py-2 pr-4 font-semibold">INC</th>
                        <th className="py-2 pr-4 font-semibold">F_CREACION</th>
                        <th className="py-2 pr-4 font-semibold">OT</th>
                        <th className="py-2 pr-4 font-semibold">CLIENTE</th>
                        <th className="py-2 font-semibold">ESTADO</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                      {metaActual.coincidencias.map((item, idx) => (
                        <tr key={`${item.inc}-${item.ot}-${idx}`} className="text-gray-800 dark:text-gray-200">
                          <td className="py-2.5 pr-4 font-mono font-semibold">{item.inc}</td>
                          <td className="py-2.5 pr-4">{formatFechaCreacion(item.f_creacion)}</td>
                          <td className="py-2.5 pr-4 font-mono">{item.ot || "—"}</td>
                          <td className="py-2.5 pr-4">{item.cliente || "—"}</td>
                          <td className="py-2.5">
                            <span
                              className={`inline-flex rounded-full border px-2 py-0.5 text-[11px] font-semibold ${getEstadoBadgeClass(item.estado)}`}
                            >
                              {item.estado || "—"}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ) : (
              <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-4 dark:border-gray-800 dark:bg-gray-800/50">
                  <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    <Calendar className="h-3.5 w-3.5 text-brand-500" />
                    F_CREACION
                  </div>
                  <p className="mt-2 text-sm font-bold text-gray-900 dark:text-white">
                    {formatFechaCreacion(principal.f_creacion)}
                  </p>
                </div>

                <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-4 dark:border-gray-800 dark:bg-gray-800/50">
                  <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    <Wrench className="h-3.5 w-3.5 text-brand-500" />
                    OT
                  </div>
                  <p className="mt-2 font-mono text-sm font-bold text-gray-900 dark:text-white">
                    {principal.ot || "—"}
                  </p>
                </div>

                <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-4 dark:border-gray-800 dark:bg-gray-800/50">
                  <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    <User className="h-3.5 w-3.5 text-brand-500" />
                    CLIENTE
                  </div>
                  <p className="mt-2 text-sm font-bold text-gray-900 dark:text-white">
                    {principal.cliente || "—"}
                  </p>
                </div>

                <div className="rounded-xl border border-gray-100 bg-gray-50/70 p-4 dark:border-gray-800 dark:bg-gray-800/50">
                  <div className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    <Info className="h-3.5 w-3.5 text-brand-500" />
                    ESTADO
                  </div>
                  <div className="mt-2">
                    <span
                      className={`inline-flex items-center rounded-full border px-3 py-0.5 text-xs font-bold ${getEstadoBadgeClass(principal.estado)}`}
                    >
                      {principal.estado || "—"}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default IncidentesView;
