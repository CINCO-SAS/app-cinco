"use client";

import PageBreadcrumb from "@/components/common/PageBreadCrumb";
import ComponentCard from "@/components/common/ComponentCard";
import { EmployeeSearchInput } from "@/components/form/EmployeeSearchInput";
import Alert from "@/components/ui/alert/Alert";
import Button from "@/components/ui/button/Button";
import { getErrorMessage, classifyError } from "@/lib/errorHandler";
import {
  downloadCertificadoLaboral,
  CertificadoLaboralManualData,
  getCertificadoFirmaConfig,
  updateCertificadoFirmaConfig,
  CertificadoFirmaConfigData
} from "@/services/empleado.service";
import { Empleado } from "@/types/empleado";
import { Download, FileText, Edit, UserX, Loader2, Save, Upload } from "lucide-react";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth.store";
import { hasCertificadosPermission, hasFirmaConfigPermission } from "@/utils/permission";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/apiConfig";

type DocumentType = "CC" | "PT" | "TI" | "CE";

const documentTypeOptions: { value: DocumentType; label: string }[] = [
  { value: "CC", label: "CC" },
  { value: "PT", label: "PT" },
  { value: "TI", label: "TI" },
  { value: "CE", label: "CE" },
];

const contratoOptions = [
  { value: "OBRA Y LABOR", label: "Obra y labor" },
  { value: "Término indefinido", label: "Término indefinido" },
  { value: "Término fijo", label: "Término fijo" },
];

const selectClasses =
  "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800";

const inputClasses =
  "h-11 w-full rounded-lg border border-gray-300 bg-transparent px-3 py-2 text-sm text-gray-800 shadow-theme-xs focus:border-brand-300 focus:outline-hidden focus:ring-3 focus:ring-brand-500/10 dark:border-gray-700 dark:bg-gray-900 dark:text-white/90 dark:focus:border-brand-800";

