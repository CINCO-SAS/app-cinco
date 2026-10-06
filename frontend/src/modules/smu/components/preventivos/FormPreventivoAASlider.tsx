"use client";

import React, { useState } from "react";
import FormStepSlider, { StepItem } from "../common/FormStepSlider";
import Label from "@/components/form/Label";
import Input from "@/components/form/input/InputField";
import TextArea from "@/components/form/input/TextArea";
import Select from "@/components/form/Select";
import EmployeeSearchInput from "@/components/form/EmployeeSearchInput";
import { Empleado } from "@/types/empleado";
import {
  CheckCheck,
  Camera,
  Image as ImageIcon,
  Upload,
  FileCheck2,
  ShieldCheck,
  PenTool,
} from "lucide-react";
import SectionHeader from "../common/SectionHeader";
import AddItemButton from "../common/AddItemButton";
import DynamicItemCard from "../common/DynamicItemCard";
import FotoSlotCard from "@/components/form/input/FotoSlotCard";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import ChecklistItem, { ChecklistEstado } from "../common/ChecklistItem";
import { toast } from "sonner";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { liberarPreviewUrl } from "@/lib/fotos";
import type { ClaveAccionAA } from "@/modules/smu/constants";
import {
  buildPreventivoAAPayload,
  subirPendientes,
  validarFechasEncabezado,
  SMU_ACTIVIDADES_ENDPOINT,
  type PendienteSubida,
  type SmuPayload,
} from "@/services/smu.service";
import { manejarErrorGuardado, toastErrorActividad } from "@/modules/smu/errors";
import { clonarEstadoInicial, liberarPreviews } from "@/modules/smu/reinicio";

// Opciones estandarizadas para los dropdowns
const OPCIONES_SI_NO_NA = [
  { value: "SÍ", label: "SÍ" },
  { value: "NO", label: "NO" },
  { value: "N/A", label: "N/A" },
];

const OPCIONES_ESTADO_DRENAJES = [
  { value: "BUENO", label: "BUENO" },
  { value: "REGULAR", label: "REGULAR" },
  { value: "MALO", label: "MALO" },
  { value: "N/A", label: "N/A" },
];

// Configuración de las 15 Casillas Fotográficas
export interface FotoSlotConfig {
  id: string;
  titulo: string;
  descripcion?: string;
}

export const FOTO_SLOTS_AA: FotoSlotConfig[] = [
  {
    id: "condensadora_pos_mantenimiento",
    titulo: "Condensadora Pos Mantenimiento",
  },
  {
    id: "evaporadora_pos_mantenimiento",
    titulo: "Evaporadora Pos Mantenimiento",
  },
  { id: "filtros_pos_mantenimiento", titulo: "Filtros Pos Mantenimiento" },
  {
    id: "panoramica_unidad_condensadora",
    titulo: "Panorámica Unidad Condensadora",
  },
  {
    id: "panoramica_unidad_manejadora",
    titulo: "Panorámica Unidad Manejadora",
  },
  { id: "panoramica_compresor", titulo: "Panorámica Compresor" },
  {
    id: "panoramica_aire_acondicionado",
    titulo: "Panorámica del Aire Acondicionado",
  },
  { id: "motor_aspa_condensadora", titulo: "Motor y Aspa Condensadora" },
  { id: "foto_temp_aire_entrada", titulo: "Temperatura Aire de Entrada" },
  { id: "foto_temp_aire_salida", titulo: "Temperatura Aire de Salida" },
  { id: "foto_temp_salon", titulo: "Temperatura Salón" },
  { id: "foto_termostato", titulo: "Termostato" },
  {
    id: "ajustes_mecanicos_electricos_1",
    titulo: "Ajustes Mecánicos y Eléctricos (1)",
  },
  {
    id: "ajustes_mecanicos_electricos_2",
    titulo: "Ajustes Mecánicos y Eléctricos (2)",
  },
  { id: "foto_serial_elemento", titulo: "Serial del Elemento" },
];

// Estructura de cada Compresor
export interface CompresorData {
  id: string;
  marca: string;
  serial: string;
  tipo: string;
  refrigerante: string;
  modelo: string;
  aislamiento_electrico: string;
  presion_succion: string;
  presion_descarga: string;
  nivel_aceite: string;
  vl1: string;
  vl2: string;
  vl3: string;
  ampl1: string;
  ampl2: string;
  ampl3: string;
}

// Estructura de cada Unidad Condensadora
export interface UnidadCondensadoraData {
  id: string;
  marca: string;
  modelo: string;
  serial: string;
  temperatura_entrada: string;
  temperatura_salida: string;
  diametro_eje: string;
  diametro_aspas: string;
}

// Estructura de cada Unidad Manejadora
export interface UnidadManejadoraData {
  id: string;
  marca: string;
  modelo: string;
  tipo: string;
  tipo_filtro: string;
  tipo_correa: string;
  marca_motor: string;
  alimentacion_ac: string;
  voltaje_motor: string;
  corriente_motor: string;
  aislamiento: string;
  serial_motor: string;
  dimensiones_blower: string;
}

// Estructura de la Lista de Chequeo
// ChecklistEstado se importa desde common/ChecklistItem
export type { ChecklistEstado };

// Estructura de Acciones y Mantenimiento Ejecutado (AA 1, AA 2...)
// Las claves tri-estado viven en `CLAVES_ACCIONES_AA` (../constants.ts) y la
// tipografía se deriva de esa lista: así un campo nuevo no puede quedar fuera
// del payload que arma smu.service.ts, ni faltar en los valores por defecto.
export type AccionesMantenimientoAAData = {
  id: string;
} & Record<ClaveAccionAA, string>;

// Estructura de Certificado y Soporte Técnico
export interface CertificadoTecnicoData {
  tipo_certificado: string;
  categoria_certificado: string;
  foto_certificado_preview?: string;
  foto_certificado_file?: File;
  foto_sitio_preview?: string;
  foto_sitio_file?: File;
}

export interface PreventivoAAFormData {
  // Paso 1: Información General
  nombre_estacion: string;
  departamento: string;
  direccion: string;
  tipo_estacion: string;
  site_owner: string;
  responsable_1: Empleado | null;
  responsable_2: Empleado | null;
  codigo_ot: string;
  fecha_inicio: string;
  fecha_fin: string;

  // Paso 2: Datos Generales Aire Acondicionado
  marca: string;
  modelo: string;
  serial: string;
  id_activo: string;
  tipo_aire: string;
  alimentacion_ac: string;
  voltaje_entrada: string;
  corriente: string;
  capacidad_btu: string;
  gestion_remota_ip: string;
  cantidad_compresores: string;
  temp_cuarto: string;
  temp_entrada: string;
  temp_salida: string;
  temp_display: string;
  ajuste_termostato: string;
  temp_termostato_pos_ajuste: string;

  // Paso 3: Compresores y Unidades Condensadoras (Dinámicos)
  compresores: CompresorData[];
  condensadoras: UnidadCondensadoraData[];

