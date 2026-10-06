import { StepItem } from "../../common/FormStepSlider";
import { FormCapexTipologia1Data, FilaMedidaSPT, InsumoSAPItem, ActividadMOItem } from "./types";

// ─── Configuración Oficial de Pasos del Formulario (Sin paso de definición) ────
export const STEPS_CONFIG_TIPOLOGIA_1: StepItem[] = [
  { id: "general", title: "Información General", shortTitle: "General" },
  { id: "suministros", title: "1. Inventario de Suministros", shortTitle: "Suministros" },
  { id: "actividades", title: "2. MO - Actividades Estandarizadas", shortTitle: "Actividades" },
  { id: "transportes", title: "3. Transportes", shortTitle: "Transportes" },
  { id: "spt", title: "4. Resultados de Reforma SPT", shortTitle: "Resultados SPT" },
  { id: "plano", title: "5. Panorámica y Plano EB", shortTitle: "Plano EB" },
  { id: "fuera_estandar", title: "6. Actividades Fuera del Estándar", shortTitle: "Justificaciones" },
  { id: "cierre", title: "7. Recomendaciones y Cierre", shortTitle: "Cierre" },
];

// ─── Opciones de Selección Estandarizadas ─────────────────────────────────────
export const OPCIONES_UNIDAD_MEDIDA = [
  { value: "UNIDADES", label: "UNIDADES" },
  { value: "UNIDAD", label: "UNIDAD" },
  { value: "METROS", label: "METROS" },
  { value: "CM", label: "CM" },
  { value: "ROLLO", label: "ROLLO" },
  { value: "KG", label: "KG" },
  { value: "GALON", label: "GALÓN" },
  { value: "GLOBAL", label: "GLOBAL" },
];

export const OPCIONES_TIPO_TRANSPORTE = [
  { value: "VEHICULO 4X4", label: "VEHÍCULO 4X4" },
  { value: "VEHICULO 4X2", label: "VEHÍCULO 4X2" },
  { value: "MOTOCICLETA", label: "MOTOCICLETA" },
  { value: "CAMIÓN", label: "CAMIÓN" },
  { value: "TRANSPORTE FLUVIAL", label: "TRANSPORTE FLUVIAL" },
  { value: "CAMINATA / SEMOVIENTE", label: "A PIE / SEMOVIENTE" },
  { value: "OTRO", label: "OTRO" },
];

