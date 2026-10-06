import { StepItem } from "../../common/FormStepSlider";
import { FormCapexTipologia3Data, InsumoSAPItem, ActividadMOItem, TransporteItem } from "./types";

// ─── Configuración Oficial de Pasos del Formulario ───────────────────────────
export const STEPS_CONFIG_TIPOLOGIA_3: StepItem[] = [
  { id: "general", title: "Información General", shortTitle: "General" },
  { id: "suministros", title: "1. Inventario de Suministros", shortTitle: "Suministros" },
  { id: "actividades", title: "2. MO - Actividades Estandarizadas", shortTitle: "Actividades" },
  { id: "transportes", title: "3. Transportes", shortTitle: "Transportes" },
  { id: "recomendaciones", title: "4. Recomendaciones", shortTitle: "Recomendaciones" },
];

// ─── Opciones de Selección Estandarizadas ─────────────────────────────────────
export const OPCIONES_UNIDAD_MEDIDA = [
  { value: "UNIDADES", label: "UNIDADES" },
  { value: "UNIDAD", label: "UNIDAD" },
  { value: "UNIDAD/EQUIPO", label: "UNIDAD/EQUIPO" },
  { value: "LB", label: "LB" },
  { value: "M3", label: "M3" },
  { value: "ML", label: "ML" },
  { value: "METROS", label: "METROS" },
  { value: "GLOBAL", label: "GLOBAL" },
];

export const OPCIONES_TIPO_TRANSPORTE = [
  { value: "VEHICULO 4X4 Y/O CAMION", label: "4X4 Y/O CAMIÓN" },
  { value: "COTEROS", label: "COTEROS" },
  { value: "SEMOVIENTES", label: "SEMOVIENTES" },
  { value: "LANCHA / PANGA / CANOA", label: "LANCHA / PANGA / CANOA" },
  { value: "OTRO", label: "OTRO" },
];