  // Paso 4: Unidades Manejadoras (Dinámicas)
  manejadoras: UnidadManejadoraData[];

  // Paso 5: Lista de Chequeo (39 Puntos)
  checklist: Record<number, ChecklistEstado>;

  // Paso 6: Acciones y Mantenimiento Ejecutado
  acciones_mantenimiento: AccionesMantenimientoAAData[];
  acciones_observaciones: string;

  // Paso 7: Anexos Fotográficos (15 Fotos)
  fotos: Record<string, { file?: File; previewUrl?: string; nombre?: string }>;
  /**
   * Descripción escrita por el técnico para cada foto del paso 7: es el
   * título que encabeza su caja en el Excel (`rotulo_evidencia`).
   * Va aparte de `fotos` para que teclear antes de subir la foto no cuente
   * como foto cargada ni se pierda al reemplazarla.
   */
  fotos_descripciones: Record<string, string>;

  // Paso 8: Plan de Mejora, Firmas y Certificaciones
  plan_mejora: string;
  tecnico_nombre: string;
  tecnico_firma: string;
  reviso_nombre: string;
  reviso_firma: string;
  empresa: string;
  certificado: CertificadoTecnicoData;
}

export const CHECKLIST_ITEMS_AA = [
  {
    item_numero: 1,
    parametro: "La fijación de las unidades condensadoras es la adecuada",
  },
  {
    item_numero: 2,
    parametro: "La fijación de las unidades manejadoras es la adecuada",
  },
  {
    item_numero: 3,
    parametro: "El anclaje y fijación de tuberías es el adecuado",
  },
  {
    item_numero: 4,
    parametro:
      "Las unidades condensadoras y manejadoras se encuentran en buenas condiciones físicas.",
  },
  { item_numero: 5, parametro: "Los manuales se encuentran con las unidades" },
  {
    item_numero: 6,
    parametro:
      "Se encuentra el control remoto de las unidades (Cuando Aplique)",
  },
  {
    item_numero: 7,
    parametro:
      "Serpentín de unidades condensadoras están limpios y en buenas condiciones",
  },
  {
    item_numero: 8,
    parametro:
      "Buena circulación de aire natural en las unidades condensadoras",
  },
  {
    item_numero: 9,
    parametro: "Existen Fugas de aire acondicionado en el cuarto",
  },
  {
    item_numero: 10,
    parametro:
      "Las tuberías de conexión entre las unidades condensadoras y manejadoras no presentan signos de maltrato, golpes, fugas de refrigerante, o signos de óxido o corrosión",
  },
  {
    item_numero: 11,
    parametro:
      "Rejilla de control de dirección de aire frío funcional y en buen estado",
  },
  {
    item_numero: 12,
    parametro:
      "Chasis de las unidades condensadora o manejadora está libre de óxido o corrosión",
  },
  {
    item_numero: 13,
    parametro:
      "El tubo de drenaje del agua condensadora se encuentra libre de obstrucciones.",
  },
  {
    item_numero: 14,
    parametro: "Las conexiones eléctricas se encuentran en buenas condiciones",
  },
  {
    item_numero: 15,
    parametro:
      "Unidad Condensadoras funcionan adecuadamente (sin ruidos o vibraciones extrañas)",
  },
  {
    item_numero: 16,
    parametro:
      "Unidad Manejadora funcionan adecuadamente (sin ruidos o vibraciones extrañas)",
  },
  {
    item_numero: 17,
    parametro:
      "Los Elementos Electrónicos de Control (Pulsadores, Selectores, Contactores, Relés) funcionan adecuadamente.",
  },
  {
    item_numero: 18,
    parametro:
      "El estado de Lubricación y Rodamientos de las unidades es el adecuado.",
  },
  {
    item_numero: 19,
    parametro: "El estado de los ejes y chumaceras es el adecuado.",
  },
  {
    item_numero: 20,
    parametro:
      "La Tarjeta de Control de Aire Acondicionado opera adecuadamente.",
  },
  {
    item_numero: 21,
    parametro:
      "Se presentan alarmas en las unidades del aire acondicionado (Sonora, Visual, etc.)",
  },
  {
    item_numero: 22,
    parametro: "Se presentan fugas de Refrigerante en serpentines y tuberías.",
  },
  { item_numero: 23, parametro: "La válvula Solenoide opera adecuadamente." },
  {
    item_numero: 24,
    parametro: "Los Filtros de Secado se encuentran operando adecuadamente.",
  },
  {
    item_numero: 25,
    parametro: "El Aislamiento térmico se encuentra en buenas condiciones.",
  },
  {
    item_numero: 26,
    parametro:
      "Nivel de enfriamiento Adecuado (Menor a 4°C En Rejillas de Salida)",
  },
  {
    item_numero: 27,
    parametro:
      "Reinicio automático (con corte de energía se reinicia la operación)",
  },
  {
    item_numero: 28,
    parametro: "Se garantiza la distribución de aire frío por todo el cuarto",
  },
  {
    item_numero: 29,
    parametro:
      "El display se encuentra en perfectas condiciones y no presenta alarmas activas o códigos de error en el display",
  },
  {
    item_numero: 30,
    parametro:
      "El Chasis del aire acondicionado está debidamente puesto a tierra (Unidad Condensadora y Unidad Manejadora)",
  },
  {
    item_numero: 31,
    parametro:
      "Sistema de potencia y control de los aires acondicionados está puesto a tierra de forma adecuada",
  },
  {
    item_numero: 32,
    parametro: "Ductería del aire acondicionado en buen estado.",
  },
  {
    item_numero: 33,
    parametro:
      "Dimensionamiento de las protecciones Eléctricas de Equipos (Manejadora-Condensadora) es el adecuado y se encuentran en buen estado.",
  },
  { item_numero: 34, parametro: "Correas Manejadoras en buen estado." },
  {
    item_numero: 35,
    parametro: "Gestión Remota (RTU) funciona adecuadamente.",
  },
  {
    item_numero: 36,
    parametro:
      "Aspa del Ventilador se encuentra en buen estado y funciona adecuadamente.",
  },
  {
    item_numero: 37,
    parametro:
      "Se requiere reforzar la seguridad del Equipo (Implementar Rejillas).",
  },
  {
    item_numero: 38,
    parametro: "Drenaje funciona adecuadamente y se encuentra en buen estado.",
  },
  { item_numero: 39, parametro: "Equipo requiere cambio por obsolescencia" },
];

const defaultCompresor = (index: number): CompresorData => ({
  id: `comp-${Date.now()}-${index}`,
  marca: "",
  serial: "",
  tipo: "",
  refrigerante: "",
  modelo: "",
  aislamiento_electrico: "",
  presion_succion: "",
  presion_descarga: "",
  nivel_aceite: "",
  vl1: "",
  vl2: "",
  vl3: "",
  ampl1: "",
  ampl2: "",
  ampl3: "",
});