// ─── Catálogo de Referencia: Suministros Frecuentes (Oficiales de la ficha) ──
export const CATALOGO_SUMINISTROS_FRECUENTES = [
  {
    codigo_sap: "3046179",
    texto_sap: "SUM CABLE DE ALUMINIO THW # 4/0 AWG",
    alcance: "Sum Cable de Aluminio THW # 4/0 AWG",
    unidad_medida: "METROS",
    comentarios: "Cambio de acuerdo a la altura de la torre + 10 metros de cola de cada bajante, solo se aplica para bajante centrales de torre (De equipos y de pararrayos)",
  },
  {
    codigo_sap: "3046184",
    texto_sap: "SUM. CABLE DE ALUMINIO THW # 4 AWG",
    alcance: "Sum. Cable de Aluminio THW # 4 AWG",
    unidad_medida: "METROS",
    comentarios: "equipotencial equipos Cambia de acuerdo al numero de equipos en la EB, anillos amplios o reducidos.",
  },
  {
    codigo_sap: "3046128",
    texto_sap: "SUMINISTRO HIDROSOLTA (BULTO X 15 KG)",
    alcance: "Sum. Cable de Aluminio THW # 6 AWG",
    unidad_medida: "UNIDADES",
    comentarios: "SUMINISTRO HIDROSOLTA (bulto x 15 kg)",
  },
  {
    codigo_sap: "3026117",
    texto_sap: "MF CINTA BANDIT ACERADA DE 1/2''*",
    alcance: "MO MF CINTA BANDIT ACERADA DE 1/2''",
    unidad_medida: "CM",
    comentarios: "ESTANDAR",
  },
  {
    codigo_sap: "3046299",
    texto_sap: "MT SE SUM HEBILLA 1/2\" ACERO INOXIDABLE",
    alcance: "HEBILLA 1/2\" DE ACERO INOXIDABLE",
    unidad_medida: "UNIDADES",
    comentarios: "ESTANDAR",
  },
  {
    codigo_sap: "3046190",
    texto_sap: "SUM. TERMINALES DE COBRE ESTAÑADO DE UN OJO 4/0",
    alcance: "Sum. Terminales de cobre estañado de un ojo 4/0",
    unidad_medida: "UNIDADES",
    comentarios: "Sum. Terminales de cobre estañado de un ojo 4/0",
  },
  {
    codigo_sap: "3046419",
    texto_sap: "SUMINISTROS TERMINALES ESTAÑADAS DE 2 OJOS NO.6",
    alcance: "Suministros Terminales estañadas de 2 ojos No.6",
    unidad_medida: "UNIDAD",
    comentarios: "Suministros Terminales estañadas de 2 ojos No.6",
  },
  {
    codigo_sap: "3046612",
    texto_sap: "SUMINISTRO E INSTALACION BUSBAR. BARRAJE COMUN PARA CONEXIONES DE TIERRA EN EXTERIORES DE 40X25 30 PERFORACIONES",
    alcance: "Suministro e instalación Busbar. Barraje común para conexiones de tierra en exteriores de 40x25 30 perforaciones, incluye todos los accesorios: tornillos, incluyendo dos aisladores para anclaje al muro",
    unidad_medida: "UNIDADES",
    comentarios: "Para equipotencializar cada equipo y cada cuarto de la estación base",
  },
  {
    codigo_sap: "3046187",
    texto_sap: "SUM. CABLE DE COBRE DESNUDO CALIBRE 2/0",
    alcance: "Sum. Cable de cobre desnudo calibre 2/0",
    unidad_medida: "METROS",
    comentarios: "suministro para el cable desnudo 2/0 para la malla de tierra",
  },
  {
    codigo_sap: "3046169",
    texto_sap: "SUMINISTRO PARARRAYOS TORRE FRANKLIN TIPO BOLA.",
    alcance: "Suministro Pararrayos torre Franklin tipo bola.",
    unidad_medida: "UNIDAD",
    comentarios: "Instalación en la torre para absorción de descargas atmosféricas",
  },
  {
    codigo_sap: "3046125",
    texto_sap: "SUMINISTRO DE GRASA DIELÉCTRICA 3 ONZA",
    alcance: "Suministro de Grasa dieléctrica 3 onza",
    unidad_medida: "UNIDADES",
    comentarios: "Prevenir la corrosión y permitir la conectividad",
  },
  {
    codigo_sap: "3046163",
    texto_sap: "SUM. ELECTRODO COPPERWELD 5/8\" X 2,4 M",
    alcance: "Sum. Electrodo Copperweld 5/8\" x 2,4 m",
    unidad_medida: "UNIDADES",
    comentarios: "SUMINISTRO DE ELECTRODO COPPERWELD",
  },
  {
    codigo_sap: "3046193",
    texto_sap: "MO MT SUMINISTR INSTALACION CONECTORES C",
    alcance: "Suministro e instalación conectores en C",
    unidad_medida: "UNIDADES",
    comentarios: "Conector para reforzar soldadura exotérmica",
  },
];

