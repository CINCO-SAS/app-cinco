"use client";

import React, { useState } from "react";
import {
  UploadCloud,
  FileSpreadsheet,
  Download,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Info,
} from "lucide-react";
import { ResultadoImportacionCsv } from "@/types/agenda.types";
import { agendaService } from "@/services/agenda.service";
import { toast } from "sonner";

interface AgendaImportarCsvTabProps {
  onImportacionFinalizada: () => void;
}

export const AgendaImportarCsvTab: React.FC<AgendaImportarCsvTabProps> = ({
  onImportacionFinalizada,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [importResult, setImportResult] = useState<ResultadoImportacionCsv | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      if (!file.name.toLowerCase().endsWith(".csv") && !file.name.toLowerCase().endsWith(".txt")) {
        toast.error("Por favor selecciona un archivo con extensión .csv");
        return;
      }
      setSelectedFile(file);
      setImportResult(null);
    }
  };

  const handleDescargarPlantilla = () => {
    const encabezados = "cedula,ot,fecha_inicio,fecha_fin,nombre_actividad\n";
    const ejemplo = "1020304050,OT-10023,2026-06-15,2026-06-18,MANTENIMIENTO NODO CENTRAL\n";
    const blob = new Blob([encabezados + ejemplo], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", "plantilla_agendas_cinco.csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleSubirArchivo = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    try {
      const res = await agendaService.importarCsv(selectedFile);
      setImportResult(res);

      if (res.fallidos === 0) {
        toast.success(`Se procesaron correctamente ${res.exitosos} agendamientos.`);
      } else {
        toast.warning(`Exitosos: ${res.exitosos} | Fallidos: ${res.fallidos}. Revisa la tabla de detalles a continuación.`);
      }

      onImportacionFinalizada();
    } catch (error: any) {
      const msg = error?.response?.data?.msg || error?.message || "Error al procesar el archivo CSV.";
      toast.error(msg);
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800 space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
        {/* Panel Izquierdo: Carga de Archivo */}
        <div className="md:col-span-6 border border-gray-200 dark:border-gray-800 rounded-xl p-4 bg-gray-50 dark:bg-gray-800/40 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 flex items-center">
                <FileSpreadsheet className="h-4 w-4 mr-2 text-brand-600 dark:text-brand-400" /> Cargar Archivo CSV de Agendas
              </h4>
              <button
                type="button"
                onClick={handleDescargarPlantilla}
                className="inline-flex items-center text-xs text-brand-600 dark:text-brand-400 hover:underline font-medium"
              >
                <Download className="h-3 w-3 mr-1" /> Descargar Plantilla
              </button>
            </div>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-3">
              Sube un archivo CSV con las columnas necesarias para crear las agendas masivamente. El sistema validará la OT y comprobará los cruces de agenda de cada técnico.
            </p>

            <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 rounded-lg p-4 text-center bg-white dark:bg-gray-900/50 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors">
              <input
                type="file"
                id="csv_agenda_file"
                accept=".csv, .txt"
                onChange={handleFileChange}
                className="hidden"
              />
              <label htmlFor="csv_agenda_file" className="cursor-pointer block">
                <UploadCloud className="h-8 w-8 mx-auto text-gray-400 dark:text-gray-500 mb-1" />
                <span className="text-xs font-semibold text-brand-600 dark:text-brand-400">
                  {selectedFile ? selectedFile.name : "Haz clic para seleccionar el archivo CSV"}
                </span>
                <p className="text-[11px] text-gray-500 mt-1">Formato CSV delimitado por comas o punto y coma</p>
              </label>
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <button
              type="button"
              onClick={handleSubirArchivo}
              disabled={!selectedFile || isUploading}
              className="w-full sm:w-auto inline-flex items-center justify-center px-4 py-2 text-xs font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors disabled:opacity-50 shadow-sm"
            >
              {isUploading ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" /> Procesando filas...
                </>
              ) : (
                <>
                  <UploadCloud className="h-3.5 w-3.5 mr-2" /> Iniciar Importación
                </>
              )}
            </button>
          </div>
        </div>

        {/* Panel Derecho: Guía de Formato */}
        <div className="md:col-span-6 border border-gray-200 dark:border-gray-800 rounded-xl p-4 bg-gray-50 dark:bg-gray-800/40 flex flex-col justify-between">
          <div>
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 flex items-center mb-2">
              <Info className="h-4 w-4 mr-2 text-brand-600 dark:text-brand-400" /> Formato de Columnas Requerido
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2">
              La primera fila debe contener los encabezados exactos:
            </p>
            <ul className="text-xs space-y-1.5 text-gray-700 dark:text-gray-300">
              <li className="flex items-start">
                <span className="font-mono font-bold text-brand-600 dark:text-brand-400 mr-1.5">• cedula:</span>
                Cédula del técnico en base de personal. (Obligatorio)
              </li>
              <li className="flex items-start">
                <span className="font-mono font-bold text-brand-600 dark:text-brand-400 mr-1.5">• ot:</span>
                Código de la OT / Actividad. (Obligatorio)
              </li>
              <li className="flex items-start">
                <span className="font-mono font-bold text-brand-600 dark:text-brand-400 mr-1.5">• fecha_inicio:</span>
                Fecha inicio en formato <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">YYYY-MM-DD</code>.
              </li>
              <li className="flex items-start">
                <span className="font-mono font-bold text-brand-600 dark:text-brand-400 mr-1.5">• fecha_fin:</span>
                Fecha fin en formato <code className="bg-gray-200 dark:bg-gray-700 px-1 rounded">YYYY-MM-DD</code>.
              </li>
              <li className="flex items-start">
                <span className="font-mono font-bold text-brand-600 dark:text-brand-400 mr-1.5">• nombre_actividad:</span>
                Nombre descriptivo. (Opcional, se infiere si se omite).
              </li>
            </ul>
          </div>
        </div>
      </div>

      {/* Resultados de la importación */}
      {importResult && (
        <div className="border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden bg-white dark:bg-gray-900 mt-4">
          <div className="p-3 bg-gray-50 dark:bg-gray-800/80 border-b border-gray-200 dark:border-gray-800 flex items-center justify-between">
            <h5 className="text-xs font-bold text-gray-900 dark:text-gray-100 flex items-center">
              Resultados del Procesamiento ({importResult.total_filas} filas)
            </h5>
            <div className="flex space-x-2 text-xs font-semibold">
              <span className="px-2 py-0.5 bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 rounded-full">
                ✓ Exitosos: {importResult.exitosos}
              </span>
              <span className="px-2 py-0.5 bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300 rounded-full">
                ✗ Fallidos: {importResult.fallidos}
              </span>
            </div>
          </div>

          <div className="max-h-60 overflow-y-auto">
            <table className="w-full text-xs text-left">
              <thead className="text-[11px] text-gray-500 uppercase bg-gray-100 dark:bg-gray-800 sticky top-0">
                <tr>
                  <th className="py-2 px-3">Fila</th>
                  <th className="py-2 px-3">Técnico</th>
                  <th className="py-2 px-3">OT</th>
                  <th className="py-2 px-3">Fechas</th>
                  <th className="py-2 px-3">Estado</th>
                  <th className="py-2 px-3">Detalle</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-gray-800 font-medium">
                {importResult.resultados.map((row, idx) => (
                  <tr
                    key={idx}
                    className={
                      row.success
                        ? "hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20"
                        : "hover:bg-rose-50/50 dark:hover:bg-rose-950/20 bg-rose-50/30 dark:bg-rose-950/10"
                    }
                  >
                    <td className="py-2 px-3">{row.fila}</td>
                    <td className="py-2 px-3 font-mono">{row.cedula}</td>
                    <td className="py-2 px-3 font-bold">{row.ot}</td>
                    <td className="py-2 px-3">
                      {row.fecha_inicio} al {row.fecha_fin}
                    </td>
                    <td className="py-2 px-3">
                      {row.success ? (
                        <span className="inline-flex items-center text-emerald-600 dark:text-emerald-400 font-semibold">
                          <CheckCircle2 className="h-3.5 w-3.5 mr-1" /> Éxito
                        </span>
                      ) : (
                        <span className="inline-flex items-center text-rose-600 dark:text-rose-400 font-semibold">
                          <XCircle className="h-3.5 w-3.5 mr-1" /> Error
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-gray-600 dark:text-gray-300">{row.mensaje}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