const defaultCondensadora = (index: number): UnidadCondensadoraData => ({
  id: `cond-${Date.now()}-${index}`,
  marca: "",
  modelo: "",
  serial: "",
  temperatura_entrada: "",
  temperatura_salida: "",
  diametro_eje: "",
  diametro_aspas: "",
});

const defaultManejadora = (index: number): UnidadManejadoraData => ({
  id: `manej-${Date.now()}-${index}`,
  marca: "",
  modelo: "",
  tipo: "",
  tipo_filtro: "",
  tipo_correa: "",
  marca_motor: "",
  alimentacion_ac: "",
  voltaje_motor: "",
  corriente_motor: "",
  aislamiento: "",
  serial_motor: "",
  dimensiones_blower: "",
});

const defaultAccionMantenimiento = (
  index: number,
): AccionesMantenimientoAAData => ({
  id: `accion-${Date.now()}-${index}`,
  limpieza_serpentines: "SÍ",
  ajuste_elementos_control: "SÍ",
  adicion_refrigerante: "N/A",
  estado_drenajes: "BUENO",
  lubricacion_componentes: "SÍ",
  cambio_filtros_secado: "NO",
  alineacion_poleas: "NO",
  cambio_componentes_electronicos: "NO",
  cambio_compresor: "NO",
  cambio_correas_filtros: "NO",
  otras_reparaciones: "NO",
});

const initialChecklist = CHECKLIST_ITEMS_AA.reduce<
  Record<number, ChecklistEstado>
>((acc, item) => {
  acc[item.item_numero] = "Si";
  return acc;
}, {});

const initialFormData: PreventivoAAFormData = {
  // Paso 1
  nombre_estacion: "",
  departamento: "",
  direccion: "",
  tipo_estacion: "",
  site_owner: "",
  responsable_1: null,
  responsable_2: null,
  codigo_ot: "",
  fecha_inicio: "",
  fecha_fin: "",

  // Paso 2
  marca: "",
  modelo: "",
  serial: "",
  id_activo: "",
  tipo_aire: "",
  alimentacion_ac: "",
  voltaje_entrada: "",
  corriente: "",
  capacidad_btu: "",
  gestion_remota_ip: "",
  cantidad_compresores: "",
  temp_cuarto: "",
  temp_entrada: "",
  temp_salida: "",
  temp_display: "",
  ajuste_termostato: "",
  temp_termostato_pos_ajuste: "",

  // Paso 3
  compresores: [defaultCompresor(1)],
  condensadoras: [defaultCondensadora(1)],

  // Paso 4
  manejadoras: [defaultManejadora(1)],

  // Paso 5
  checklist: initialChecklist,

  // Paso 6
  acciones_mantenimiento: [defaultAccionMantenimiento(1)],
  acciones_observaciones: "",

  // Paso 7
  fotos: {},
  fotos_descripciones: {},

  // Paso 8
  plan_mejora: "",
  tecnico_nombre: "",
  tecnico_firma: "",
  reviso_nombre: "",
  reviso_firma: "",
  empresa: "",
  certificado: {
    tipo_certificado: "",
    categoria_certificado: "",
    foto_certificado_preview: "",
    foto_sitio_preview: "",
  },
};

// Configuración limpia y compacta de pasos
const stepsConfig: StepItem[] = [
  { id: "estacion", title: "Información General", shortTitle: "General" },
  { id: "generales_aa", title: "Datos Generales AA", shortTitle: "Equipo AA" },
  {
    id: "condensadora",
    title: "Condensadora y Compresores",
    shortTitle: "Condensadora",
  },
  { id: "manejadora", title: "Unidad Manejadora", shortTitle: "Manejadora" },
  { id: "checklist", title: "Lista de Chequeo (39)", shortTitle: "Checklist" },
  { id: "acciones", title: "Mantenimiento Ejecutado", shortTitle: "Acciones" },
  { id: "fotos", title: "Anexos Fotográficos (15)", shortTitle: "Fotos" },
  {
    id: "cierre_firmas",
    title: "Plan de Mejora y Firmas",
    shortTitle: "Cierre",
  },
];

