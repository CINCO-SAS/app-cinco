"use client";

import React, { useEffect, useState } from "react";
import { X } from "lucide-react";
import FormStepSlider from "../common/FormStepSlider";
import Alert from "@/components/ui/alert/Alert";
import { useFormCatalogStore } from "@/store/formCatalog.store";
import {
  FormCapexTipologia3Data,
  InsumoSAPItem,
  ActividadMOItem,
  TransporteItem,
} from "./tipologia3/types";
import {
  STEPS_CONFIG_TIPOLOGIA_3,
  INITIAL_FORM_DATA_TIPOLOGIA_3,
  CATALOGO_SUMINISTROS_FRECUENTES,
  CATALOGO_ACTIVIDADES_FRECUENTES,
  createDefaultInsumo,
  createDefaultActividad,
  createDefaultTransporte,
} from "./tipologia3/constants";
import {
  Paso1General,
  Paso2Suministros,
  Paso3ActividadesMO,
  Paso4Transportes,
  Paso5Recomendaciones,
} from "./tipologia3";
import {
  getPendingStepTitles,
  isTipologia3FormComplete,
} from "./tipologia3/completion";
import { toast } from "sonner";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { liberarPreviewUrl } from "@/lib/fotos";
import {
  buildCapexTipologia3Payload,
  subirPendientes,
  validarFechasEncabezado,
  SMU_ACTIVIDADES_ENDPOINT,
  type PendienteSubida,
  type SmuPayload,
} from "@/services/smu.service";
import { manejarErrorGuardado, toastErrorActividad } from "@/modules/smu/errors";
import { clonarEstadoInicial, liberarPreviews } from "@/modules/smu/reinicio";

