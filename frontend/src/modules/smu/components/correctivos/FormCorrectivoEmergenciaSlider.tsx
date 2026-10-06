"use client";

import React, { useEffect, useRef, useState } from "react";
import FormStepSlider, { StepItem } from "../common/FormStepSlider";
import FotoSlotCard from "@/components/form/input/FotoSlotCard";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import Select from "@/components/form/Select";
import EmployeeSearchInput from "@/components/form/EmployeeSearchInput";
import { Empleado } from "@/types/empleado";
import {
  Plus,
  Trash2,
  CheckCircle2,
  Truck,
  Wrench,
  FileText,
  PenTool,
  ShieldCheck,
  AlertTriangle,
  Layers,
  Camera,
} from "lucide-react";
import type { CategoriaActividad } from "@/modules/smu/types/smu.types";
import { toast } from "sonner";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { liberarPreviewUrl } from "@/lib/fotos";
import { ORIGEN_MATERIAL_OPERARIO } from "@/modules/smu/constants";
import { quitarFotoEvidencia } from "@/modules/smu/evidencias";
import {
  buildCorrectivoEmergenciaPayload,
  subirPendientes,
  validarFechasEncabezado,
  SMU_ACTIVIDADES_ENDPOINT,
  type PendienteSubida,
  type SmuPayload,
} from "@/services/smu.service";
import { manejarErrorGuardado, toastErrorActividad } from "@/modules/smu/errors";
import { clonarEstadoInicial, liberarPreviews } from "@/modules/smu/reinicio";

// Opciones estandarizadas
const OPCIONES_SI_NO = [
  { value: "SI", label: "SÍ" },
  { value: "NO", label: "NO" },
];

const OPCIONES_SI_NO_NA = [
  { value: "SI", label: "SÍ" },
  { value: "NO", label: "NO" },
  { value: "N/A", label: "N/A" },
];

const OPCIONES_CATEGORIA_CRITICIDAD = [
  { value: "1. ALTA", label: "1. ALTA" },
  { value: "2. MEDIA", label: "2. MEDIA" },
  { value: "3. BAJA", label: "3. BAJA" },
];

const OPCIONES_TIPO_EQUIPO_FALLA = [
  { value: "NO APLICA FALLA", label: "NO APLICA FALLA" },
  { value: "PLANTA ELÉCTRICA", label: "PLANTA ELÉCTRICA" },
  { value: "AIRE ACONDICIONADO", label: "AIRE ACONDICIONADO" },
  { value: "RECTIFICADOR", label: "RECTIFICADOR" },
  { value: "BANCO DE BATERÍAS", label: "BANCO DE BATERÍAS" },
  { value: "SISTEMA SPT / PARARRAYOS", label: "SISTEMA SPT / PARARRAYOS" },
  {
    value: "TABLERO DE TRANSFERENCIA (ATS)",
    label: "TABLERO DE TRANSFERENCIA (ATS)",
  },
  {
    value: "SUBESTACIÓN / TRANSFORMADOR",
    label: "SUBESTACIÓN / TRANSFORMADOR",
  },
  { value: "ESTRUCTURA / TORRE", label: "ESTRUCTURA / TORRE" },
  { value: "OTRO", label: "OTRO" },
];

const OPCIONES_ORIGEN_MATERIAL = [
  { value: "CINCO SAS", label: "CINCO SAS" },
  { value: ORIGEN_MATERIAL_OPERARIO, label: ORIGEN_MATERIAL_OPERARIO },
  { value: "PROVEEDOR / ALIADO", label: "PROVEEDOR / ALIADO" },
];

const OPCIONES_UNIDAD_MEDIDA = [
  { value: "UNIDAD", label: "UNIDAD" },
  { value: "METROS", label: "METROS" },
  { value: "PAQ", label: "PAQ" },
  { value: "ROLLO", label: "ROLLO" },
  { value: "KG", label: "KG" },
  { value: "GALON", label: "GALÓN" },
  { value: "GLOBAL", label: "GLOBAL" },
];

const OPCIONES_TIPO_TRANSPORTE = [
  { value: "VEHICULO 4X4", label: "VEHÍCULO 4X4" },
  { value: "VEHICULO 4X2", label: "VEHÍCULO 4X2" },
  { value: "MOTO", label: "MOTOCICLETA" },
  { value: "CAMIÓN", label: "CAMIÓN" },
  { value: "LANCHA / FLUVIAL", label: "LANCHA / FLUVIAL" },
  { value: "A PIE / BESTIA", label: "A PIE / BESTIA" },
  { value: "OTRO", label: "OTRO" },
];

// Estructura de una evidencia fotográfica
export interface EvidenciaFotoItem {
  id: string;
  previewUrl?: string;
  file?: File;
  nombre?: string;
  descripcion: string;
}