export const FormPreventivoAASlider: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] =
    useState<PreventivoAAFormData>(initialFormData);
  const { submit, isLoading } = useFormSubmit<SmuPayload>();
  // Cubre TODO el guardado (subida de fotos + POST): `isLoading` de
  // useFormSubmit solo está en true durante el POST.
  const [enviando, setEnviando] = useState(false);

  // Genérico a propósito: si el valor no coincide con el tipo del campo,
  // tsc falla en el punto de llamada (evita guardar un ChangeEvent u objeto
  // donde se espera string y terminar como "[object Object]" en la API).
  const updateField = <K extends keyof PreventivoAAFormData>(
    field: K,
    value: PreventivoAAFormData[K],
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Handlers Compresores
  const handleAddCompresor = () => {
    setFormData((prev) => ({
      ...prev,
      compresores: [
        ...prev.compresores,
        defaultCompresor(prev.compresores.length + 1),
      ],
    }));
  };

  const handleRemoveCompresor = (id: string) => {
    if (formData.compresores.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      compresores: prev.compresores.filter((c) => c.id !== id),
    }));
  };

  const handleUpdateCompresor = (
    id: string,
    field: keyof CompresorData,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      compresores: prev.compresores.map((c) =>
        c.id === id ? { ...c, [field]: value } : c,
      ),
    }));
  };

  // Handlers Condensadoras
  const handleAddCondensadora = () => {
    setFormData((prev) => ({
      ...prev,
      condensadoras: [
        ...prev.condensadoras,
        defaultCondensadora(prev.condensadoras.length + 1),
      ],
    }));
  };

  const handleRemoveCondensadora = (id: string) => {
    if (formData.condensadoras.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      condensadoras: prev.condensadoras.filter((c) => c.id !== id),
    }));
  };

  const handleUpdateCondensadora = (
    id: string,
    field: keyof UnidadCondensadoraData,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      condensadoras: prev.condensadoras.map((c) =>
        c.id === id ? { ...c, [field]: value } : c,
      ),
    }));
  };

  // Handlers Manejadoras
  const handleAddManejadora = () => {
    setFormData((prev) => ({
      ...prev,
      manejadoras: [
        ...prev.manejadoras,
        defaultManejadora(prev.manejadoras.length + 1),
      ],
    }));
  };

  const handleRemoveManejadora = (id: string) => {
    if (formData.manejadoras.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      manejadoras: prev.manejadoras.filter((m) => m.id !== id),
    }));
  };

  const handleUpdateManejadora = (
    id: string,
    field: keyof UnidadManejadoraData,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      manejadoras: prev.manejadoras.map((m) =>
        m.id === id ? { ...m, [field]: value } : m,
      ),
    }));
  };

  // Handlers Checklist
  const handleChecklistChange = (
    item_numero: number,
    estado: ChecklistEstado,
  ) => {
    setFormData((prev) => ({
      ...prev,
      checklist: {
        ...prev.checklist,
        [item_numero]: estado,
      },
    }));
  };

  const handleSetAllChecklist = (estado: ChecklistEstado) => {
    const updated = CHECKLIST_ITEMS_AA.reduce<Record<number, ChecklistEstado>>(
      (acc, item) => {
        acc[item.item_numero] = estado;
        return acc;
      },
      {},
    );
    setFormData((prev) => ({ ...prev, checklist: updated }));
  };

  // Handlers Acciones de Mantenimiento
  const handleAddAccion = () => {
    setFormData((prev) => ({
      ...prev,
      acciones_mantenimiento: [
        ...prev.acciones_mantenimiento,
        defaultAccionMantenimiento(prev.acciones_mantenimiento.length + 1),
      ],
    }));
  };

  const handleRemoveAccion = (id: string) => {
    if (formData.acciones_mantenimiento.length <= 1) return;
    setFormData((prev) => ({
      ...prev,
      acciones_mantenimiento: prev.acciones_mantenimiento.filter(
        (a) => a.id !== id,
      ),
    }));
  };

  const handleUpdateAccion = (
    id: string,
    field: keyof AccionesMantenimientoAAData,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      acciones_mantenimiento: prev.acciones_mantenimiento.map((a) =>
        a.id === id ? { ...a, [field]: value } : a,
      ),
    }));
  };

  // Handlers Fotos
  const handleFotoUpload = (slotId: string, file: File) => {
    const prev = formData.fotos[slotId]?.previewUrl;
    liberarPreviewUrl(prev);
    const previewUrl = URL.createObjectURL(file);
    setFormData((prev) => ({
      ...prev,
      fotos: {
        ...prev.fotos,
        [slotId]: { file, previewUrl, nombre: file.name },
      },
    }));
  };

  const handleFotoRemove = (slotId: string) => {
    const prev = formData.fotos[slotId]?.previewUrl;
    liberarPreviewUrl(prev);
    setFormData((prev) => {
      const updated = { ...prev.fotos };
      delete updated[slotId];
      return { ...prev, fotos: updated };
    });
  };

  const handleFotoDescripcion = (slotId: string, descripcion: string) => {
    setFormData((prev) => ({
      ...prev,
      fotos_descripciones: {
        ...prev.fotos_descripciones,
        [slotId]: descripcion,
      },
    }));
  };

  // Handlers Certificados y Fotos de Cierre
  const handleCertificadoFotoUpload = (
    field: "foto_certificado_preview" | "foto_sitio_preview",
    file: File,
  ) => {
    liberarPreviewUrl(formData.certificado[field]);
    const previewUrl = URL.createObjectURL(file);
    const fileField =
      field === "foto_certificado_preview"
        ? "foto_certificado_file"
        : "foto_sitio_file";
    setFormData((prev) => ({
      ...prev,
      certificado: {
        ...prev.certificado,
        [field]: previewUrl,
        [fileField]: file,
      },
    }));
  };

  const handleCertificadoFotoRemove = (
    field: "foto_certificado_preview" | "foto_sitio_preview",
  ) => {
    liberarPreviewUrl(formData.certificado[field]);
    const fileField =
      field === "foto_certificado_preview"
        ? "foto_certificado_file"
        : "foto_sitio_file";
    setFormData((prev) => ({
      ...prev,
      certificado: {
        ...prev.certificado,
        [field]: undefined,
        [fileField]: undefined,
      },
    }));
  };

  const fotosCargadasCount = Object.keys(formData.fotos).length;

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

      // Fase 3: las fotos se suben ANTES de crear la actividad (la API es
      // solo-POST, no hay PUT para adjuntarlas después).
      const pendientes: PendienteSubida[] = [];
      const payload = buildPreventivoAAPayload(formData, pendientes);
      await subirPendientes(pendientes);

      await submit(payload, {
        endpoint: SMU_ACTIVIDADES_ENDPOINT,
        method: "POST",
        onSuccess: (res) => {
          toast.success(
            `Preventivo de aire acondicionado guardado${
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

  const tecnicoNombreMostrado = formData.responsable_1
    ? `${formData.responsable_1.nombre} ${formData.responsable_1.apellido}`
    : formData.tecnico_nombre;

  return (
    <FormStepSlider
      steps={stepsConfig}
      currentStep={currentStep}
      onStepChange={setCurrentStep}
      onSubmit={handleSubmit}
      submitLabel="Guardar Preventivo AA"
      isSubmitting={isLoading || enviando}
    >
      {/* ── PASO 1: Información General ── */}
      {currentStep === 0 && (
        <div className="space-y-6">
          <SectionHeader
            title="Información General de la Estación"
            description="Complete los datos del sitio, los técnicos responsables y las fechas de ejecución."
          />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
            <div>
              <Label>Nombre de la Estación *</Label>
              <Input
                placeholder="Nombre de la estación"
                value={formData.nombre_estacion}
                onChange={(e) => updateField("nombre_estacion", e.target.value)}
              />
            </div>
            <div>
              <Label>Departamento *</Label>
              <Input
                placeholder="Departamento"
                value={formData.departamento}
                onChange={(e) => updateField("departamento", e.target.value)}
              />
            </div>
            <div>
              <Label>Dirección</Label>
              <Input
                placeholder="Dirección del sitio"
                value={formData.direccion}
                onChange={(e) => updateField("direccion", e.target.value)}
              />
            </div>
            <div>
              <Label>Tipo de Estación</Label>
              <Input
                placeholder="Tipo de estación"
                value={formData.tipo_estacion}
                onChange={(e) => updateField("tipo_estacion", e.target.value)}
              />
            </div>
            <div>
              <Label>Site Owner</Label>
              <Input
                placeholder="Site owner / Operador"
                value={formData.site_owner}
                onChange={(e) => updateField("site_owner", e.target.value)}
              />
            </div>
            <div>
              <Label>Código OT *</Label>
              <Input
                placeholder="Código OT"
                value={formData.codigo_ot}
                onChange={(e) => updateField("codigo_ot", e.target.value)}
              />
            </div>
            <div>
              <Label>Fecha Inicio Ejecución</Label>
              <Input
                type="datetime-local"
                value={formData.fecha_inicio}
                onChange={(e) => updateField("fecha_inicio", e.target.value)}
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

          {/* Responsables */}
          <div className="grid grid-cols-1 gap-5 pt-2 sm:grid-cols-2">
            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/2">
              <EmployeeSearchInput
                label="Responsable 1 (Principal) *"
                placeholder="Buscar por cédula o nombre..."
                value={formData.responsable_1}
                onChange={(empleado) => updateField("responsable_1", empleado)}
                required
                name="responsable_1"
                hint="Técnico principal ejecutor de la actividad"
              />
            </div>

            <div className="rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/2">
              <EmployeeSearchInput
                label="Responsable 2 (Apoyo / Acompañante)"
                placeholder="Buscar por cédula o nombre..."
                value={formData.responsable_2}
                onChange={(empleado) => updateField("responsable_2", empleado)}
                name="responsable_2"
                hint="Técnico auxiliar o de apoyo (opcional)"
              />
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 2: Datos Generales Aire Acondicionado ── */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <SectionHeader
            title="Datos Generales del Aire Acondicionado"
            description="Registre las especificaciones del equipo, alimentación eléctrica y mediciones de temperatura."
          />

          <div className="rounded-xl border border-gray-100 bg-gray-50/30 p-5 dark:border-gray-800 dark:bg-white/1">
            <h5 className="text-brand-600 dark:text-brand-400 mb-4 text-xs font-semibold tracking-wider uppercase">
              Especificaciones y Datos Técnicos del Equipo
            </h5>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
              <div>
                <Label>Marca *</Label>
                <Input
                  placeholder="Marca del equipo"
                  value={formData.marca}
                  onChange={(e) => updateField("marca", e.target.value)}
                />
              </div>
              <div>
                <Label>Modelo *</Label>
                <Input
                  placeholder="Modelo del equipo"
                  value={formData.modelo}
                  onChange={(e) => updateField("modelo", e.target.value)}
                />
              </div>
              <div>
                <Label>Serial *</Label>
                <Input
                  placeholder="Número de serie"
                  value={formData.serial}
                  onChange={(e) => updateField("serial", e.target.value)}
                />
              </div>
              <div>
                <Label>ID Activo Fijo</Label>
                <Input
                  placeholder="Placa / Activo fijo"
                  value={formData.id_activo}
                  onChange={(e) => updateField("id_activo", e.target.value)}
                />
              </div>
              <div>
                <Label>Tipo Aire</Label>
                <Input
                  placeholder="Tipo de aire"
                  value={formData.tipo_aire}
                  onChange={(e) => updateField("tipo_aire", e.target.value)}
                />
              </div>
              <div>
                <Label>Alimentación AC</Label>
                <Input
                  placeholder="Alimentación AC"
                  value={formData.alimentacion_ac}
                  onChange={(e) =>
                    updateField("alimentacion_ac", e.target.value)
                  }
                />
              </div>
              <div>
                <Label>Voltaje de Entrada AC (V)</Label>
                <Input
                  type="number"
                  step="0.1"
                  placeholder="Voltaje (V)"
                  value={formData.voltaje_entrada}
                  onChange={(e) =>
                    updateField("voltaje_entrada", e.target.value)
                  }
                />
              </div>
              <div>
                <Label>Corriente (Amp)</Label>
                <Input
                  type="number"
                  step="0.1"
                  placeholder="Corriente (A)"
                  value={formData.corriente}
                  onChange={(e) => updateField("corriente", e.target.value)}
                />
              </div>
              <div>
                <Label>Capacidad BTU</Label>
                <Input
                  type="number"
                  placeholder="Capacidad BTU"
                  value={formData.capacidad_btu}
                  onChange={(e) => updateField("capacidad_btu", e.target.value)}
                />
              </div>
              <div>
                <Label>Gestión Remota IP</Label>
                <Input
                  placeholder="IP de gestión"
                  value={formData.gestion_remota_ip}
                  onChange={(e) =>
                    updateField("gestion_remota_ip", e.target.value)
                  }
                />
              </div>
              <div>
                <Label>Cant. Compresores</Label>
                <Input
                  type="number"
                  placeholder="Cantidad"
                  value={formData.cantidad_compresores}
                  onChange={(e) =>
                    updateField("cantidad_compresores", e.target.value)
                  }
                />
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-gray-100 bg-gray-50/30 p-5 dark:border-gray-800 dark:bg-white/1">
            <h5 className="text-brand-600 dark:text-brand-400 mb-4 text-xs font-semibold tracking-wider uppercase">
              Temperaturas y Termostato
            </h5>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3">
              <div>
                <Label>Temp. Cuarto Equipo (Medida con Instrumento) (°C)</Label>
                <Input
                  type="number"
                  step="0.1"
                  placeholder="Temp. Cuarto (°C)"
                  value={formData.temp_cuarto}
                  onChange={(e) => updateField("temp_cuarto", e.target.value)}
                />
              </div>
              <div>
                <Label>Temperatura AA Entrada (°C)</Label>
                <Input
                  type="number"
                  step="0.1"
                  placeholder="Temp. Entrada (°C)"
                  value={formData.temp_entrada}
                  onChange={(e) => updateField("temp_entrada", e.target.value)}
                />
              </div>
              <div>
                <Label>Temperatura AA Salida (°C)</Label>
                <Input
                  type="number"
                  step="0.1"
                  placeholder="Temp. Salida (°C)"
                  value={formData.temp_salida}
                  onChange={(e) => updateField("temp_salida", e.target.value)}
                />
              </div>
              <div>
                <Label>Temp. Display (°C)</Label>
                <Input
                  type="number"
                  step="0.1"
                  placeholder="Temp. Display (°C)"
                  value={formData.temp_display}
                  onChange={(e) => updateField("temp_display", e.target.value)}
                />
              </div>
              <div>
                <Label>Temp. Termostato / Ajuste Termostato</Label>
                <Input
                  placeholder="Ajuste termostato"
                  value={formData.ajuste_termostato}
                  onChange={(e) =>
                    updateField("ajuste_termostato", e.target.value)
                  }
                />
              </div>
              <div>
                <Label>Temp. Termostato Pos Ajuste</Label>
                <Input
                  placeholder="Temp. pos ajuste"
                  value={formData.temp_termostato_pos_ajuste}
                  onChange={(e) =>
                    updateField("temp_termostato_pos_ajuste", e.target.value)
                  }
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 3: Condensadora y Compresores ── */}
      {currentStep === 2 && (
        <div className="space-y-8">
          <SectionHeader
            title="Unidades Condensadoras y Compresores"
            description="Registre las características de cada compresor y unidad condensadora. Puede añadir más unidades con los botones correspondientes."
          />

          {/* COMPRESORES */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h5 className="text-brand-600 dark:text-brand-400 text-sm font-semibold tracking-wider uppercase">
                Compresores ({formData.compresores.length})
              </h5>
              <AddItemButton
                label="Agregar Compresor"
                onClick={handleAddCompresor}
              />
            </div>

            {formData.compresores.map((comp, idx) => (
              <DynamicItemCard
                key={comp.id}
                label={`COMPRESOR ${idx + 1}`}
                onRemove={
                  formData.compresores.length > 1
                    ? () => handleRemoveCompresor(comp.id)
                    : undefined
                }
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                  <div>
                    <Label>Marca</Label>
                    <Input
                      placeholder="Marca"
                      value={comp.marca}
                      onChange={(e) =>
                        handleUpdateCompresor(comp.id, "marca", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Serial</Label>
                    <Input
                      placeholder="Serial"
                      value={comp.serial}
                      onChange={(e) =>
                        handleUpdateCompresor(comp.id, "serial", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Tipo</Label>
                    <Input
                      placeholder="Tipo"
                      value={comp.tipo}
                      onChange={(e) =>
                        handleUpdateCompresor(comp.id, "tipo", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Refrigerante</Label>
                    <Input
                      placeholder="Tipo refrigerante"
                      value={comp.refrigerante}
                      onChange={(e) =>
                        handleUpdateCompresor(
                          comp.id,
                          "refrigerante",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Modelo</Label>
                    <Input
                      placeholder="Modelo"
                      value={comp.modelo}
                      onChange={(e) =>
                        handleUpdateCompresor(comp.id, "modelo", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Aislamiento Eléctrico (MΩ)</Label>
                    <Input
                      placeholder="Aislamiento"
                      value={comp.aislamiento_electrico}
                      onChange={(e) =>
                        handleUpdateCompresor(
                          comp.id,
                          "aislamiento_electrico",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Presión Succión (PSI)</Label>
                    <Input
                      placeholder="Presión succión"
                      value={comp.presion_succion}
                      onChange={(e) =>
                        handleUpdateCompresor(
                          comp.id,
                          "presion_succion",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Presión Descarga (PSI)</Label>
                    <Input
                      placeholder="Presión descarga"
                      value={comp.presion_descarga}
                      onChange={(e) =>
                        handleUpdateCompresor(
                          comp.id,
                          "presion_descarga",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Nivel de Aceite</Label>
                    <Input
                      placeholder="Nivel aceite"
                      value={comp.nivel_aceite}
                      onChange={(e) =>
                        handleUpdateCompresor(
                          comp.id,
                          "nivel_aceite",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Voltaje VL1 / VL2 / VL3 (V)</Label>
                    <div className="grid grid-cols-3 gap-1">
                      <Input
                        placeholder="L1"
                        value={comp.vl1}
                        onChange={(e) =>
                          handleUpdateCompresor(comp.id, "vl1", e.target.value)
                        }
                      />
                      <Input
                        placeholder="L2"
                        value={comp.vl2}
                        onChange={(e) =>
                          handleUpdateCompresor(comp.id, "vl2", e.target.value)
                        }
                      />
                      <Input
                        placeholder="L3"
                        value={comp.vl3}
                        onChange={(e) =>
                          handleUpdateCompresor(comp.id, "vl3", e.target.value)
                        }
                      />
                    </div>
                  </div>
                  <div className="sm:col-span-2 md:col-span-2">
                    <Label>Corriente AMPL1 / AMPL2 / AMPL3 (A)</Label>
                    <div className="grid grid-cols-3 gap-1">
                      <Input
                        placeholder="Amp 1"
                        value={comp.ampl1}
                        onChange={(e) =>
                          handleUpdateCompresor(
                            comp.id,
                            "ampl1",
                            e.target.value,
                          )
                        }
                      />
                      <Input
                        placeholder="Amp 2"
                        value={comp.ampl2}
                        onChange={(e) =>
                          handleUpdateCompresor(
                            comp.id,
                            "ampl2",
                            e.target.value,
                          )
                        }
                      />
                      <Input
                        placeholder="Amp 3"
                        value={comp.ampl3}
                        onChange={(e) =>
                          handleUpdateCompresor(
                            comp.id,
                            "ampl3",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                  </div>
                </div>
              </DynamicItemCard>
            ))}
          </div>

          {/* UNIDADES CONDENSADORAS */}
          <div className="space-y-4 pt-2">
            <div className="flex items-center justify-between">
              <h5 className="text-brand-600 dark:text-brand-400 text-sm font-semibold tracking-wider uppercase">
                Unidades Condensadoras ({formData.condensadoras.length})
              </h5>
              <AddItemButton
                label="Agregar Condensadora"
                onClick={handleAddCondensadora}
              />
            </div>

            {formData.condensadoras.map((cond, idx) => (
              <DynamicItemCard
                key={cond.id}
                label={`UNIDAD CONDENSADORA ${idx + 1}`}
                onRemove={
                  formData.condensadoras.length > 1
                    ? () => handleRemoveCondensadora(cond.id)
                    : undefined
                }
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                  <div>
                    <Label>Marca</Label>
                    <Input
                      placeholder="Marca"
                      value={cond.marca}
                      onChange={(e) =>
                        handleUpdateCondensadora(
                          cond.id,
                          "marca",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Modelo</Label>
                    <Input
                      placeholder="Modelo"
                      value={cond.modelo}
                      onChange={(e) =>
                        handleUpdateCondensadora(
                          cond.id,
                          "modelo",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Serial</Label>
                    <Input
                      placeholder="Serial"
                      value={cond.serial}
                      onChange={(e) =>
                        handleUpdateCondensadora(
                          cond.id,
                          "serial",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Temperatura Entrada (°C)</Label>
                    <Input
                      placeholder="Temp. Entrada (°C)"
                      value={cond.temperatura_entrada}
                      onChange={(e) =>
                        handleUpdateCondensadora(
                          cond.id,
                          "temperatura_entrada",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Temperatura Salida (°C)</Label>
                    <Input
                      placeholder="Temp. Salida (°C)"
                      value={cond.temperatura_salida}
                      onChange={(e) =>
                        handleUpdateCondensadora(
                          cond.id,
                          "temperatura_salida",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Diámetro Eje</Label>
                    <Input
                      placeholder="Diámetro eje"
                      value={cond.diametro_eje}
                      onChange={(e) =>
                        handleUpdateCondensadora(
                          cond.id,
                          "diametro_eje",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Diámetro Aspas</Label>
                    <Input
                      placeholder="Diámetro aspas"
                      value={cond.diametro_aspas}
                      onChange={(e) =>
                        handleUpdateCondensadora(
                          cond.id,
                          "diametro_aspas",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                </div>
              </DynamicItemCard>
            ))}
          </div>
        </div>
      )}

      {/* ── PASO 4: Unidad Manejadora (Dinámica) ── */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <SectionHeader
            title={`Unidades Manejadoras (${formData.manejadoras.length})`}
            description="Registre las especificaciones de cada unidad manejadora, motor y blower."
            action={
              <AddItemButton
                label="Agregar Manejadora"
                onClick={handleAddManejadora}
              />
            }
          />

          <div className="space-y-4">
            {formData.manejadoras.map((manej, idx) => (
              <DynamicItemCard
                key={manej.id}
                label={`MANEJADORA ${idx + 1}`}
                onRemove={
                  formData.manejadoras.length > 1
                    ? () => handleRemoveManejadora(manej.id)
                    : undefined
                }
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                  <div>
                    <Label>Marca</Label>
                    <Input
                      placeholder="Marca"
                      value={manej.marca}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "marca",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Modelo</Label>
                    <Input
                      placeholder="Modelo"
                      value={manej.modelo}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "modelo",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Tipo</Label>
                    <Input
                      placeholder="Tipo"
                      value={manej.tipo}
                      onChange={(e) =>
                        handleUpdateManejadora(manej.id, "tipo", e.target.value)
                      }
                    />
                  </div>
                  <div>
                    <Label>Tipo de Filtro</Label>
                    <Input
                      placeholder="Tipo de filtro"
                      value={manej.tipo_filtro}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "tipo_filtro",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Tipo Correa</Label>
                    <Input
                      placeholder="Tipo de correa"
                      value={manej.tipo_correa}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "tipo_correa",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Marca Motor</Label>
                    <Input
                      placeholder="Marca motor"
                      value={manej.marca_motor}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "marca_motor",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Alimentación AC</Label>
                    <Input
                      placeholder="Alimentación AC"
                      value={manej.alimentacion_ac}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "alimentacion_ac",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Voltaje del Motor (V)</Label>
                    <Input
                      placeholder="Voltaje motor"
                      value={manej.voltaje_motor}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "voltaje_motor",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Corriente Motor (A)</Label>
                    <Input
                      placeholder="Corriente motor (A)"
                      value={manej.corriente_motor}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "corriente_motor",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Aislamiento (MΩ)</Label>
                    <Input
                      placeholder="Aislamiento"
                      value={manej.aislamiento}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "aislamiento",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Serial Motor</Label>
                    <Input
                      placeholder="Serial motor"
                      value={manej.serial_motor}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "serial_motor",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Dimensiones Blower</Label>
                    <Input
                      placeholder="Dimensiones blower"
                      value={manej.dimensiones_blower}
                      onChange={(e) =>
                        handleUpdateManejadora(
                          manej.id,
                          "dimensiones_blower",
                          e.target.value,
                        )
                      }
                    />
                  </div>
                </div>
              </DynamicItemCard>
            ))}
          </div>
        </div>
      )}

      {/* ── PASO 5: Lista de Chequeo General (39 Puntos) ── */}
      {currentStep === 4 && (
        <div className="space-y-6">
          <SectionHeader
            title="Lista de Chequeo General (39 Puntos de Inspección)"
            description="Evalúe cada parámetro como Sí, No o No Aplica."
            action={
              <button
                type="button"
                onClick={() => handleSetAllChecklist("Si")}
                className="border-success-200 bg-success-50 text-success-700 hover:bg-success-100 dark:border-success-500/30 dark:bg-success-500/10 dark:text-success-400 inline-flex items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-all"
              >
                <CheckCheck className="h-3.5 w-3.5" />
                Marcar Todos &quot;Sí&quot;
              </button>
            }
          />

          <div className="divide-y divide-gray-100 overflow-hidden rounded-xl border border-gray-200 bg-white dark:divide-gray-800 dark:border-gray-800 dark:bg-white/2">
            {CHECKLIST_ITEMS_AA.map((item) => (
              <ChecklistItem
                key={item.item_numero}
                numero={item.item_numero}
                parametro={item.parametro}
                value={formData.checklist[item.item_numero] || "Si"}
                onChange={(estado) =>
                  handleChecklistChange(item.item_numero, estado)
                }
              />
            ))}
          </div>
        </div>
      )}

      {/* ── PASO 6: Acciones y Mantenimiento Ejecutado ── */}
      {currentStep === 5 && (
        <div className="space-y-6">
          <SectionHeader
            title={`Acciones y Mantenimiento Ejecutado (${formData.acciones_mantenimiento.length})`}
            description="Seleccione las opciones correspondientes para cada equipo (AA 1, AA 2...)."
            action={
              <AddItemButton
                label="Agregar Equipo AA"
                onClick={handleAddAccion}
              />
            }
          />

          <div className="space-y-4">
            {formData.acciones_mantenimiento.map((accion, idx) => (
              <DynamicItemCard
                key={accion.id}
                label={`AA ${idx + 1}`}
                onRemove={
                  formData.acciones_mantenimiento.length > 1
                    ? () => handleRemoveAccion(accion.id)
                    : undefined
                }
              >
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
                  <div>
                    <Label>Limpieza de Serpentines</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.limpieza_serpentines}
                      onChange={(val) =>
                        handleUpdateAccion(
                          accion.id,
                          "limpieza_serpentines",
                          val,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Ajuste Elementos de Control</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.ajuste_elementos_control}
                      onChange={(val) =>
                        handleUpdateAccion(
                          accion.id,
                          "ajuste_elementos_control",
                          val,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Adición Refrigerante</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.adicion_refrigerante}
                      onChange={(val) =>
                        handleUpdateAccion(
                          accion.id,
                          "adicion_refrigerante",
                          val,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Estado Drenajes</Label>
                    <Select
                      options={OPCIONES_ESTADO_DRENAJES}
                      value={accion.estado_drenajes}
                      onChange={(val) =>
                        handleUpdateAccion(accion.id, "estado_drenajes", val)
                      }
                    />
                  </div>
                  <div>
                    <Label>Lubricación de Componentes</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.lubricacion_componentes}
                      onChange={(val) =>
                        handleUpdateAccion(
                          accion.id,
                          "lubricacion_componentes",
                          val,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Cambio Filtros Secado</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.cambio_filtros_secado}
                      onChange={(val) =>
                        handleUpdateAccion(
                          accion.id,
                          "cambio_filtros_secado",
                          val,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Alineación de Poleas</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.alineacion_poleas}
                      onChange={(val) =>
                        handleUpdateAccion(accion.id, "alineacion_poleas", val)
                      }
                    />
                  </div>
                  <div>
                    <Label>Cambio Comp. Electrónicos</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.cambio_componentes_electronicos}
                      onChange={(val) =>
                        handleUpdateAccion(
                          accion.id,
                          "cambio_componentes_electronicos",
                          val,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Cambio de Compresor</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.cambio_compresor}
                      onChange={(val) =>
                        handleUpdateAccion(accion.id, "cambio_compresor", val)
                      }
                    />
                  </div>
                  <div>
                    <Label>Cambio de Correas/Filtros</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.cambio_correas_filtros}
                      onChange={(val) =>
                        handleUpdateAccion(
                          accion.id,
                          "cambio_correas_filtros",
                          val,
                        )
                      }
                    />
                  </div>
                  <div>
                    <Label>Otras Reparaciones</Label>
                    <Select
                      options={OPCIONES_SI_NO_NA}
                      value={accion.otras_reparaciones}
                      onChange={(val) =>
                        handleUpdateAccion(accion.id, "otras_reparaciones", val)
                      }
                    />
                  </div>
                </div>
              </DynamicItemCard>
            ))}
          </div>

          <div>
            <Label>Observaciones de las Acciones</Label>
            <TextArea
              rows={3}
              placeholder="Observaciones sobre las acciones ejecutadas..."
              value={formData.acciones_observaciones}
              onChange={(e) =>
                updateField("acciones_observaciones", e.target.value)
              }
            />
          </div>
        </div>
      )}

      {/* ── PASO 7: Anexos Fotográficos (15 Fotos) ── */}
      {currentStep === 6 && (
        <div className="space-y-6">
          <SectionHeader
            title="Soportes Mantenimiento (Anexos Fotográficos)"
            description="Cargue las 15 fotografías de soporte para validar la ejecución de la actividad."
            action={
              <div className="bg-brand-50 text-brand-600 dark:bg-brand-500/10 dark:text-brand-400 inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold">
                <Camera className="h-3.5 w-3.5" />
                {fotosCargadasCount} de {FOTO_SLOTS_AA.length} fotos cargadas
              </div>
            }
          />

          {/* Grilla responsiva de 15 casillas */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {FOTO_SLOTS_AA.map((slot, idx) => (
              <FotoSlotWithDescripcion
                key={slot.id}
                index={idx + 1}
                titulo={slot.titulo}
                inputId={`foto-input-${slot.id}`}
                previewUrl={formData.fotos[slot.id]?.previewUrl}
                onUpload={(file) => file && handleFotoUpload(slot.id, file)}
                onRemove={() => handleFotoRemove(slot.id)}
                descripcion={formData.fotos_descripciones[slot.id] ?? ""}
                onDescripcionChange={(valor) =>
                  handleFotoDescripcion(slot.id, valor)
                }
                descripcionLabel={`Descripción de la foto ${idx + 1}`}
              />
            ))}
          </div>
        </div>
      )}

      {/* ── PASO 8: Plan de Mejora, Firmas y Certificaciones ── */}
      {currentStep === 7 && (
        <div className="space-y-6">
          {/* Bloque 1: Plan de Mejora */}
          <div className="rounded-xl border border-gray-200 bg-gray-50/30 p-5 dark:border-gray-800 dark:bg-white/1">
            <h4 className="mb-3 flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-white/90">
              <FileCheck2 className="text-brand-500 h-4 w-4" />
              5. Plan de Mejora
            </h4>
            <TextArea
              rows={3}
              placeholder="Describa el plan de mejora, acciones correctivas o recomendaciones técnicas..."
              value={formData.plan_mejora}
              onChange={(e) => updateField("plan_mejora", e.target.value)}
            />
          </div>

          {/* Bloque 2: Firmas y Validaciones */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/2">
            <h4 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-white/90">
              <PenTool className="text-brand-500 h-4 w-4" />
              Firmas y Responsables de Entrega
            </h4>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {/* Técnico */}
              <div className="space-y-3 rounded-lg border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/1">
                <span className="text-brand-600 dark:text-brand-400 text-xs font-bold tracking-wider uppercase">
                  TÉCNICO EJECUTOR
                </span>
                <div>
                  <Label>Nombre del Técnico</Label>
                  <Input
                    value={tecnicoNombreMostrado}
                    onChange={(e) =>
                      updateField("tecnico_nombre", e.target.value)
                    }
                    placeholder="Nombre completo"
                  />
                </div>
                <div>
                  <Label>Firma / Nombre de Firma</Label>
                  <Input
                    value={formData.tecnico_firma}
                    onChange={(e) =>
                      updateField("tecnico_firma", e.target.value)
                    }
                    placeholder="Firma del técnico"
                  />
                </div>
              </div>

              {/* Revisó */}
              <div className="space-y-3 rounded-lg border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/1">
                <span className="text-brand-600 dark:text-brand-400 text-xs font-bold tracking-wider uppercase">
                  REVISÓ / COORDINACIÓN
                </span>
                <div>
                  <Label>Revisó</Label>
                  <Input
                    value={formData.reviso_nombre}
                    onChange={(e) =>
                      updateField("reviso_nombre", e.target.value)
                    }
                    placeholder="Nombre de quien revisó"
                  />
                </div>
                <div>
                  <Label>Firma / Nombre de Firma</Label>
                  <Input
                    value={formData.reviso_firma}
                    onChange={(e) =>
                      updateField("reviso_firma", e.target.value)
                    }
                    placeholder="Firma de quien revisó"
                  />
                </div>
              </div>

              {/* Empresa */}
              <div className="space-y-3 rounded-lg border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/1">
                <span className="text-brand-600 dark:text-brand-400 text-xs font-bold tracking-wider uppercase">
                  EMPRESA EJECUTORA
                </span>
                <div>
                  <Label>Empresa</Label>
                  <Input
                    value={formData.empresa}
                    onChange={(e) => updateField("empresa", e.target.value)}
                    placeholder="Nombre de la empresa"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Bloque 3: Certificados Técnicos y Soporte en Sitio */}
          <div className="rounded-xl border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-white/2">
            <h4 className="mb-4 flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-white/90">
              <ShieldCheck className="text-brand-500 h-4 w-4" />
              Certificado Técnico y Soporte en Sitio
            </h4>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
              {/* Certificado Datos */}
              <div>
                <Label>Certificado</Label>
                <Input
                  value={formData.certificado.tipo_certificado}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      certificado: {
                        ...prev.certificado,
                        tipo_certificado: e.target.value,
                      },
                    }))
                  }
                  placeholder="Tipo de certificado"
                />
              </div>

              {/* Técnico */}
              <div>
                <Label>Técnico</Label>
                <Input
                  value={tecnicoNombreMostrado}
                  disabled
                  placeholder="Nombre del técnico"
                  className="bg-gray-100/60 dark:bg-gray-800/60"
                />
              </div>

              {/* Categoría */}
              <div>
                <Label>Categoría / Matrícula</Label>
                <Input
                  value={formData.certificado.categoria_certificado}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      certificado: {
                        ...prev.certificado,
                        categoria_certificado: e.target.value,
                      },
                    }))
                  }
                  placeholder="Categoría o matrícula"
                />
              </div>

              {/* Empresa */}
              <div>
                <Label>Empresa</Label>
                <Input
                  value={formData.empresa}
                  disabled
                  placeholder="Empresa ejecutora"
                  className="bg-gray-100/60 dark:bg-gray-800/60"
                />
              </div>
            </div>

            {/* Soportes: Foto Matrícula + Foto Técnico en Sitio */}
            <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
              {/* 1. Foto Matrícula CONTE / Certificado */}
              <FotoSlotCard
                index={1}
                titulo="Foto Certificado / Matrícula Profesional"
                previewUrl={formData.certificado.foto_certificado_preview}
                inputId="foto-certificado-input"
                onUpload={(file) =>
                  file &&
                  handleCertificadoFotoUpload("foto_certificado_preview", file)
                }
                onRemove={() =>
                  handleCertificadoFotoRemove("foto_certificado_preview")
                }
              />

              <FotoSlotCard
                index={2}
                titulo="Foto del Técnico en Sitio (con Carné / EPP)"
                previewUrl={formData.certificado.foto_sitio_preview}
                inputId="foto-sitio-input"
                onUpload={(file) =>
                  file &&
                  handleCertificadoFotoUpload("foto_sitio_preview", file)
                }
                onRemove={() =>
                  handleCertificadoFotoRemove("foto_sitio_preview")
                }
              />
            </div>
          </div>
        </div>
      )}
    </FormStepSlider>
  );
};

export default FormPreventivoAASlider;