const FormCapexTipologia3Slider: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<FormCapexTipologia3Data>(
    INITIAL_FORM_DATA_TIPOLOGIA_3,
  );
  const { submit, isLoading } = useFormSubmit<SmuPayload>();
  // Cubre TODO el guardado (subida de fotos + POST): `isLoading` de
  // useFormSubmit solo está en true durante el POST.
  const [enviando, setEnviando] = useState(false);

  // ── Estado del catálogo frecuente (Zustand) ────────────────────────────────
  const consolidateCatalog = useFormCatalogStore((state) => state.consolidate);
  const resetCatalog = useFormCatalogStore((state) => state.resetCatalog);
  const completionWarning = useFormCatalogStore(
    (state) => state.completionWarning,
  );
  const dismissCompletionWarning = useFormCatalogStore(
    (state) => state.dismissCompletionWarning,
  );

  // El estado vive fuera del formulario: se limpia al entrar/salir para que
  const formDataRef = React.useRef(formData);
  React.useEffect(() => {
    formDataRef.current = formData;
  }, [formData]);

  useEffect(() => {
    return () => {
      resetCatalog();
      const d = formDataRef.current;
      d.insumos.forEach((i) => liberarPreviewUrl(i.foto_preview));
      d.actividades.forEach((a) => {
        liberarPreviewUrl(a.foto_antes_preview);
        liberarPreviewUrl(a.foto_despues_preview);
      });
      d.transportes.forEach((t) => {
        liberarPreviewUrl(t.foto_antes_preview);
        liberarPreviewUrl(t.foto_durante_preview);
        liberarPreviewUrl(t.foto_despues_preview);
      });
    };
  }, [resetCatalog]);

  /**
   * Consolida los chips "en uso" → "completados" y, si el formulario no está
   * completo, deja el aviso con los pasos que faltan.
   */
  const handleConsolidateCatalog = () => {
    consolidateCatalog({
      formComplete: isTipologia3FormComplete(formData),
      pendingStepTitles: getPendingStepTitles(formData),
    });
  };

  /** Se dispara al navegar con la barra de progreso o con Anterior/Siguiente. */
  const handleStepChange = (stepIndex: number) => {
    handleConsolidateCatalog();
    setCurrentStep(stepIndex);
  };

  const updateField = <K extends keyof FormCapexTipologia3Data>(
    field: K,
    value: FormCapexTipologia3Data[K],
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // ── Suministros Handlers ────────────────────────────────────────────────────
  const handleAddInsumo = () => {
    setFormData((prev) => ({
      ...prev,
      insumos: [...prev.insumos, createDefaultInsumo(prev.insumos.length + 1)],
    }));
  };

  const handleRemoveInsumo = (id: string) => {
    if (formData.insumos.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      insumos: prev.insumos.filter((i) => i.id !== id),
    }));
  };

  const handleUpdateInsumo = (
    id: string,
    field: keyof InsumoSAPItem,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      insumos: prev.insumos.map((i) =>
        i.id === id ? { ...i, [field]: value } : i,
      ),
    }));
  };

  const handleApplySuministroTemplate = (
    id: string,
    item: (typeof CATALOGO_SUMINISTROS_FRECUENTES)[0],
  ) => {
    setFormData((prev) => ({
      ...prev,
      insumos: prev.insumos.map((i) =>
        i.id === id
          ? {
              ...i,
              codigo_sap: item.codigo_sap,
              texto_sap: item.texto_sap,
              alcance: item.alcance,
              unidad_medida: item.unidad_medida,
              cantidad_estandar: item.cantidad_estandar,
              comentarios: item.comentarios,
            }
          : i,
      ),
    }));
  };

  const handleInsumoFotoUpload = (id: string, file: File) => {
    const insumo = formData.insumos.find((i) => i.id === id);
    liberarPreviewUrl(insumo?.foto_preview);
    const previewUrl = URL.createObjectURL(file);
    setFormData((prev) => ({
      ...prev,
      insumos: prev.insumos.map((i) =>
        i.id === id
          ? {
              ...i,
              foto_preview: previewUrl,
              foto_file: file,
              foto_nombre: file.name,
            }
          : i,
      ),
    }));
  };

  const handleInsumoFotoRemove = (id: string) => {
    const insumo = formData.insumos.find((i) => i.id === id);
    liberarPreviewUrl(insumo?.foto_preview);
    setFormData((prev) => ({
      ...prev,
      insumos: prev.insumos.map((i) =>
        i.id === id
          ? {
              ...i,
              foto_preview: undefined,
              foto_file: undefined,
              foto_nombre: undefined,
            }
          : i,
      ),
    }));
  };

  /** Título de la caja en el Excel para la foto del suministro. */
  const handleInsumoFotoDescripcion = (id: string, valor: string) => {
    handleUpdateInsumo(id, "foto_descripcion", valor);
  };

  // ── Actividades MO Handlers ─────────────────────────────────────────────────
  const handleAddActividad = () => {
    setFormData((prev) => ({
      ...prev,
      actividades: [
        ...prev.actividades,
        createDefaultActividad(prev.actividades.length + 1),
      ],
    }));
  };

  const handleRemoveActividad = (id: string) => {
    if (formData.actividades.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      actividades: prev.actividades.filter((a) => a.id !== id),
    }));
  };

  const handleUpdateActividad = (
    id: string,
    field: keyof ActividadMOItem,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      actividades: prev.actividades.map((a) =>
        a.id === id ? { ...a, [field]: value } : a,
      ),
    }));
  };

  const handleApplyActividadTemplate = (
    id: string,
    item: (typeof CATALOGO_ACTIVIDADES_FRECUENTES)[0],
  ) => {
    setFormData((prev) => ({
      ...prev,
      actividades: prev.actividades.map((a) =>
        a.id === id
          ? {
              ...a,
              codigo_sap: item.codigo_sap,
              texto_sap: item.texto_sap,
              alcance: item.alcance,
              comentarios: item.comentarios,
            }
          : a,
      ),
    }));
  };

  const handleActividadFotoUpload = (
    id: string,
    field: "foto_antes_preview" | "foto_despues_preview",
    file: File,
  ) => {
    const actividad = formData.actividades.find((a) => a.id === id);
    liberarPreviewUrl(actividad?.[field]);
    const previewUrl = URL.createObjectURL(file);
    const fileField =
      field === "foto_antes_preview" ? "foto_antes_file" : "foto_despues_file";
    const nombreField =
      field === "foto_antes_preview"
        ? "foto_antes_nombre"
        : "foto_despues_nombre";
    setFormData((prev) => ({
      ...prev,
      actividades: prev.actividades.map((a) =>
        a.id === id
          ? {
              ...a,
              [field]: previewUrl,
              [fileField]: file,
              [nombreField]: file.name,
            }
          : a,
      ),
    }));
  };

  const handleActividadFotoRemove = (
    id: string,
    field: "foto_antes_preview" | "foto_despues_preview",
  ) => {
    const actividad = formData.actividades.find((a) => a.id === id);
    liberarPreviewUrl(actividad?.[field]);
    const fileField =
      field === "foto_antes_preview" ? "foto_antes_file" : "foto_despues_file";
    const nombreField =
      field === "foto_antes_preview"
        ? "foto_antes_nombre"
        : "foto_despues_nombre";
    setFormData((prev) => ({
      ...prev,
      actividades: prev.actividades.map((a) =>
        a.id === id
          ? {
              ...a,
              [field]: undefined,
              [fileField]: undefined,
              [nombreField]: undefined,
            }
          : a,
      ),
    }));
  };

  /** Título de la caja en el Excel para las fotos antes/después. */
  const handleActividadFotoDescripcion = (
    id: string,
    parte: "antes" | "despues",
    valor: string,
  ) => {
    handleUpdateActividad(
      id,
      parte === "antes" ? "foto_antes_descripcion" : "foto_despues_descripcion",
      valor,
    );
  };

  // ── Transportes Handlers ────────────────────────────────────────────────────
  const handleAddTransporte = () => {
    setFormData((prev) => ({
      ...prev,
      transportes: [
        ...prev.transportes,
        createDefaultTransporte(prev.transportes.length + 1),
      ],
    }));
  };

  const handleRemoveTransporte = (id: string) => {
    if (formData.transportes.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      transportes: prev.transportes.filter((t) => t.id !== id),
    }));
  };

  const handleUpdateTransporte = (
    id: string,
    field: keyof TransporteItem,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      transportes: prev.transportes.map((t) =>
        t.id === id ? { ...t, [field]: value } : t,
      ),
    }));
  };

  const handleTransporteFotoUpload = (
    id: string,
    field:
      "foto_antes_preview" | "foto_durante_preview" | "foto_despues_preview",
    file: File,
  ) => {
    const transporte = formData.transportes.find((t) => t.id === id);
    liberarPreviewUrl(transporte?.[field]);
    const previewUrl = URL.createObjectURL(file);
    const fileField = field.replace("_preview", "_file") as
      "foto_antes_file" | "foto_durante_file" | "foto_despues_file";
    const nombreField = field.replace("_preview", "_nombre") as
      "foto_antes_nombre" | "foto_durante_nombre" | "foto_despues_nombre";
    setFormData((prev) => ({
      ...prev,
      transportes: prev.transportes.map((t) =>
        t.id === id
          ? {
              ...t,
              [field]: previewUrl,
              [fileField]: file,
              [nombreField]: file.name,
            }
          : t,
      ),
    }));
  };

  const handleTransporteFotoRemove = (
    id: string,
    field:
      "foto_antes_preview" | "foto_durante_preview" | "foto_despues_preview",
  ) => {
    const transporte = formData.transportes.find((t) => t.id === id);
    liberarPreviewUrl(transporte?.[field]);
    const fileField = field.replace("_preview", "_file") as
      "foto_antes_file" | "foto_durante_file" | "foto_despues_file";
    const nombreField = field.replace("_preview", "_nombre") as
      "foto_antes_nombre" | "foto_durante_nombre" | "foto_despues_nombre";
    setFormData((prev) => ({
      ...prev,
      transportes: prev.transportes.map((t) =>
        t.id === id
          ? {
              ...t,
              [field]: undefined,
              [fileField]: undefined,
              [nombreField]: undefined,
            }
          : t,
      ),
    }));
  };

  /** Título de la caja en el Excel para las fotos del transporte. */
  const handleTransporteFotoDescripcion = (
    id: string,
    parte: "antes" | "durante" | "despues",
    valor: string,
  ) => {
    handleUpdateTransporte(
      id,
      parte === "antes"
        ? "foto_antes_descripcion"
        : parte === "durante"
          ? "foto_durante_descripcion"
          : "foto_despues_descripcion",
      valor,
    );
  };

  /**
   * Tras un guardado exitoso el formulario queda vacío y en el paso 1, listo
   * para una nueva actividad; si no, el botón seguiría activo con los mismos
   * datos y un segundo clic duplicaría el registro.
   */
  const reiniciarFormulario = () => {
    liberarPreviews(formData);
    setFormData(clonarEstadoInicial(INITIAL_FORM_DATA_TIPOLOGIA_3));
    setCurrentStep(0);
  };

  const handleSubmit = async () => {
    // Un solo guardado en vuelo: si no, un segundo clic mientras se suben las
    // fotos (subirPendientes corre ANTES del POST) crearía la actividad dos veces.
    if (enviando) return;
    setEnviando(true);
    try {
      handleConsolidateCatalog();

      if (!formData.nombre_estacion.trim()) {
        toast.error("Ingresa el nombre de la estación.");
        return;
      }

      if (!formData.responsable_ejecuta?.cedula) {
        toast.error(
          "Selecciona el responsable que ejecuta: la cédula es obligatoria.",
        );
        return;
      }

      // La Fecha de Inicio es obligatoria y creíble (año 1900–2100): si queda
      // vacía o con basura ("12/12/1212"), el registro aparecería sin fecha en
      // el historial. Se bloquea con aviso en vez de guardar a medias.
      const errorFechas = validarFechasEncabezado(
        formData.fecha_inicio,
        formData.fecha_fin,
      );
      if (errorFechas) {
        toast.error(errorFechas);
        return;
      }

      // La completitud ya no es solo un aviso: sin ella no se guarda.
      // handleConsolidateCatalog() dejó el Alert con los pasos pendientes.
      if (!isTipologia3FormComplete(formData)) {
        toast.error(
          "Formulario incompleto: completa los pasos pendientes antes de guardar.",
        );
        return;
      }

      // Fase 3: las fotos se suben ANTES de crear la actividad (la API es
      // solo-POST, no hay PUT para adjuntarlas después).
      const pendientes: PendienteSubida[] = [];
      const payload = buildCapexTipologia3Payload(formData, pendientes);
      await subirPendientes(pendientes);

      await submit(payload, {
        endpoint: SMU_ACTIVIDADES_ENDPOINT,
        method: "POST",
        onSuccess: (res) => {
          toast.success(
            `Ficha CAPEX Tipología 3 guardada${
              res?.id ? ` (actividad #${res.id})` : ""
            }.`,
          );
          reiniciarFormulario();
        },
        onError: toastErrorActividad,
      });
    } catch (err) {
      // onError ya avisó los errores del backend (ApiErrorDetail); lo
      // inesperado (builder, catálogo, guardas) lo reporta este manejador.
      manejarErrorGuardado(err);
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      {completionWarning && (
        <div className="relative mb-4">
          <Alert
            variant="warning"
            title="Formulario incompleto"
            message={completionWarning}
          />
          <button
            type="button"
            onClick={dismissCompletionWarning}
            aria-label="Cerrar aviso"
            className="text-warning-500 hover:bg-warning-50 dark:hover:bg-warning-500/15 absolute top-3 right-3 rounded-md p-1 transition-all"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      <FormStepSlider
        steps={STEPS_CONFIG_TIPOLOGIA_3}
        currentStep={currentStep}
        onStepChange={handleStepChange}
        onSubmit={handleSubmit}
        submitLabel="Guardar Tipología 3"
        isSubmitting={isLoading || enviando}
      >
        {/* Paso 0: Información General */}
        {currentStep === 0 && (
          <Paso1General formData={formData} updateField={updateField} />
        )}

        {/* Paso 1: 1.- INVENTARIO DE SUMINISTROS */}
        {currentStep === 1 && (
          <Paso2Suministros
            insumos={formData.insumos}
            onAddInsumo={handleAddInsumo}
            onRemoveInsumo={handleRemoveInsumo}
            onUpdateInsumo={handleUpdateInsumo}
            onApplyTemplate={handleApplySuministroTemplate}
            onFotoUpload={handleInsumoFotoUpload}
            onFotoRemove={handleInsumoFotoRemove}
            onFotoDescripcion={handleInsumoFotoDescripcion}
          />
        )}

        {/* Paso 2: 2.- MO - ACTIVIDADES ESTANDARIZADAS */}
        {currentStep === 2 && (
          <Paso3ActividadesMO
            actividades={formData.actividades}
            onAddActividad={handleAddActividad}
            onRemoveActividad={handleRemoveActividad}
            onUpdateActividad={handleUpdateActividad}
            onApplyTemplate={handleApplyActividadTemplate}
            onFotoUpload={handleActividadFotoUpload}
            onFotoRemove={handleActividadFotoRemove}
            onFotoDescripcion={handleActividadFotoDescripcion}
          />
        )}

        {/* Paso 3: 3. TRANSPORTES */}
        {currentStep === 3 && (
          <Paso4Transportes
            transportes={formData.transportes}
            onAddTransporte={handleAddTransporte}
            onRemoveTransporte={handleRemoveTransporte}
            onUpdateTransporte={handleUpdateTransporte}
            onFotoUpload={handleTransporteFotoUpload}
            onFotoRemove={handleTransporteFotoRemove}
            onFotoDescripcion={handleTransporteFotoDescripcion}
          />
        )}

        {/* Paso 4: 4. RECOMENDACIONES DE LA ACTIVIDAD */}
        {currentStep === 4 && (
          <Paso5Recomendaciones formData={formData} updateField={updateField} />
        )}
      </FormStepSlider>
    </>
  );
};

export default FormCapexTipologia3Slider;