// Estructura de Material
export interface MaterialInstaladoItem {
  id: string;
  origen_material: string;
  descripcion: string;
  cantidad: string;
  tipo_unidad: string;
  /**
   * Fotos de la fila del material: las columnas FOTO ANTES y FOTO DESPUÉS del
   * bloque 4 del Excel (`material_<n>_foto_antes|despues` en `campo_origen`).
   */
  foto_antes_preview?: string;
  foto_antes_file?: File;
  foto_despues_preview?: string;
  foto_despues_file?: File;
}

// Estructura del Formulario
export interface FormCorrectivoEmergenciaData {
  // Paso 1: Información General
  nombre_estacion: string;
  regional: string;
  departamento: string;
  direccion: string;
  tipo_estacion: string;
  tipo_sitio: string;
  site_owner: string;
  categoria_criticidad: string;
  responsable_1: Empleado | null;
  responsable_2: Empleado | null;
  numero_inc: string;
  numero_tas: string;
  fecha_inicio: string;
  fecha_fin: string;
  implica_exclusion: string;

  // Paso 2: Información de la Actividad
  tipo_actividad: string; // CORRECTIVO o EMERGENCIA
  tipo_equipo_falla: string;
  marca: string;
  modelo: string;
  presenta_afectacion_servicios: string;
  reinstalacion: string;
  cambio: string;
  reparacion: string;

  // Paso 3: Descripción de Falla y Solución
  descripcion_falla: string;
  descripcion_solucion: string;
  descripcion_fallas_componentes: string;

  // Paso 4: Materiales Instalados
  materiales: MaterialInstaladoItem[];

  // Paso 5: Transportes Especiales
  distancia_km: string;
  tiempo_desplazamiento: string;
  tipo_transporte: string;
  observacion_transporte: string;

  // Paso 6: Evidencias Fotográficas
  evidencias: EvidenciaFotoItem[];

  // Paso 7: Observaciones y Cierre (Firmas / Certificado)
  observaciones: string;
  detalles_plano: string;
  tecnico_nombre: string;
  tecnico_firma: string;
  revisa_nombre: string;
  revisa_firma: string;
  empresa_ejecuta: string;
  certificado_tipo: string;
  certificado_categoria: string;
}

const defaultMaterialItem = (index: number): MaterialInstaladoItem => ({
  id: `mat-${Date.now()}-${index}`,
  origen_material: "CINCO SAS",
  descripcion: "",
  cantidad: "1",
  tipo_unidad: "UNIDAD",
});

const initialFormData: FormCorrectivoEmergenciaData = {
  nombre_estacion: "",
  regional: "",
  departamento: "",
  direccion: "",
  tipo_estacion: "",
  tipo_sitio: "",
  site_owner: "",
  categoria_criticidad: "1. ALTA",
  responsable_1: null,
  responsable_2: null,
  numero_inc: "",
  numero_tas: "",
  fecha_inicio: "",
  fecha_fin: "",
  implica_exclusion: "NO",

  tipo_actividad: "CORRECTIVO",
  tipo_equipo_falla: "NO APLICA FALLA",
  marca: "",
  modelo: "",
  presenta_afectacion_servicios: "NO",
  reinstalacion: "N/A",
  cambio: "N/A",
  reparacion: "N/A",

  descripcion_falla: "",
  descripcion_solucion: "",
  descripcion_fallas_componentes: "",

  materiales: [defaultMaterialItem(1)],

  distancia_km: "",
  tiempo_desplazamiento: "",
  tipo_transporte: "VEHICULO 4X4",
  observacion_transporte: "",

  evidencias: [],

  observaciones: "",
  detalles_plano: "",
  tecnico_nombre: "",
  tecnico_firma: "",
  revisa_nombre: "",
  revisa_firma: "",
  empresa_ejecuta: "",
  certificado_tipo: "",
  certificado_categoria: "",
};

// Pasos con nombres cortos y limpios para la navegación
const stepsConfig: StepItem[] = [
  { id: "general", title: "Información General", shortTitle: "General" },
  {
    id: "actividad",
    title: "Información de Actividad",
    shortTitle: "Actividad",
  },
  {
    id: "diagnostico",
    title: "Falla y Solución",
    shortTitle: "Falla / Solución",
  },
  {
    id: "materiales",
    title: "Materiales Instalados",
    shortTitle: "Materiales",
  },
  {
    id: "transportes",
    title: "Transportes Especiales",
    shortTitle: "Transporte",
  },
  { id: "evidencias", title: "Evidencias Fotográficas", shortTitle: "Fotos" },
  { id: "cierre", title: "Observaciones y Firmas", shortTitle: "Cierre" },
];

interface FormCorrectivoEmergenciaSliderProps {
  categoriaInicial?: CategoriaActividad | null;
}

const FormCorrectivoEmergenciaSlider: React.FC<
  FormCorrectivoEmergenciaSliderProps