const CertificadosLaboralesModule = () => {
  const user = useAuthStore((state) => state.user);
  const hasPermission = hasCertificadosPermission(user);
  const router = useRouter();

  const [selectedEmployee, setSelectedEmployee] = useState<Empleado | null>(null);
  const [documentType, setDocumentType] = useState<DocumentType>("CC");
  const [isDownloading, setIsDownloading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  // Manual form state
  const [showManualForm, setShowManualForm] = useState(false);
  const [salario, setSalario] = useState("");
  const [tipoContrato, setTipoContrato] = useState("OBRA Y LABOR");
  const [cargo, setCargo] = useState("");
  const [fechaIngreso, setFechaIngreso] = useState("");
  const [fechaEgreso, setFechaEgreso] = useState("");
  const [estado, setEstado] = useState("ACTIVO");
  const [genero, setGenero] = useState("M");

  // Signature management state
  const hasFirmaPermission = hasFirmaConfigPermission(user);
  const [firmaConfig, setFirmaConfig] = useState<CertificadoFirmaConfigData | null>(null);
  const [firmanteNombre, setFirmanteNombre] = useState("");
  const [firmanteCargo, setFirmanteCargo] = useState("");
  const [firmaFile, setFirmaFile] = useState<File | null>(null);
  const [isSavingFirma, setIsSavingFirma] = useState(false);
  const [firmaPreviewUrl, setFirmaPreviewUrl] = useState("");
  const [firmaMessage, setFirmaMessage] = useState("");
  const [firmaError, setFirmaError] = useState("");
  const [cacheBuster, setCacheBuster] = useState(0);

  const loadFirmaConfig = async () => {
    try {
      const data = await getCertificadoFirmaConfig();
      setFirmaConfig(data);
      setFirmanteNombre(data.firmante_nombre);
      setFirmanteCargo(data.firmante_cargo);
      setFirmaPreviewUrl(`${API_BASE_URL}/empleados/empleados/certificado-firma-imagen/?t=${Date.now()}`);
    } catch (err) {
      console.error("Error al cargar la configuración de la firma", err);
    }
  };

  useEffect(() => {
    if (user && hasFirmaPermission) {
      loadFirmaConfig();
    }
  }, [user, hasFirmaPermission]);

  const handleSaveFirmaConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!firmanteNombre.trim() || !firmanteCargo.trim()) {
      setFirmaError("El nombre y cargo son obligatorios.");
      return;
    }

    setIsSavingFirma(true);
    setFirmaError("");
    setFirmaMessage("");

    try {
      const formData = new FormData();
      formData.append("firmante_nombre", firmanteNombre.trim());
      formData.append("firmante_cargo", firmanteCargo.trim());
      if (firmaFile) {
        formData.append("firma_imagen", firmaFile);
      }

      const updated = await updateCertificadoFirmaConfig(formData);
      setFirmaConfig(updated);
      setFirmaFile(null);
      setCacheBuster((prev) => prev + 1);
      setFirmaMessage("Configuración de firma actualizada exitosamente.");
      setFirmaPreviewUrl(`${API_BASE_URL}/empleados/empleados/certificado-firma-imagen/?t=${Date.now()}`);
    } catch (err: any) {
      const msg = getErrorMessage(err);
      setFirmaError(msg || "Ocurrió un error al guardar la configuración.");
    } finally {
      setIsSavingFirma(false);
    }
  };

  useEffect(() => {
    if (user && !hasPermission) {
      router.replace("/");
    }
  }, [user, hasPermission, router]);

  useEffect(() => {
    if (selectedEmployee) {
      setCargo(selectedEmployee.cargo || "");
      setFechaIngreso(selectedEmployee.fecha_ingreso || "");
      setFechaEgreso(selectedEmployee.fecha_egreso || "");
      setEstado(selectedEmployee.estado || "ACTIVO");
      const empGenero = selectedEmployee?.genero;
      setGenero(typeof empGenero === "string" && empGenero.toUpperCase().startsWith("F") ? "F" : "M");
      setSalario("");
      setShowManualForm(false);
      setErrorMessage("");
      setSuccessMessage("");
    }
  }, [selectedEmployee]);

  if (!hasPermission) {
    return null;
  }

  const triggerDownload = async (manualData?: CertificadoLaboralManualData) => {
    if (!selectedEmployee || isDownloading) return;

    setIsDownloading(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      const { blob, filename } = await downloadCertificadoLaboral(
        selectedEmployee.id,
        documentType,
        manualData,
      );
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      window.URL.revokeObjectURL(url);
      setSuccessMessage(
        `Se generó el certificado de ${selectedEmployee.nombre} ${selectedEmployee.apellido}.`,
      );
    } catch (error: any) {
      const classified = classifyError(error);
      const msg = getErrorMessage(classified);
      setErrorMessage(msg);
      // Auto-display manual form if SIIGO or contract/salary data is missing
      setShowManualForm(true);
    } finally {
      setIsDownloading(false);
    }
  };

  const handleDownloadAuto = () => {
    const manualData: CertificadoLaboralManualData = {
      estado,
      ...(fechaEgreso ? { fecha_egreso: fechaEgreso } : {}),
    };
    void triggerDownload(manualData);
  };

  const handleDownloadManual = () => {
    if (!salario || Number(salario) <= 0) {
      setErrorMessage("Por favor ingrese un salario básico válido mayor a cero.");
      return;
    }
    const manualData: CertificadoLaboralManualData = {
      salario,
      tipo_contrato: tipoContrato,
      cargo,
      fecha_ingreso: fechaIngreso,
      fecha_egreso: fechaEgreso,
      estado,
      genero,
    };
    void triggerDownload(manualData);
  };

  return (
    <div className="space-y-6">
      <PageBreadcrumb pageTitle={["RRHH", "Certificados Laborales"]} />

      <ComponentCard
        title="Generación de certificado laboral"
        desc="Selecciona un empleado para descargar su certificado laboral en PDF. Si el empleado no existe en SIIGO, puedes ingresar los datos manualmente."
      >
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.4fr)_320px]">
          <div className="space-y-6">
            <EmployeeSearchInput
              label="Empleado"
              value={selectedEmployee}
              onChange={(employee) => {
                setSelectedEmployee(employee);
              }}
              placeholder="Busca por nombre, apellido o cédula"
              hint="El selector consume el endpoint de empleados del backend."
              includeInactive={true}
            />

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Tipo de documento
                </label>
                <select
                  value={documentType}
                  onChange={(event) =>
                    setDocumentType(event.target.value as DocumentType)
                  }
                  className={selectClasses}
                >
                  {documentTypeOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Estado del certificado
                </label>
                <select
                  value={estado}
                  onChange={(event) => setEstado(event.target.value)}
                  className={selectClasses}
                >
                  <option value="ACTIVO">Activo</option>
                  <option value="INACTIVO">Inactivo / Retirado</option>
                </select>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Button
                onClick={handleDownloadAuto}
                disabled={!selectedEmployee || isDownloading}
                startIcon={
                  isDownloading ? (
                    <Loader2 size={16} className="animate-spin text-white" />
                  ) : (
                    <Download size={16} />
                  )
                }
              >
                {isDownloading ? "Generando certificado..." : "Descargar certificado"}
              </Button>

              {selectedEmployee && !showManualForm && (
                <Button
                  variant="outline"
                  onClick={() => setShowManualForm(true)}
                  disabled={isDownloading}
                  startIcon={<Edit size={16} />}
                >
                  Ingresar datos manualmente
                </Button>
              )}
            </div>

            {isDownloading && (
              <div className="flex items-center gap-3.5 rounded-xl border border-brand-200 bg-brand-50/80 p-4 dark:border-brand-900/60 dark:bg-brand-950/40 text-brand-900 dark:text-brand-100 shadow-sm animate-pulse">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-500/10 text-brand-600 dark:bg-brand-500/20 dark:text-brand-400">
                  <Loader2 className="h-5 w-5 animate-spin" />
                </div>
                <div className="text-sm">
                  <p className="font-semibold text-brand-800 dark:text-brand-200">
                    Generando certificado laboral PDF...
                  </p>
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    Consultando la información del empleado y compilando el documento. Por favor espera un momento.
                  </p>
                </div>
              </div>
            )}

            {errorMessage ? (
              <Alert
                variant="error"
                title="No fue posible generar el certificado"
                message={errorMessage}
              />
            ) : null}

            {successMessage ? (
              <Alert
                variant="success"
                title="Certificado generado"
                message={successMessage}
              />
            ) : null}

            {/* Formulario para ingreso manual si no hay SIIGO o se elige ingresar manualmente */}
            {selectedEmployee && showManualForm && (
              <div className="rounded-2xl border border-brand-200 bg-brand-50/40 p-5 dark:border-brand-900/50 dark:bg-brand-950/20 space-y-4">
                <div className="flex items-center gap-2 text-brand-700 dark:text-brand-300">
                  <UserX size={18} />
                  <h4 className="text-sm font-semibold">
                    Ingreso manual de datos del certificado
                  </h4>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  Completa o modifica la información del contrato y salario para generar el PDF.
                </p>

                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                      Salario básico ($) *
                    </label>
                    <input
                      type="number"
                      value={salario}
                      onChange={(e) => setSalario(e.target.value)}
                      placeholder="Ej: 1423500"
                      className={inputClasses}
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                      Tipo de Contrato *
                    </label>
                    <select
                      value={tipoContrato}
                      onChange={(e) => setTipoContrato(e.target.value)}
                      className={selectClasses}
                    >
                      {contratoOptions.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                      Cargo
                    </label>
                    <input
                      type="text"
                      value={cargo}
                      onChange={(e) => setCargo(e.target.value)}
                      placeholder="Ej: TECNICO INSTALACIONES"
                      className={inputClasses}
                    />
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                      Estado
                    </label>
                    <select
                      value={estado}
                      onChange={(e) => setEstado(e.target.value)}
                      className={selectClasses}
                    >
                      <option value="ACTIVO">Activo</option>
                      <option value="INACTIVO">Inactivo / Retirado</option>
                    </select>
                  </div>

                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700 dark:text-gray-300">
                      Fecha de Ingreso
                    </label>
                    <input
                      type="date"
                      value={fechaIngreso}
                      onChange={(e) => setFechaIngreso(e.target.value)}
                      className={inputClasses}
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-gray-700 dark:text-gray-300">
                      Fecha de egreso (si aplica)
                    </label>
                    <input
                      type="date"
                      value={fechaEgreso}
                      onChange={(e) => setFechaEgreso(e.target.value)}
                      className={inputClasses}
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-xs font-medium text-gray-700 dark:text-gray-300">
                      Género gramatical
                    </label>
                    <select
                      value={genero}
                      onChange={(e) => setGenero(e.target.value)}
                      className={selectClasses}
                    >
                      <option value="M">Masculino (el señor / identificado)</option>
                      <option value="F">Femenino (la señora / identificada)</option>
                    </select>
                  </div>
                </div>

                <div className="pt-2 flex items-center justify-between gap-3">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowManualForm(false)}
                  >
                    Ocultar formulario
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleDownloadManual}
                    disabled={isDownloading}
                    startIcon={
                      isDownloading ? (
                        <Loader2 size={15} className="animate-spin text-white" />
                      ) : (
                        <Download size={15} />
                      )
                    }
                  >
                    {isDownloading ? "Generando..." : "Generar con datos manuales"}
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="rounded-2xl border border-dashed border-gray-300 bg-gray-50/70 p-5 dark:border-gray-700 dark:bg-gray-900/40">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-xl bg-brand-50 p-3 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400">
                <FileText size={20} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-800 dark:text-white/90">
                  Resumen de validación
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Información para verificar la generación.
                </p>
              </div>
            </div>

            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500 dark:text-gray-400">Empleado</dt>
                <dd className="font-medium text-gray-800 dark:text-white/90">
                  {selectedEmployee
                    ? `${selectedEmployee.nombre} ${selectedEmployee.apellido}`
                    : "Sin seleccionar"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">Cédula</dt>
                <dd className="font-medium text-gray-800 dark:text-white/90">
                  {selectedEmployee?.cedula || "Sin seleccionar"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">Cargo</dt>
                <dd className="font-medium text-gray-800 dark:text-white/90">
                  {cargo || selectedEmployee?.cargo || "No disponible"}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">
                  Tipo de documento
                </dt>
                <dd className="font-medium text-gray-800 dark:text-white/90">
                  {documentType}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">
                  Estado del certificado
                </dt>
                <dd className="font-medium text-gray-800 dark:text-white/90">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold ${
                      estado === "INACTIVO"
                        ? "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
                        : "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
                    }`}
                  >
                    {estado === "INACTIVO" ? "Inactivo / Retirado" : "Activo"}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-gray-500 dark:text-gray-400">
                  Modo de generación
                </dt>
                <dd className="font-medium text-gray-800 dark:text-white/90">
                  {showManualForm ? "Ingreso manual de datos" : "Automático (SIIGO)"}
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </ComponentCard>

      {hasFirmaPermission && (
        <div className="mt-6">
          <ComponentCard title="Gestión de Firma del Certificado">
            <form onSubmit={handleSaveFirmaConfig} className="space-y-6">
              {firmaMessage && (
                <Alert variant="success" title="Éxito" message={firmaMessage} />
              )}
              {firmaError && (
                <Alert variant="error" title="Error" message={firmaError} />
              )}

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Nombre del firmante
                    </label>
                    <input
                      type="text"
                      value={firmanteNombre}
                      onChange={(e) => setFirmanteNombre(e.target.value)}
                      placeholder="Ej. FARAY MONSALVE URREGO"
                      className={inputClasses}
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Cargo del firmante
                    </label>
                    <input
                      type="text"
                      value={firmanteCargo}
                      onChange={(e) => setFirmanteCargo(e.target.value)}
                      placeholder="Ej. Dirección Gestión Humana"
                      className={inputClasses}
                    />
                  </div>

                  <div>
                    <label className="mb-1.5 block text-sm font-medium text-gray-700 dark:text-gray-300">
                      Nueva imagen de firma (PNG/JPG)
                    </label>
                    <div className="relative flex items-center justify-center rounded-lg border border-dashed border-gray-300 p-4 hover:bg-gray-50/50 dark:border-gray-700 dark:hover:bg-gray-800/50">
                      <input
                        type="file"
                        accept="image/*"
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setFirmaFile(e.target.files[0]);
                          }
                        }}
                        className="absolute inset-0 cursor-pointer opacity-0"
                      />
                      <div className="flex flex-col items-center space-y-1 text-center">
                        <Upload className="h-6 w-6 text-gray-400" />
                        <span className="text-xs text-gray-600 dark:text-gray-400">
                          {firmaFile ? firmaFile.name : "Subir imagen de firma"}
                        </span>
                        <span className="text-[10px] text-gray-400">
                          Arrastra o selecciona un archivo
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col items-center justify-center rounded-xl border border-gray-200 bg-gray-50/50 p-6 dark:border-gray-800 dark:bg-gray-900/30">
                  <span className="mb-3 text-xs font-semibold text-gray-500 dark:text-gray-400">
                    Vista previa de firma actual
                  </span>
                  <div className="flex h-36 w-full max-w-60 items-center justify-center rounded-lg border border-gray-300 bg-white p-3 shadow-sm dark:border-gray-800 dark:bg-gray-950">
                    {firmaPreviewUrl ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={firmaPreviewUrl}
                        alt="Firma actual"
                        className="max-h-full max-w-full object-contain"
                        onError={(e) => {
                          // No-op
                        }}
                      />
                    ) : (
                      <span className="text-xs text-gray-400">Sin firma configurada</span>
                    )}
                  </div>
                  <span className="mt-2 text-[10px] text-gray-400 text-center">
                    Esta firma se plasmará en todos los certificados generados
                  </span>
                </div>
              </div>

              <div className="flex justify-end pt-4 border-t border-gray-200 dark:border-gray-800">
                <Button
                  type="submit"
                  disabled={isSavingFirma}
                  startIcon={
                    isSavingFirma ? (
                      <Loader2 size={15} className="animate-spin text-white" />
                    ) : (
                      <Save size={15} />
                    )
                  }
                >
                  {isSavingFirma ? "Guardando..." : "Guardar cambios"}
                </Button>
              </div>
            </form>
          </ComponentCard>
        </div>
      )}
    </div>
  );
};

export default CertificadosLaboralesModule;