// ─── Catálogo de Referencia: Suministros Frecuentes (Oficiales de la ficha) ──
export const CATALOGO_SUMINISTROS_FRECUENTES = [
  {
    codigo_sap: "3045806",
    texto_sap: "REFRIGERANTE R410A",
    alcance: "REFRIGERANTE R410A",
    unidad_medida: "LB",
    cantidad_estandar: "25",
    comentarios:
      "Reconversión a refrigerantes ecológicos. 12BTU = 6 Lbs + 7 Lbs promedio por 15 mts de tubería / 24BTU = 8 Lbs + 7 Lbs / 36BTU = 10 Lbs + 7 Lbs / 48BTU = 12 Lbs + 7 Lbs / 60BTU = 14 Lbs + 7 Lbs",
  },
  {
    codigo_sap: "3045516",
    texto_sap: "MT AA SUMINISTRO COMPRESOR 3,5TR",
    alcance: "El proveedor deberá suministrar COMPRESOR CON CAPACIDAD DE 3,5 TR",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045517",
    texto_sap: "MT AA SUMINISTRO COMPRESOR 5,0TR",
    alcance: "El proveedor deberá suministrar COMPRESOR CON CAPACIDAD DE 5,0 TR",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045518",
    texto_sap: "MT AA SUM COMPRESOR HERM MINI SPLIT MONO",
    alcance:
      "El proveedor deberá suministrar COMPRESORES TIPO \"HERMETICO\" PARA MINI SPLIT / MONOFÁSICOS A 220 VAC - 60HZ - R407c.",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045519",
    texto_sap: "MT AA SUM COMPRESOR HERM MINI SPLIT 1,5TR",
    alcance:
      "El proveedor deberá suministrar COMPRESORES TIPO \"HERMETICO\" PARA MINI SPLIT / MONOFÁSICOS A 220 VAC - 60HZ - R407c. CAPACIDAD DE 1,5 TR",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045520",
    texto_sap: "MT AA SUM COMPRESOR HERM MINI SPLIT 2,0TR",
    alcance:
      "El proveedor deberá suministrar COMPRESORES TIPO \"HERMETICO\" PARA MINI SPLIT / MONOFÁSICOS A 220 VAC - 60HZ - R407c. CON CAPACIDAD DE 2,0 TR",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045521",
    texto_sap: "MT AA SUM COMPRESOR HERM MINI SPLIT 2,5TR",
    alcance:
      "El proveedor deberá suministrar COMPRESORES TIPO \"HERMETICO\" PARA MINI SPLIT / MONOFÁSICOS A 220 VAC - 60HZ - R407c. CAPACIDAD DE 2,5 TR",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045522",
    texto_sap: "MT AA SUM COMPRESOR HERM MINI SPLIT 3,0TR",
    alcance:
      "El proveedor deberá suministrar COMPRESORES TIPO \"HERMETICO\" PARA MINI SPLIT / MONOFÁSICOS A 220 VAC - 60HZ - R407c. CAPACIDAD DE 3,0 TR",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045523",
    texto_sap: "MT AA SUM COMPRESOR HERM MINI SPLIT 3,5TR",
    alcance:
      "El proveedor deberá suministrar COMPRESORES TIPO \"HERMETICO\" PARA MINI SPLIT / MONOFÁSICOS A 220 VAC - 60HZ - R407c. CAPACIDAD DE 3,5 TR",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045524",
    texto_sap: "MT AA SUM COMPRESOR 2,0TR COPELAND HERM",
    alcance:
      "El proveedor deberá suministrar COMPRESOR CON CAPACIDAD DE 2,0 TR. COMPRESORES \"COPELAND\" TIPO \"HERMETICO\" / MONOFÁSICOS A 220 VAC - R407C / SERIE \"CR\"",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045525",
    texto_sap: "MT AA SUM COMPRESOR 2,5TR COPELAND HERM",
    alcance:
      "El proveedor deberá suministrar COMPRESOR CON CAPACIDAD DE 2,5 TR. COMPRESORES \"COPELAND\" TIPO \"HERMETICO\" / MONOFÁSICOS A 220 VAC - R407C / SERIE \"CR\"",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045526",
    texto_sap: "MT AA SUM COMPRESOR 3,0TR COPELAND HERM",
    alcance:
      "El proveedor deberá suministrar COMPRESOR CON CAPACIDAD DE 3,0 TR. COMPRESORES \"COPELAND\" TIPO \"HERMETICO\" / MONOFÁSICOS A 220 VAC - R407C / SERIE \"CR\"",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045527",
    texto_sap: "MT AA SUM COMPRESOR 3,5TR COPELAND HERM",
    alcance:
      "El proveedor deberá suministrar COMPRESOR CON CAPACIDAD DE 3,5 TR. COMPRESORES \"COPELAND\" TIPO \"HERMETICO\" / MONOFÁSICOS A 220 VAC - R407C / SERIE \"CR\"",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045528",
    texto_sap: "MT AA SUM COMPRESOR 5,0TR COPELAND HERM",
    alcance:
      "El proveedor deberá suministrar COMPRESOR CON CAPACIDAD DE 5,0 TR. COMPRESORES \"COPELAND\" TIPO \"HERMETICO\" / MONOFÁSICOS A 220 VAC - R407C / SERIE \"CR\"",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple por capacidad y configuración energía comercial estación base. El que aplique",
  },
  {
    codigo_sap: "3045508",
    texto_sap: "MT AA SUMINISTRO FILTRO SECADOR 1/4\"",
    alcance: "El proveedor debe suministrar FILTRO SECADOR DE 1/4 PULGADAS",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA y diámetro de tubería. El que aplique",
  },
  {
    codigo_sap: "3045510",
    texto_sap: "MT AA SUMINISTRO FILTRO SECADOR 1/2\"",
    alcance: "El proveedor debe suministrar FILTRO SECADOR DE 1/2 PULGADAS",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA y diámetro de tubería. El que aplique",
  },
  {
    codigo_sap: "3045512",
    texto_sap: "MT AA SUMINISTRO FILTRO SECADOR 3/4\"",
    alcance: "El proveedor debe suministrar FILTRO SECADOR DE 3/4 PULGADAS",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA y diámetro de tubería. El que aplique",
  },
  {
    codigo_sap: "3045509",
    texto_sap: "MT AA SUMINISTRO FILTRO SECADOR 3/8\"",
    alcance: "El proveedor debe suministrar FILTRO SECADOR DE 3/8 PULGADAS",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA y diámetro de tubería. El que aplique",
  },
  {
    codigo_sap: "3045511",
    texto_sap: "MT AA SUMINISTRO FILTRO SECADOR 5/8\"",
    alcance: "El proveedor debe suministrar FILTRO SECADOR DE 5/8 PULGADAS",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA y diámetro de tubería. El que aplique",
  },
  {
    codigo_sap: "3045805",
    texto_sap: "NITROGENO",
    alcance: "NITROGENO",
    unidad_medida: "M3",
    cantidad_estandar: "3",
    comentarios: "Gas comprimido",
  },
  {
    codigo_sap: "3045549",
    texto_sap: "MT AA SUMINISTRO TUBERIA DE COBRE 1/4\"",
    alcance:
      "El proveedor deberá suministrar TUBERÍA DE COBRE DE 1/4 PULGADAS. Incluye suministro de soportes estructurales tipo \"Riel\" donde sea necesario.",
    unidad_medida: "ML",
    cantidad_estandar: "5",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA. El que aplique",
  },
  {
    codigo_sap: "3045551",
    texto_sap: "MT AA SUMINISTRO TUBERIA DE COBRE 1/2\"",
    alcance:
      "El proveedor deberá suministrar TUBERÍA DE COBRE DE 1/2 PULGADAS. Incluye suministro de soportes estructurales tipo \"Riel\" donde sea necesario.",
    unidad_medida: "ML",
    cantidad_estandar: "5",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA. El que aplique",
  },
  {
    codigo_sap: "3045553",
    texto_sap: "MT AA SUMINISTRO TUBERIA DE COBRE 3/4\"",
    alcance:
      "El proveedor deberá suministrar TUBERÍA DE COBRE DE 3/4 PULGADAS. Incluye suministro de soportes estructurales tipo \"Riel\" donde sea necesario.",
    unidad_medida: "ML",
    cantidad_estandar: "5",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA. El que aplique",
  },
  {
    codigo_sap: "3045550",
    texto_sap: "MT AA SUMINISTRO TUBERIA DE COBRE 3/8\"",
    alcance:
      "El proveedor deberá suministrar TUBERÍA DE COBRE DE 3/8 PULGADAS. Incluye suministro de soportes estructurales tipo \"Riel\" donde sea necesario.",
    unidad_medida: "ML",
    cantidad_estandar: "5",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA. El que aplique",
  },
  {
    codigo_sap: "3045552",
    texto_sap: "MT AA SUMINISTRO TUBERIA DE COBRE 5/8\"",
    alcance:
      "El proveedor deberá suministrar TUBERÍA DE COBRE DE 5/8 PULGADAS. Incluye suministro de soportes estructurales tipo \"Riel\" donde sea necesario.",
    unidad_medida: "ML",
    cantidad_estandar: "5",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA. El que aplique",
  },
  {
    codigo_sap: "3045615",
    texto_sap: "MT AA SUMINIST DRENAJES TUBERIA PVC 1/2\"",
    alcance:
      "El proveedor debe realizar suministro de drenajes en tubería PVC de 1/2\" para equipos de aire acondicionado. Incluye accesorios.",
    unidad_medida: "ML",
    cantidad_estandar: "2",
    comentarios:
      "Se debe realizar la instalación de drenaje para guiar el agua producto de la condensación y evitar daños de los equipos por contacto con agua",
  },
  {
    codigo_sap: "3045543",
    texto_sap: "MT AA SUM CAPACITOR ARRAN COMPRES MAX5TR",
    alcance: "El proveedor deberá suministrar CAPACITOR DE ARRANQUE DE COMPRESOR (CAPACIDAD HASTA 5 TR)",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "2",
    comentarios: "Capacitor eléctrico que se utiliza para aumentar el par motor inicial de un motor",
  },
  {
    codigo_sap: "3045548",
    texto_sap: "MT AA SUMIN AISLAMIENTO TERMICO RUBATEX",
    alcance: "El proveedor deberá suministrar AISLAMIENTO TERMICO - \"RUBATEX\"",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "15",
    comentarios: "Se utiliza para aislar y controlar la condensación de vapor de agua",
  },
  {
    codigo_sap: "3045803",
    texto_sap: "MT OTR SUM RUBATEX CINTA R1/8X2\"ESPX915M",
    alcance: "Rubatex cinta rollo 1/8\" x 2\" esp. x 9.15m",
    unidad_medida: "ML",
    cantidad_estandar: "15",
    comentarios: "Se utiliza para aislar y controlar la condensación de vapor de agua",
  },
  {
    codigo_sap: "EN CREACION 9",
    texto_sap: "CINTA AISLANTE DE VINILO SUPER 33+ SCOTCH 19MMX20",
    alcance: "CINTA AISLANTE DE VINILO SUPER 33+ SCOTCH 19MMX20",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "3",
    comentarios: "Se utiliza para todas las tipologías #1, #2, #3, #4, #5 y correctivos menores",
  },
  {
    codigo_sap: "3046398",
    texto_sap: "MT SE SUM CABLE ENCAUCHETADO 3X10",
    alcance: "CABLE ENCAUCHETADO 3X10",
    unidad_medida: "ML",
    cantidad_estandar: "15",
    comentarios: "Para AA de capacidades de 12000BTU a 24000BTU",
  },
  {
    codigo_sap: "3046401",
    texto_sap: "MT SE SUM CABLE ENCAUCHETADO 3X8",
    alcance: "CABLE ENCAUCHETADO 3X8",
    unidad_medida: "ML",
    cantidad_estandar: "15",
    comentarios: "Para AA de capacidades de 36000BTU a 60000BTU",
  },
  {
    codigo_sap: "3045611",
    texto_sap: "MT AA SUM MOTOR EL MO220V-AC1 1/4HP COND",
    alcance:
      "El proveedor deberá suministrar MOTOR ELÉCTRICO MONOFÁSICO A 220 V-AC DE 1 1/4 HP para Condensadora",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios:
      "Motor ventilador del condensador — se encarga de refrigerar el serpentín de la condensadora para retirar el calor del líquido refrigerante. Donde aplique",
  },
];