> = ({ categoriaInicial }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<FormCorrectivoEmergenciaData>(
    () => ({
      ...initialFormData,
      tipo_actividad:
        categoriaInicial === "emergencias" ? "EMERGENCIA" : "CORRECTIVO",
    }),
  );
  const { submit, isLoading } = useFormSubmit<SmuPayload>();
  // Cubre TODO el guardado (subida de fotos + POST): `isLoading` de
  // useFormSubmit solo está en true durante el POST.
  const [enviando, setEnviando] = useState(false);

  // `tipo_actividad` es de solo lectura: deriva del selector de categoría del
  // padre. Se ajusta durante el render (patrón "adjusting state when a prop
  // changes") en vez de un efecto, para no provocar renders en cascada:
  // https://react.dev/learn/you-might-not-need-an-effect
  const [categoriaPrevia, setCategoriaPrevia] = useState(categoriaInicial);
  if (categoriaInicial !== categoriaPrevia) {
    setCategoriaPrevia(categoriaInicial);
    if (categoriaInicial) {
      const nuevo =
        categoriaInicial === "emergencias" ? "EMERGENCIA" : "CORRECTIVO";
      setFormData((prev) =>
        prev.tipo_actividad !== nuevo
          ? { ...prev, tipo_actividad: nuevo }
          : prev,
      );
    }
  }

  // Genérico a propósito: el valor debe coincidir con el tipo del campo
  // (tsc falla en el llamado si se pasa un evento u objeto donde va un string).
  const updateField = <K extends keyof FormCorrectivoEmergenciaData>(
    field: K,
    value: FormCorrectivoEmergenciaData[K],
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Handlers para la tabla dinámica de materiales
  const handleAddMaterial = () => {
    setFormData((prev) => ({
      ...prev,
      materiales: [
        ...prev.materiales,
        defaultMaterialItem(prev.materiales.length + 1),
      ],
    }));
  };

  const handleRemoveMaterial = (id: string) => {
    if (formData.materiales.length <= 1) return;
    const eliminado = formData.materiales.find((m) => m.id === id);
    liberarPreviewUrl(eliminado?.foto_antes_preview);
    liberarPreviewUrl(eliminado?.foto_despues_preview);
    setFormData((prev) => ({
      ...prev,
      materiales: prev.materiales.filter((m) => m.id !== id),
    }));
  };

  const handleUpdateMaterial = (
    id: string,
    field: keyof MaterialInstaladoItem,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      materiales: prev.materiales.map((m) =>
        m.id === id ? { ...m, [field]: value } : m,
      ),
    }));
  };

  /**
   * Foto de la fila de un material (FOTO ANTES / FOTO DESPUÉS del Excel).
   * `FotoSlotCard` valida el archivo y avisa la baja con `onUpload(null)` +
   * `onRemove`, así que solo actuamos cuando hay archivo. La vista previa
   * anterior se revoca aquí (al eliminar ya la revoca el propio slot).
   */
  const handleMaterialFotoUpload = (
    id: string,
    parte: "antes" | "despues",
    file: File | null,
  ) => {
    if (!file) return;
    setFormData((prev) => ({
      ...prev,
      materiales: prev.materiales.map((m) => {
        if (m.id !== id) return m;
        const previa =
          parte === "antes" ? m.foto_antes_preview : m.foto_despues_preview;
        liberarPreviewUrl(previa);
        return parte === "antes"
          ? {
              ...m,
              foto_antes_preview: URL.createObjectURL(file),
              foto_antes_file: file,
            }
          : {
              ...m,
              foto_despues_preview: URL.createObjectURL(file),
              foto_despues_file: file,
            };
      }),
    }));
  };

  const handleMaterialFotoRemove = (id: string, parte: "antes" | "despues") => {
    setFormData((prev) => ({
      ...prev,
      materiales: prev.materiales.map((m) => {
        if (m.id !== id) return m;
        return parte === "antes"
          ? { ...m, foto_antes_preview: undefined, foto_antes_file: undefined }
          : {
              ...m,
              foto_despues_preview: undefined,
              foto_despues_file: undefined,
            };
      }),
    }));
  };

  // Las vistas previas blob: (evidencias y fotos de materiales) se liberan al
  // guardar (`reiniciarFormulario`) y también si el formulario se desmonta
  // antes: sin esto, cambiar de módulo deja objectURL colgados en memoria.
  const formDataRef = useRef(formData);
  useEffect(() => {
    formDataRef.current = formData;
  });
  useEffect(
    () => () => {
      liberarPreviews(formDataRef.current);
    },
    [],
  );

  /**
   * Tras un guardado exitoso el formulario queda vacío y en el paso 1, listo
   * para una nueva actividad; si no, el botón seguiría activo con los mismos
   * datos y un segundo clic duplicaría el registro.
   */
  const reiniciarFormulario = () => {
    liberarPreviews(formData);
    setFormData(clonarEstadoInicial(initialFormData));
    setCurrentStep(0);
  };

  const handleSubmit = async () => {
    // Un solo guardado en vuelo: si no, un segundo clic mientras se suben las
    // fotos (subirPendientes corre ANTES del POST) crearía la actividad dos veces.
    if (enviando) return;
    setEnviando(true);
    try {
      if (!formData.nombre_estacion.trim()) {
        toast.error("Ingresa el nombre de la estación.");
        return;
      }

      if (!formData.responsable_1?.cedula) {
        toast.error(
          "Selecciona el responsable de la actividad: la cédula es obligatoria.",
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

      const categoria: "correctivos" | "emergencias" =
        formData.tipo_actividad === "EMERGENCIA"
          ? "emergencias"
          : "correctivos";

      // Fase 3: las fotos se suben ANTES de crear la actividad (la API es
      // solo-POST, no hay PUT para adjuntarlas después).
      const pendientes: PendienteSubida[] = [];
      const payload = buildCorrectivoEmergenciaPayload(
        formData,
        categoria,
        pendientes,
      );
      await subirPendientes(pendientes);

      await submit(payload, {
        endpoint: SMU_ACTIVIDADES_ENDPOINT,
        method: "POST",
        onSuccess: (res) => {
          toast.success(
            `Actividad ${
              categoria === "emergencias" ? "de emergencia" : "correctiva"
            } guardada${res?.id ? ` (actividad #${res.id})` : ""}.`,
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

  // ── Handlers de Evidencias Fotográficas ──────────────────────────────────────
  const handleAddEvidencia = () => {
    const nueva: EvidenciaFotoItem = {
      id: `ev-${Date.now()}`,
      previewUrl: undefined,
      descripcion: "",
    };
    setFormData((prev) => ({
      ...prev,
      evidencias: [...prev.evidencias, nueva],
    }));
  };

  const handleRemoveEvidencia = (id: string) => {
    const ev = formData.evidencias.find((e) => e.id === id);
    liberarPreviewUrl(ev?.previewUrl);
    setFormData((prev) => ({
      ...prev,
      evidencias: prev.evidencias.filter((e) => e.id !== id),
    }));
  };

  const handleEvidenciaUpload = (id: string, file: File) => {
    const ev = formData.evidencias.find((item) => item.id === id);
    liberarPreviewUrl(ev?.previewUrl);
    const previewUrl = URL.createObjectURL(file);
    setFormData((prev) => ({
      ...prev,
      evidencias: prev.evidencias.map((item) =>
        item.id === id
          ? { ...item, previewUrl, file, nombre: file.name }
          : item,
      ),
    }));
  };

  /**
   * Baja de la foto de una evidencia: limpia vista previa, File y nombre
   * (ver `quitarFotoEvidencia`), conservando la fila y su descripción.
   */
  const handleEvidenciaRemove = (id: string) => {
    setFormData((prev) => ({
      ...prev,
      evidencias: quitarFotoEvidencia(prev.evidencias, id),
    }));
  };

  const handleEvidenciaDescripcion = (id: string, descripcion: string) => {
    setFormData((prev) => ({
      ...prev,
      evidencias: prev.evidencias.map((ev) =>
        ev.id === id ? { ...ev, descripcion } : ev,
      ),
    }));
  };

  const tecnicoNombreMostrado = formData.responsable_1
    ? `${formData.responsable_1.nombre} ${formData.responsable_1.apellido}`
    : formData.tecnico_nombre;

  return (
    <FormStepSlider
      steps={stepsConfig}
      currentStep={currentStep}
      onStepChange={setCurrentStep}
      onSubmit={handleSubmit}
      submitLabel="Guardar Actividad"
      isSubmitting={isLoading || enviando}
    >
      {/* ── PASO 1: Información General ── */}
      {currentStep === 0 && (
        <div className="space-y-6">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              1. Información General de la Estación y Actividad
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Complete los datos del sitio, números de control y fechas de
              ejecución.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Columna Izquierda */}
            <div className="space-y-4">
              <div>
                <Label>Nombre de Estación</Label>
                <Input
                  type="text"
                  value={formData.nombre_estacion}
                  onChange={(e) =>
                    updateField("nombre_estacion", e.target.value)
                  }
                  placeholder="Ingrese nombre de la estación"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Regional</Label>
                  <Input
                    type="text"
                    value={formData.regional}
                    onChange={(e) => updateField("regional", e.target.value)}
                    placeholder="Regional"
                  />
                </div>
                <div>
                  <Label>Departamento</Label>
                  <Input
                    type="text"
                    value={formData.departamento}
                    onChange={(e) =>
                      updateField("departamento", e.target.value)
                    }
                    placeholder="Departamento"
                  />
                </div>
              </div>

              <div>
                <Label>Dirección</Label>
                <Input
                  type="text"
                  value={formData.direccion}
                  onChange={(e) => updateField("direccion", e.target.value)}
                  placeholder="Dirección del sitio"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Tipo de Estación</Label>
                  <Input
                    type="text"
                    value={formData.tipo_estacion}
                    onChange={(e) =>
                      updateField("tipo_estacion", e.target.value)
                    }
                    placeholder="Ej: TERRAZA, TORRE"
                  />
                </div>
                <div>
                  <Label>Tipo de Sitio</Label>
                  <Input
                    type="text"
                    value={formData.tipo_sitio}
                    onChange={(e) => updateField("tipo_sitio", e.target.value)}
                    placeholder="Ej: URBANO, RURAL"
                  />
                </div>
              </div>

              <div>
                <Label>Site Owner / Propietario</Label>
                <Input
                  type="text"
                  value={formData.site_owner}
                  onChange={(e) => updateField("site_owner", e.target.value)}
                  placeholder="Nombre del propietario del predio"
                />
              </div>
            </div>

            {/* Columna Derecha */}
            <div className="space-y-4">
              <div>
                <Label>Categoría de Criticidad</Label>
                <Select
                  options={OPCIONES_CATEGORIA_CRITICIDAD}
                  value={formData.categoria_criticidad}
                  onChange={(val) => updateField("categoria_criticidad", val)}
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>No. INC (Incidente)</Label>
                  <Input
                    type="text"
                    value={formData.numero_inc}
                    onChange={(e) => updateField("numero_inc", e.target.value)}
                    placeholder="No. Incidente"
                  />
                </div>
                <div>
                  <Label>No. TAS</Label>
                  <Input
                    type="text"
                    value={formData.numero_tas}
                    onChange={(e) => updateField("numero_tas", e.target.value)}
                    placeholder="No. TAS"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label>Fecha Inicio / Ejecución</Label>
                  <Input
                    type="datetime-local"
                    value={formData.fecha_inicio}
                    onChange={(e) =>
                      updateField("fecha_inicio", e.target.value)
                    }
                  />
                </div>
                <div>
                  <Label>Fecha Fin Actividad</Label>
                  <Input
                    type="datetime-local"
                    value={formData.fecha_fin}
                    onChange={(e) => updateField("fecha_fin", e.target.value)}
                  />
                </div>
              </div>

              <div>
                <Label>¿Implica Exclusión?</Label>
                <Select
                  options={OPCIONES_SI_NO}
                  value={formData.implica_exclusion}
                  onChange={(val) => updateField("implica_exclusion", val)}
                />
              </div>

              {/* Búsqueda de Técnicos */}
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <EmployeeSearchInput
                  label="Responsable Técnico 1"
                  value={formData.responsable_1}
                  onChange={(emp) => updateField("responsable_1", emp)}
                  placeholder="Buscar técnico principal..."
                />
                <EmployeeSearchInput
                  label="Responsable Técnico 2 (Auxiliar)"
                  value={formData.responsable_2}
                  onChange={(emp) => updateField("responsable_2", emp)}
                  placeholder="Buscar técnico auxiliar..."
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 2: Información de la Actividad ── */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              2. Información Detallada de la Actividad
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Indique el tipo de equipo intervenido, alcance de la acción y
              afectación de servicios.
            </p>
          </div>

          <div className="space-y-5 rounded-2xl border border-gray-200 bg-gray-50/50 p-5 dark:border-gray-800 dark:bg-white/[0.02]">
            {/* Tipo de Actividad — derivado del selector padre, solo lectura */}
            <div className="flex items-center gap-3">
              <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                Tipo de Actividad:
              </span>
              <span
                className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ${
                  formData.tipo_actividad === "EMERGENCIA"
                    ? "bg-error-50 text-error-600 dark:bg-error-500/10 dark:text-error-400"
                    : "bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400"
                }`}
              >
                {formData.tipo_actividad === "EMERGENCIA"
                  ? " Emergencia"
                  : " Correctivo"}
              </span>
            </div>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
              <div>
                <Label>Tipo de Equipo en Falla</Label>
                <Select
                  options={OPCIONES_TIPO_EQUIPO_FALLA}
                  value={formData.tipo_equipo_falla}
                  onChange={(val) => updateField("tipo_equipo_falla", val)}
                />
              </div>

              <div>
                <Label>Marca del Equipo</Label>
                <Input
                  type="text"
                  value={formData.marca}
                  onChange={(e) => updateField("marca", e.target.value)}
                  placeholder="Marca del equipo intervenido"
                />
              </div>

              <div>
                <Label>Modelo del Equipo</Label>
                <Input
                  type="text"
                  value={formData.modelo}
                  onChange={(e) => updateField("modelo", e.target.value)}
                  placeholder="Modelo del equipo"
                />
              </div>
            </div>
          </div>

          {/* Matriz de Acciones y Afectación */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
            <h5 className="mb-4 text-xs font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
              Alcance de la Intervención y Afectación
            </h5>

            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <Label>¿Afectación de Servicios?</Label>
                <Select
                  options={OPCIONES_SI_NO}
                  value={formData.presenta_afectacion_servicios}
                  onChange={(val) =>
                    updateField("presenta_afectacion_servicios", val)
                  }
                />
              </div>

              <div>
                <Label>Reinstalación</Label>
                <Select
                  options={OPCIONES_SI_NO_NA}
                  value={formData.reinstalacion}
                  onChange={(val) => updateField("reinstalacion", val)}
                />
              </div>

              <div>
                <Label>Cambio</Label>
                <Select
                  options={OPCIONES_SI_NO_NA}
                  value={formData.cambio}
                  onChange={(val) => updateField("cambio", val)}
                />
              </div>

              <div>
                <Label>Reparación</Label>
                <Select
                  options={OPCIONES_SI_NO_NA}
                  value={formData.reparacion}
                  onChange={(val) => updateField("reparacion", val)}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 3: Descripción de Falla y Solución ── */}
      {currentStep === 2 && (
        <div className="space-y-6">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              3 y 4. Diagnóstico de la Falla y Solución Ejecutada
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Detalle el origen de la anomalía y el procedimiento técnico
              llevado a cabo en sitio.
            </p>
          </div>

          <div className="space-y-5">
            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
              <div className="mb-2 flex items-center gap-2 text-amber-600 dark:text-amber-400">
                <AlertTriangle className="h-4 w-4" />
                <Label className="!mb-0 font-semibold">
                  3. Descripción de la Falla
                </Label>
              </div>
              <TextArea
                rows={4}
                value={formData.descripcion_falla}
                onChange={(e) =>
                  updateField("descripcion_falla", e.target.value)
                }
                placeholder="Describa de manera detallada los síntomas, origen o condición de falla encontrada en la estación..."
              />
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
              <div className="mb-2 flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                <Wrench className="h-4 w-4" />
                <Label className="!mb-0 font-semibold">
                  4. Descripción de la Solución
                </Label>
              </div>
              <TextArea
                rows={4}
                value={formData.descripcion_solucion}
                onChange={(e) =>
                  updateField("descripcion_solucion", e.target.value)
                }
                placeholder="Detalle todas las acciones correctivas realizadas (ej: tendido de cable, ajuste de barrajes, reemplazo de componentes, etc.)..."
              />
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
              <Label className="font-semibold">
                Descripción de Fallas en Componentes (Opcional)
              </Label>
              <TextArea
                rows={2}
                value={formData.descripcion_fallas_componentes}
                onChange={(e) =>
                  updateField("descripcion_fallas_componentes", e.target.value)
                }
                placeholder="Detalles complementarios sobre componentes específicos si aplica..."
              />
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 4: Materiales Instalados ── */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
                5. Materiales e Insumos Instalados
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Registre los materiales utilizados durante la intervención:
                origen, cantidad consumida y sus fotos antes y después.
              </p>
            </div>
            <button
              type="button"
              onClick={handleAddMaterial}
              className="bg-brand-500 hover:bg-brand-600 inline-flex items-center gap-1.5 self-start rounded-xl px-3.5 py-2 text-xs font-medium text-white shadow-sm transition sm:self-auto"
            >
              <Plus className="h-3.5 w-3.5" />
              Agregar Material
            </button>
          </div>

          <div className="space-y-3">
            {formData.materiales.map((material, idx) => (
              <div
                key={material.id}
                className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition-all hover:border-gray-300 dark:border-gray-800 dark:bg-white/[0.02]"
              >
                <div className="mb-3 flex items-center justify-between border-b border-gray-100 pb-3 dark:border-gray-800">
                  <div className="flex items-center gap-2">
                    <span className="bg-brand-100 text-brand-700 dark:bg-brand-900/40 dark:text-brand-300 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold">
                      {idx + 1}
                    </span>
                    <span className="text-xs font-semibold text-gray-700 dark:text-gray-200">
                      Ítem #{idx + 1}
                    </span>
                  </div>

                  {formData.materiales.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveMaterial(material.id)}
                      className="inline-flex items-center gap-1 text-xs text-red-500 transition hover:text-red-700"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Eliminar
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 gap-3 sm:grid-cols-12">
                  <div className="sm:col-span-4">
                    <Label className="text-[11px]">
                      ¿Material comprado por operario / origen?
                    </Label>
                    <Select
                      options={OPCIONES_ORIGEN_MATERIAL}
                      value={material.origen_material}
                      onChange={(val) =>
                        handleUpdateMaterial(
                          material.id,
                          "origen_material",
                          val,
                        )
                      }
                    />
                  </div>

                  <div className="sm:col-span-5">
                    <Label className="text-[11px]">
                      Descripción del Material
                    </Label>
                    <Input
                      type="text"
                      value={material.descripcion}
                      onChange={(e) =>
                        handleUpdateMaterial(
                          material.id,
                          "descripcion",
                          e.target.value,
                        )
                      }
                      placeholder="Ej: CABLE ALUMINIO #4, ABRAZADERA METAL, etc."
                    />
                  </div>

                  <div className="sm:col-span-1">
                    <Label className="text-[11px]">Cantidad</Label>
                    <Input
                      type="number"
                      value={material.cantidad}
                      onChange={(e) =>
                        handleUpdateMaterial(
                          material.id,
                          "cantidad",
                          e.target.value,
                        )
                      }
                      placeholder="1"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <Label className="text-[11px]">Unidad de Medida</Label>
                    <Select
                      options={OPCIONES_UNIDAD_MEDIDA}
                      value={material.tipo_unidad}
                      onChange={(val) =>
                        handleUpdateMaterial(material.id, "tipo_unidad", val)
                      }
                    />
                  </div>
                </div>

                {/* Fotos de la fila: columnas FOTO ANTES y FOTO DESPUÉS del
                    bloque 4 del Excel (opcionales, se suben al guardar). */}
                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <div>
                    <Label className="text-[11px]">
                      Foto del material · antes (opcional)
                    </Label>
                    <FotoSlotCard
                      index={idx + 1}
                      titulo="Foto antes"
                      inputId={`material-antes-${material.id}`}
                      previewUrl={material.foto_antes_preview}
                      onUpload={(file) =>
                        handleMaterialFotoUpload(material.id, "antes", file)
                      }
                      onRemove={() =>
                        handleMaterialFotoRemove(material.id, "antes")
                      }
                    />
                  </div>
                  <div>
                    <Label className="text-[11px]">
                      Foto del material · después (opcional)
                    </Label>
                    <FotoSlotCard
                      index={idx + 1}
                      titulo="Foto después"
                      inputId={`material-despues-${material.id}`}
                      previewUrl={material.foto_despues_preview}
                      onUpload={(file) =>
                        handleMaterialFotoUpload(material.id, "despues", file)
                      }
                      onRemove={() =>
                        handleMaterialFotoRemove(material.id, "despues")
                      }
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── PASO 5: Transportes Especiales ── */}
      {currentStep === 4 && (
        <div className="space-y-6">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              9. Transportes Especiales y Desplazamientos
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Información de tiempos de traslado, distancia recorrida y medio de
              movilización.
            </p>
          </div>

          <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
            <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
              <div>
                <Label>Distancia en KM</Label>
                <Input
                  type="text"
                  value={formData.distancia_km}
                  onChange={(e) => updateField("distancia_km", e.target.value)}
                  placeholder="Ej: 7.3"
                />
              </div>

              <div>
                <Label>Tiempo de Desplazamiento</Label>
                <Input
                  type="text"
                  value={formData.tiempo_desplazamiento}
                  onChange={(e) =>
                    updateField("tiempo_desplazamiento", e.target.value)
                  }
                  placeholder="Ej: 25 min, 1 hora"
                />
              </div>

              <div>
                <Label>Tipo de Transporte</Label>
                <Select
                  options={OPCIONES_TIPO_TRANSPORTE}
                  value={formData.tipo_transporte}
                  onChange={(val) => updateField("tipo_transporte", val)}
                />
              </div>
            </div>

            <div className="mt-4">
              <Label>Observación de Transporte / Ruta</Label>
              <TextArea
                rows={2}
                value={formData.observacion_transporte}
                onChange={(e) =>
                  updateField("observacion_transporte", e.target.value)
                }
                placeholder="Observaciones de la vía, carretera, estado del acceso, etc."
              />
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 6: Evidencias Fotográficas ── */}
      {currentStep === 5 && (
        <div className="space-y-6">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              6. Evidencias Fotográficas
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Agregue las fotografías que evidencian el trabajo realizado. Cada
              imagen debe incluir una descripción del hallazgo o detalle
              capturado.
            </p>
          </div>

          {/* Listado de evidencias */}
          {formData.evidencias.length > 0 && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {formData.evidencias.map((ev, idx) => (
                <div key={ev.id} className="relative">
                  {/* Botón eliminar evidencia */}
                  <button
                    type="button"
                    onClick={() => handleRemoveEvidencia(ev.id)}
                    className="bg-error-500 hover:bg-error-600 absolute -top-2 -right-2 z-10 flex h-6 w-6 items-center justify-center rounded-full text-white shadow-md transition-all"
                    title="Eliminar evidencia"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>

                  <FotoSlotWithDescripcion
                    index={idx + 1}
                    titulo={`Evidencia ${idx + 1}`}
                    previewUrl={ev.previewUrl}
                    inputId={`evidencia-input-${ev.id}`}
                    onUpload={(file) =>
                      file && handleEvidenciaUpload(ev.id, file)
                    }
                    onRemove={() => handleEvidenciaRemove(ev.id)}
                    descripcion={ev.descripcion}
                    onDescripcionChange={(val) =>
                      handleEvidenciaDescripcion(ev.id, val)
                    }
                    descripcionPlaceholder="Describe el hallazgo o detalle de la foto..."
                    descripcionLabel="Descripción de la evidencia"
                  />
                </div>
              ))}
            </div>
          )}

          {/* Estado vacío */}
          {formData.evidencias.length === 0 && (
            <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-gray-200 bg-gray-50/50 py-12 text-center dark:border-gray-800 dark:bg-white/[0.01]">
              <div className="bg-brand-50 text-brand-500 dark:bg-brand-500/10 dark:text-brand-400 flex h-12 w-12 items-center justify-center rounded-full">
                <Camera className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Aún no hay evidencias fotográficas
                </p>
                <p className="text-xs text-gray-400 dark:text-gray-500">
                  Haga clic en &quot;Agregar Evidencia&quot; para subir la
                  primera foto.
                </p>
              </div>
            </div>
          )}

          {/* Botón agregar */}
          <button
            type="button"
            onClick={handleAddEvidencia}
            className="border-brand-300 bg-brand-50/30 text-brand-600 hover:border-brand-400 hover:bg-brand-50 dark:border-brand-700 dark:bg-brand-500/5 dark:text-brand-400 dark:hover:border-brand-500 dark:hover:bg-brand-500/10 flex w-full items-center justify-center gap-2 rounded-xl border-2 border-dashed py-3 text-sm font-medium transition-all"
          >
            <Plus className="h-4 w-4" />
            Agregar Evidencia Fotográfica
          </button>

          {formData.evidencias.length > 0 && (
            <p className="text-center text-xs text-gray-400 dark:text-gray-500">
              {formData.evidencias.length} evidencia
              {formData.evidencias.length !== 1 ? "s" : ""} agregada
              {formData.evidencias.length !== 1 ? "s" : ""}
            </p>
          )}
        </div>
      )}

      {/* ── PASO 7: Observaciones y Cierre (Firmas / Certificado) ── */}
      {currentStep === 6 && (
        <div className="space-y-6">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              7, 8 y 10. Observaciones, Plano y Cierre de la Actividad
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Observaciones generales, detalles del plano y datos de validación
              técnica.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
              <Label className="font-semibold">
                7. Observaciones de la Actividad
              </Label>
              <TextArea
                rows={3}
                value={formData.observaciones}
                onChange={(e) => updateField("observaciones", e.target.value)}
                placeholder="Observaciones finales, pendientes o aclaraciones técnicas..."
              />
            </div>

            <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
              <Label className="font-semibold">
                8. Detalles del Plano / Croquis
              </Label>
              <TextArea
                rows={3}
                value={formData.detalles_plano}
                onChange={(e) => updateField("detalles_plano", e.target.value)}
                placeholder="Descripción del esquema técnico, barrajes, cables y trazado..."
              />
            </div>
          </div>

          {/* Firmas y Validación Técnica */}
          <div className="rounded-2xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/[0.02]">
            <h5 className="mb-4 text-xs font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
              10. Firmas y Validación Técnica
            </h5>

            <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
              {/* Técnico Ejecutor */}
              <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/[0.01]">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-200">
                  <PenTool className="text-brand-500 h-3.5 w-3.5" />
                  Técnico Ejecutor
                </div>

                <div>
                  <Label className="text-[11px]">Nombre del Técnico</Label>
                  <Input
                    type="text"
                    value={tecnicoNombreMostrado}
                    onChange={(e) =>
                      updateField("tecnico_nombre", e.target.value)
                    }
                    placeholder="Nombre completo del técnico"
                  />
                </div>

                <div>
                  <Label className="text-[11px]">Empresa quien ejecuta</Label>
                  <Input
                    type="text"
                    value={formData.empresa_ejecuta}
                    onChange={(e) =>
                      updateField("empresa_ejecuta", e.target.value)
                    }
                    placeholder="Nombre de la empresa ejecutora"
                  />
                </div>
              </div>

              {/* Responsable de Revisión */}
              <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/[0.01]">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-gray-700 dark:text-gray-200">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-500" />
                  Revisión / Coordinación
                </div>

                <div>
                  <Label className="text-[11px]">Nombre de quien revisa</Label>
                  <Input
                    type="text"
                    value={formData.revisa_nombre}
                    onChange={(e) =>
                      updateField("revisa_nombre", e.target.value)
                    }
                    placeholder="Nombre de quien revisa o aprueba"
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <Label className="text-[11px]">Tipo Certificado</Label>
                    <Input
                      type="text"
                      value={formData.certificado_tipo}
                      onChange={(e) =>
                        updateField("certificado_tipo", e.target.value)
                      }
                      placeholder="Ej: TARJETA CONTE"
                    />
                  </div>
                  <div>
                    <Label className="text-[11px]">Categoría</Label>
                    <Input
                      type="text"
                      value={formData.certificado_categoria}
                      onChange={(e) =>
                        updateField("certificado_categoria", e.target.value)
                      }
                      placeholder="Ej: TE-1, TE-6"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </FormStepSlider>
  );
};

export default FormCorrectivoEmergenciaSlider;