// ─── Catálogo de Referencia: Actividades MO Frecuentes ────────────────────────
export const CATALOGO_ACTIVIDADES_FRECUENTES = [
  {
    codigo_sap: "3045889",
    texto_sap: "APERTURA BRECHA DE 0,3 M DE ANCHO X 0,8 M DE PROFUNDIDAD EN",
    alcance: "APERTURA BRECHA DE 0,3 M DE ANCHO X 0,8 M DE PROFUNDIDAD EN TERRENO ROCOSO.",
    comentarios: "Primera. Apertura de la malla a Tierra y cierre = 2 / Segunda. Apertura de la malla del poste y cierre = 2 / Tercera. Apertura para unificar malla de poste y anillo de la EB + cierre = 2",
  },
  {
    codigo_sap: "3046050",
    texto_sap: "INS. CABLE DE ALUMINIO THW # 4/0 AWG",
    alcance: "Ins. Cable de Aluminio THW # 4/0 AWG",
    comentarios: "Ins. Cable de Aluminio THW # 4/0 AWG",
  },
  {
    codigo_sap: "3046055",
    texto_sap: "INS. CABLE DE ALUMINIO THW # 4 AWG",
    alcance: "Ins. Cable de Aluminio THW # 4 AWG",
    comentarios: "equipotencial equipos Cambia de acuerdo al numero de equipos en la EB, anillos amplios o reducidos.",
  },
  {
    codigo_sap: "3046055",
    texto_sap: "INSTALACION HIDROSOLTA (BULTO X 15 KG)",
    alcance: "Instalación o barrido del equipo en terreno",
    comentarios: "Cambia de acuerdo al área del terrenos en la EB, anillos amplios o reducidos.",
  },
  {
    codigo_sap: "3026117",
    texto_sap: "MO CINTA BANDIT ACERADA DE 1/2''* + MO SE SUM HEBILLA 1/2\" ACERO INOXIDABLE",
    alcance: "Instalación",
    comentarios: "Instalación",
  },
  {
    codigo_sap: "3046038",
    texto_sap: "INST. ELECTRODO DE COBRE 5/8\" X 2,4 M EN TERRENO ROCOSO",
    alcance: "Inst. Electrodo de cobre 5/8\" x 2,4 m en terreno rocoso",
    comentarios: "Instalación de electrodo de acuerdo a la naturaleza del terreno",
  },
  {
    codigo_sap: "3045958",
    texto_sap: "TRATAMIENTO DEL TERRENO CON SUELO ARTIFICIAL PARA EL MEJORAMIENTO DE LA PUESTA A TIERRA",
    alcance: "Tratamiento del terreno con suelo artificial para el mejoramiento de la puesta a tierra Incluye medición de la resistencia de puesta a tierra, antes y después del tratamiento con entrega de informe. Incluye, instalación de alambre de cobre, varilla y accesorios de puesta a tierra. Previo estudio y mediciones solicitadas por Comcel.",
    comentarios: "TRATAMIENTO DEL TERRENO CON SUELO ARTIFICIAL PARA EL MEJORAMIENTO DE LA PUESTA A TIERRA INCLUYE MEDICIÓN DE LA RESISTENCIA DE PUESTA A TIERRA, ANTES Y DESPUÉS DEL TRATAMIENTO CON ENTREGA DE INFORME.",
  },
  {
    codigo_sap: "3046612",
    texto_sap: "SUMINISTRO E INSTALACION BUSBAR. BARRAJE COMUN PARA CONEXIONES DE TIERRA EN EXTERIORES DE 40X25 30 PERFORACIONES",
    alcance: "Suministro e instalación Busbar. Barraje común para conexiones de tierra en exteriores de 40x25 30 perforaciones, incluye todos los accesorios: tornillos, incluyendo dos aisladores para anclaje al muro",
    comentarios: "Para equipotencializar cada equipo y cada cuarto de la estación base.",
  },
  {
    codigo_sap: "3046058",
    texto_sap: "INS. CABLE DE COBRE DESNUDO CALIBRE 2/0",
    alcance: "Ins. Cable de cobre desnudo calibre 2/0",
    comentarios: "Instalación para el cable desnudo 2/0",
  },
  {
    codigo_sap: "3046106",
    texto_sap: "RETIRO DE PLATINA DE TIERRA (BUSBAR)",
    alcance: "Retiro de platina de tierra (BUSBAR)",
    comentarios: "para el retiro completo de las busbar que están en la estación base",
  },
  {
    codigo_sap: "3046193",
    texto_sap: "MO MT SUMINISTR INSTALACION CONECTORES C",
    alcance: "Suministro e instalación conectores en C",
    comentarios: "Conector para reforzar soldadura exotérmica",
  },
  {
    codigo_sap: "3046003",
    texto_sap: "INSTALACIÓN PARARRAYOS TORRE FRANKLIN TIPO BOLA.",
    alcance: "Suministro e instalación conectores en C",
    comentarios: "Instalación Pararrayos torre Franklin tipo bola.",
  },
];