// ─── Catálogo de Referencia: Actividades MO Frecuentes ────────────────────────
export const CATALOGO_ACTIVIDADES_FRECUENTES = [
  {
    codigo_sap: "3045806",
    texto_sap: "REFRIGERANTE R410A",
    alcance: "REFRIGERANTE R410A",
    comentarios:
      "Reconversión tecnología a refrigerantes ecológicos. 12BTU = 6 Lbs + 7 Lbs / 24BTU = 8 Lbs + 7 Lbs / 36BTU = 10 Lbs + 7 Lbs / 48BTU = 12 Lbs + 7 Lbs / 60BTU = 14 Lbs + 7 Lbs (promedio por 15 mts de tubería)",
  },
  {
    codigo_sap: "3045398",
    texto_sap: "MO AA AJUSTE RECARGA REFRIGERANTE MAX5TR",
    alcance:
      "El proveedor debe realizar AJUSTE O RECARGA DE REFRIGERANTE DE AIRE ACONDICIONADO con capacidad hasta 5 TR (R22 - R407C - R410A)",
    comentarios: "Item corresponde a la mano de obra del suministro del refrigerante",
  },
  {
    codigo_sap: "3045471",
    texto_sap: "MO AA CAMB/CONVERS REFRIGE EQ AA MAX10TR",
    alcance:
      "El proveedor debe realizar las modificaciones, configuración y ajustes necesarios para conversión a refrigerante ecológico en los equipos de acondicionamiento de aire con capacidades hasta 10 TR",
    comentarios: "Se realiza reconversión de R22 a R410, por temas ecológicos",
  },
  {
    codigo_sap: "3045402",
    texto_sap: "MO AA CAMBIO COMPRESORES MAX 5TR",
    alcance: "El proveedor debe realizar CAMBIO DE COMPRESORES de capacidad hasta 5 TR",
    comentarios: "Cambio de unidad averiada por unidad nueva",
  },
  {
    codigo_sap: "3045332",
    texto_sap: "MO AA CAMBIO FILTRO SECADOR",
    alcance: "El proveedor debe realizar CAMBIO DE FILTRO SECADOR",
    comentarios:
      "La labor del filtro es filtrar las partículas y los residuos que fluyen en el circuito y también absorber cualquier humedad",
  },
  {
    codigo_sap: "3045459",
    texto_sap: "EL PROVEEDOR DEBE REALIZAR BARRIDO CON NITRÓGENO POR CIRCUITO.",
    alcance: "El proveedor debe realizar barrido con nitrógeno por circuito.",
    comentarios: "1 de vacío, 1 de barrido",
  },
  {
    codigo_sap: "3045425",
    texto_sap: "INSTALACIÓN - MONTAJE DE TUBERÍA DE COBRE 1/4 PULGADAS",
    alcance: "El proveedor debe realizar INSTALACIÓN - MONTAJE DE TUBERÍA DE COBRE DE 1/4 PULGADAS hasta 5m",
    comentarios: "Si cumple de acuerdo a la capacidad (BTU) del AA. El que aplique",
  },
  {
    codigo_sap: "3045615",
    texto_sap: "MT AA SUMINIST DRENAJES TUBERIA PVC 1/2\"",
    alcance:
      "El proveedor debe realizar suministro de drenajes en tubería PVC de 1/2\" para equipos de aire acondicionado. Incluye accesorios.",
    comentarios:
      "Se debe realizar la instalación de drenaje para guiar el agua producto de la condensación y evitar daños de los equipos por contacto con agua",
  },
  {
    codigo_sap: "3045415",
    texto_sap: "MO AA CAMBIO BLOWER Y/O MOTOR(ES) MAX5TR",
    alcance:
      "El proveedor debe realizar CAMBIO CONJUNTO DE BLOWERS Y/O MOTOR(ES) DE LA UNIDAD EVAPORADORA O CONDENSADORA. Capacidades hasta 5 TR. Donde aplique y con VoBo de jefes o ingenieros de soporte debe presentar evidencia de aprobación",
    comentarios:
      "Motor ventilador del evaporador — se encarga de mantener el flujo continuo de aire en el recinto. Donde aplique",
  },
  {
    codigo_sap: "3045395",
    texto_sap: "MO AA CAMBIO CAPACITORES ARRANQ COMPRESR",
    alcance: "El proveedor debe realizar CAMBIO DE CAPACITORES DE ARRANQUE DEL COMPRESOR",
    comentarios: "Permite que el motor se encienda y apague rápidamente",
  },
  {
    codigo_sap: "3045548",
    texto_sap: "MT AA SUMIN AISLAMIENTO TERMICO RUBATEX",
    alcance:
      "El proveedor deberá suministrar AISLAMIENTO TERMICO - \"RUBATEX\" y cinta Rubatex rollo 1/8\" x 2\" esp. x 9.15m",
    comentarios: "Se utiliza para aislar y controlar la condensación de vapor de agua",
  },
  {
    codigo_sap: "3045611",
    texto_sap: "MT AA SUM MOTOR EL MO220V-AC1 1/4HP COND",
    alcance:
      "El proveedor deberá suministrar MOTOR ELÉCTRICO MONOFÁSICO A 220 V-AC DE 1 1/4 HP para Condensadora",
    comentarios: "Motor ventilador del condensador. Donde aplique",
  },
  {
    codigo_sap: "S/N",
    texto_sap: "PANORAMICA DE LA TUBERIA DESDE LA SALIDA DE LA EVAPORADORA HASTA LA CONDENSADORA",
    alcance:
      "Deben presentar en fotografías el recorrido de la tubería desde la condensadora hasta la evaporadora sin curvaturas, tendidos estéticos y asegurados",
    comentarios: "Registro fotográfico antes / después",
  },
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
  descripcion: "",
  foto_antes_preview: undefined,
  foto_despues_preview: undefined,
});

export const createDefaultTransporte = (index: number): TransporteItem => ({
  id: `transporte-${Date.now()}-${index}`,
  tipo: "VEHICULO 4X4 Y/O CAMION",
  codigo_sap: "",
  descripcion: "",
  foto_antes_preview: undefined,
  foto_durante_preview: undefined,
  foto_despues_preview: undefined,
});

export const INITIAL_FORM_DATA_TIPOLOGIA_3: FormCapexTipologia3Data = {
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

  // 3. Transportes
  transportes: [createDefaultTransporte(1)],

  // 4. Recomendaciones de la Actividad
  recomendaciones_finales: "",
};