// ─── Elementos Técnicos de Referencia del Plano ───────────────────────────────
export const ELEMENTOS_PLANO_SPT = [
  "Anillo de tierra #1 (Malla Perimetral)",
  "Anillo de tierra #2 (Anillo Torre - 28 metros aprox.)",
  "Bajante #1 (Torre / Pararrayos 60 metros)",
  "Bajante #2 (Pata Aérea / Enlaces)",
  "Línea central 70 metros",
  "Cable de cobre desnudo 2/0 (28 metros alrededor de la torre)",
  "Cable en aluminio 4/0 bajante central (60m pararrayos a bajo + 70m bajante a busbar + 10m a busbar = 160m)",
  "Cable en aluminio #4 para los puentes en las omegas (8 metros)",
  "Barrajes Busbar 40x25 para equipotencialización",
  "Electrodos Copperweld 5/8'' x 2.4 m (8 varillas)",
  "Soldaduras exotérmicas / Conectores en C",
  "Muros de contención / Pasamuros de ingreso",
];

// ─── Generadores de Datos Iniciales ───────────────────────────────────────────
export const createDefaultInsumo = (index: number): InsumoSAPItem => ({
  id: `insumo-${Date.now()}-${index}`,
  texto_sap: "",
  codigo_sap: "",
  alcance: "",
  comentarios: "",
  cantidad_estandar: "",
  cantidad_real: "",
  unidad_medida: "UNIDADES",
});

export const createDefaultActividad = (index: number): ActividadMOItem => ({
  id: `actividad-${Date.now()}-${index}`,
  texto_sap: "",
  codigo_sap: "",
  alcance: "",
  comentarios: "",
  foto_antes_preview: undefined,
  foto_despues_preview: undefined,
});

export const DEFAULT_FILAS_SPT_INICIALES: FilaMedidaSPT[] = [
  { id: "spt-1", distancia: "5", medida_ohmio: "", resistividad: "" },
  { id: "spt-2", distancia: "10", medida_ohmio: "", resistividad: "" },
  { id: "spt-3", distancia: "15", medida_ohmio: "", resistividad: "" },
  { id: "spt-4", distancia: "20", medida_ohmio: "", resistividad: "" },
  { id: "spt-5", distancia: "25", medida_ohmio: "", resistividad: "" },
];

export const INITIAL_FORM_DATA_TIPOLOGIA_1: FormCapexTipologia1Data = {
  // Información General
  nombre_estacion: "",
  ot: "",
  fecha_inicio: "",
  fecha_fin: "",
  tipo_estacion: "",
  site_owner: "",
  responsable_ejecuta: null,
  empresa: "",
  coordinador_aliado: "",

  // 1.- Inventario de Suministros
  insumos: [createDefaultInsumo(1)],

  // 2.- MO - Actividades Estandarizadas
  actividades: [createDefaultActividad(1)],
  descripcion_general_actividades: "",

  // 3. Transportes
  transporte_tipo: "VEHICULO 4X4",
  transporte_codigo_sap: "",
  transporte_distancia_km: "",
  transporte_tiempo_desplazamiento: "",
  transporte_descripcion: "",
  transporte_foto_antes: undefined,
  transporte_foto_durante: undefined,
  transporte_foto_despues: undefined,

  // 4. Resultados de Reforma SPT
  spt_naturaleza_terreno_desc: "",
  spt_naturaleza_terreno_foto: undefined,
  filas_spt: DEFAULT_FILAS_SPT_INICIALES,
  spt_recomendacion_aliado: "",

  // 5. Panorámica de la Torre y Plano EB
  foto_panoramica_preview: undefined,
  foto_plano_preview: undefined,
  plano_recomendacion_aliado: "",

  // 6. Actividades Fuera del Estándar
  otras_actividades_1: "",
  otras_actividades_2: "",
  otras_actividades_3: "",
  texto_justificacion_otras_actividades: "",
  fotos_justificacion: [
    { id: "just-1" },
    { id: "just-2" },
    { id: "just-3" },
    { id: "just-4" },
  ],
  foto_soporte_matricula_preview: undefined,
  matricula_nombre: "",
  matricula_numero: "",
  matricula_fecha: "",

  // 7. Recomendaciones y Cierre
  recomendaciones_finales: "",
  responsable_entrega_nombre: "",
  responsable_entrega_cedula: "",
  responsable_entrega_cargo: "Técnico Ejecutor",
  responsable_entrega_fecha: "",
  responsable_entrega_firma: "",

  aprobado_nombre: "",
  aprobado_cedula: "",
  aprobado_cargo: "Coordinador / Aliado",
  aprobado_fecha: "",
  aprobado_firma: "",
  observaciones_cierre: "",
};
