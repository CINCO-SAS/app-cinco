import { StepItem } from "../../common/FormStepSlider";
import { FormCapexTipologia5Data, InsumoSAPItem, ActividadMOItem, TransporteItem, JustificacionFotoItem } from "./types";

// ─── Configuración Oficial de Pasos del Formulario ───────────────────────────
export const STEPS_CONFIG_TIPOLOGIA_5: StepItem[] = [
  { id: "general", title: "Información General", shortTitle: "General" },
  { id: "suministros", title: "1. Inventario de Suministros", shortTitle: "Suministros" },
  { id: "actividades", title: "2. MO - Actividades Estandarizadas", shortTitle: "Actividades" },
  { id: "transportes", title: "3. Transportes", shortTitle: "Transportes" },
  { id: "plano", title: "4. Panorámica y Plano EB", shortTitle: "Panorámica/Plano" },
  { id: "fuera_estandar", title: "5. Fuera del Estándar", shortTitle: "Fuera Estándar" },
  { id: "recomendaciones", title: "6. Recomendaciones", shortTitle: "Recomendaciones" },
];

// ─── Opciones de Selección Estandarizadas ─────────────────────────────────────
export const OPCIONES_UNIDAD_MEDIDA = [
  { value: "UNIDADES", label: "UNIDADES" },
  { value: "UNIDAD", label: "UNIDAD" },
  { value: "METROS", label: "METROS" },
  { value: "ML", label: "ML" },
  { value: "CM", label: "CM" },
  { value: "M3", label: "M3" },
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
    codigo_sap: "3046131",
    texto_sap: "MT SE SUMINISTRO PARARRAYOS 15KV",
    alcance: "PARARRAYOS 15KV TIPO ESTACION POLIMERICO OHIO BRASS",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "La cantidad está sometida de acuerdo a la configuración: doble pararrayo si es monofásico 4 y si es trifásico 6 pararrayos (cantidad estándar: 4 o 6).",
  },
  {
    codigo_sap: "3046260",
    texto_sap: "MT SE SUM CORTACIRCUITO MONOPOL 15KV100A",
    alcance: "CORTACIRCUITO MONOPOLAR 15 KV 100A",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "La cantidad está sometida de acuerdo a la configuración: doble pararrayo si es monofásico 4 y si es trifásico 6 pararrayos (cantidad estándar: 4 o 6).",
  },
  {
    codigo_sap: "3046292",
    texto_sap: "MT SE SUM FUSIBLE DUAL 3.1 A 15KV",
    alcance: "FUSIBLE DUAL 3.1 A 15 KV",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "Se requiere para la protección de los equipos, la cantidad depende de la configuración del sitio (cantidad estándar: 4 o 6).",
  },
  {
    codigo_sap: "3046176",
    texto_sap: "MT SE SUM CABLE COBRE THHN/THWN #2AWG",
    alcance: "Sum. Cable de cobre THHN/THWN # 2 AWG",
    unidad_medida: "ML",
    cantidad_estandar: "",
    comentarios:
      "SUMINISTRO PARA EL CAMBIO DE LA ACOMETIDA DEL CONTADOR AL TOTALIZADOR + DESDE EL TOTALIZADOR A LA TRANSFERENCIA + CONTACTOR DE EMERGENCIA A PLANTA DE HASTA 115A.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046185",
    texto_sap: "MT SE SUM CABLE COBRE TIPO VEHICULO #4",
    alcance: "Sum. Cable de cobre tipo vehículo #4.",
    unidad_medida: "ML",
    cantidad_estandar: "",
    comentarios:
      "PARA LA ALIMENTACIÓN DE SISTEMA DE RECTIFICACIÓN BIFÁSICO.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046178",
    texto_sap: "MT SE SUM CABLE COBRE THHN/THWN #6AWG",
    alcance: "Sum. Cable de cobre THHN/THWN # 6 AWG",
    unidad_medida: "ML",
    cantidad_estandar: "",
    comentarios:
      "La cantidad instalada depende de la configuración del sitio.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046412",
    texto_sap: "MT SE SUM TERMIN ESTAÑAD/TERMO PLATEAD#4",
    alcance: "SUMINISTRO TERMINALES ESTAÑADAS O TERMO PLATEADAS DE #4",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "Se requiere para dar buen ajuste a conexión entre el conductor y el totalizador.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046413",
    texto_sap: "MT SE SUM TERMIN ESTAÑAD/TERMO PLATEAD#2",
    alcance: "SUMINISTRO TERMINALES ESTAÑADAS O TERMO PLATEADAS DE #2",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "Se requiere para dar buen ajuste a conexión entre el conductor y el totalizador.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046419",
    texto_sap: "MT SE SUM TERMINALES ESTAÑADA 2 OJOS #6",
    alcance: "Suministros Terminales estañadas de 2 ojos No.6",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "Se requiere para dar buen ajuste a conexión entre el conductor y el totalizador.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046333",
    texto_sap: "MT SE SUM TUBO GALVANIZ 2\"X3MT CON UNION",
    alcance: "TUBO GALVANIZADO 2\" x 3 MTS con unión",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "PARA EL BAJANTE DEL TRANSFORMADOR.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046299",
    texto_sap: "MT SE SUM HEBILLA 1/2\" ACERO INOXIDABLE",
    alcance: "HEBILLA 1/2\" DE ACERO INOXIDABLE",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "Se requiere para el ajuste de la cinta bandit.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3026117",
    texto_sap: "MO MF CINTA BANDIT ACERADA DE 1/2''",
    alcance: "MO MF CINTA BANDIT ACERADA DE 1/2''",
    unidad_medida: "CM",
    cantidad_estandar: "1000",
    comentarios: "Se requiere para sujetar el tubo galvanizado.",
  },
  {
    codigo_sap: "3046140",
    texto_sap: "MT SE PROTECCION CLAS I+II SOBRETENS INV",
    alcance:
      "Protección Clase I+II Contra Sobretensiones Inversor: Suministro DPS Clase I+II, 3P+NPE, 150V, 12,5kA (10/350), 30kA (8/20) por vía, Up≤1000V. Incluye terminales, elementos de conexión y elementos de fijación.",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "Debemos revisar este tema porque el elemento requerido es una AC Data 200KA 220/110 3F.",
  },
  {
    codigo_sap: "3046329",
    texto_sap: "MT SE SUM TRANSF 1F15KVA13,2KV/240-120V",
    alcance: "TRANSFORMADOR 1F 15KVA 13,2KV/240-120V",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios:
      "En caso que aplique. NO todas las tipologías deben proceder con cambio del transformador; el cambio debe llevar un VoBo por correo de jefe o ingeniero de soporte.",
  },
  {
    codigo_sap: "3046330",
    texto_sap: "MT SE SUM TRANSF 1F25KVA13,2KV/240-120V",
    alcance: "TRANSFORMADOR 1F 25KVA 13,2KV/240-120V",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios:
      "En caso que aplique. NO todas las tipologías deben proceder con cambio del transformador; el cambio debe llevar un VoBo por correo de jefe o ingeniero de soporte.",
  },
  {
    codigo_sap: "3046331",
    texto_sap: "MT SE SUM TRANSF 3F30KVA11,4KV/208-120V",
    alcance: "TRANSFORMADOR 3F 30KVA 11,4KV/208-120V",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios:
      "En caso que aplique. NO todas las tipologías deben proceder con cambio del transformador; el cambio debe llevar un VoBo por correo de jefe o ingeniero de soporte.",
  },
  {
    codigo_sap: "3046332",
    texto_sap: "MT SE SUM TRANSF 3F30KVA13,2KV/214-123V",
    alcance: "TRANSFORMADOR 3F 30KVA 13,2KV/214-123V",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios:
      "En caso que aplique. NO todas las tipologías deben proceder con cambio del transformador; el cambio debe llevar un VoBo por correo de jefe o ingeniero de soporte.",
  },
  {
    codigo_sap: "3046450",
    texto_sap: "MT SE SUM TABLERO AC COMPL INCLU BREAKER",
    alcance:
      "Suministro Tablero AC completo incluye breakers (Según estándar vigente de Comcel. Todos los breakers son tipo industrial de 25 KA de ruptura) estándar adjunto. Tablero construido en lámina Cold Roll Cal.18 con tratamiento superficial y acabado de pintura.",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "",
  },
  {
    codigo_sap: "3046144",
    texto_sap: "MT SE SUMINIST CINTA MARCACION INSTAL AC",
    alcance:
      "Suministro de cintas de marcación instalaciones AC (BLANCA, ROJA, VERDE, AMARILLA, AZUL, NEGRA)",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios: "Cantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046555",
    texto_sap: "MT SE SUMIN AMARRA PLASTICA 25CMX100UN",
    alcance: "Suministro Amarras plásticas 25 cm *100 unidades",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios: "Cantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046424",
    texto_sap: "MT SE SUM TERMIN USA COMPRE 2BARRIL LARG",
    alcance: "Terminal USA Compresión 2 barril largo",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios: "Cantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046425",
    texto_sap: "MT SE SUM TERMIN USA COMPRE 4BARRIL LARG",
    alcance: "Terminal USA Compresión 4 barril largo",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios: "Cantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046438",
    texto_sap: "MT SE SUM INTERRUPTOR PRINCIPAL 3X125AMP",
    alcance:
      "Suministro de interruptor principal de 3x125 AMP Icc=45 KA. Marca Merlin Gerin o Siemens. Para sistema monofásico. Incluye desinstalación de breaker existente.",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "2",
    comentarios:
      "APLICA PARA SISTEMA TRIFÁSICO.\nPARA SISTEMA BIFÁSICO CAPACIDAD MÁX. DE 125A DE DOS POLOS: uno de 125 o de 100 breaker principal y uno para protección del TGP de 100 A.",
  },
  {
    codigo_sap: "3045588",
    texto_sap: "MT AA SUM BREAKER TOTALIZAD IND 3X80AMP",
    alcance: "El proveedor deberá suministrar BREAKER TIPO TOTALIZADOR INDUSTRIAL DE 3x80 AMP. - 25 KA",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "2",
    comentarios:
      "APLICA PARA LOS POWER:\n2 BREAKER DE 3X80A PARA TRIFÁSICO\n2 BREAKER DE 2X80A PARA BIFÁSICO\nCUMPLIR EL ICC",
  },
  {
    codigo_sap: "3046448",
    texto_sap: "MT SE SUM BREAKER TOTALIZ3*100A65KA RUPT",
    alcance: "BREAKER totalizador 3*100A, 65 Ka de Ruptura",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "APLICA PARA BREAKER PPAL EB Y DEL POWER.",
  },
  {
    codigo_sap: "3046457",
    texto_sap: "MT SE SUM CAJA CONTAD TRIF+TOTALIZAET918",
    alcance: "CAJA CONTADOR TRIFÁSICO + TOTALIZADOR ET918",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "1",
    comentarios: "APLICA PARA LA CAJA DEL CONTADOR Y DEL TOTALIZADOR.",
  },
  {
    codigo_sap: "3046229",
    texto_sap: "MT SE SUM CONECTOR TRANSVERSAL #2",
    alcance: "CONECTOR TRANSVERSAL #2",
    unidad_medida: "UNIDAD",
    cantidad_estandar: "",
    comentarios:
      "CONECTOR TRANSVERSAL DE MT.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046183",
    texto_sap: "MT SE SUM CABLE ALUMINIO TIPO VEHICULO #4",
    alcance: "Sum. Cable de aluminio tipo vehículo #4.",
    unidad_medida: "METROS",
    cantidad_estandar: "",
    comentarios:
      "PARA LA ALIMENTACIÓN DE SISTEMA DE RECTIFICACIÓN BIFÁSICO.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
  {
    codigo_sap: "3046220",
    texto_sap: "MT SE SUM CABLE ALUMINIO THHN/THWN #1-0AWG",
    alcance: "Sum. Cable de ALUMINIO THHN/THWN # 1-0 AWG",
    unidad_medida: "METROS",
    cantidad_estandar: "",
    comentarios:
      "SUMINISTRO PARA EL CAMBIO DE LA ACOMETIDA DEL CONTADOR AL TOTALIZADOR + DESDE EL TOTALIZADOR A LA TRANSFERENCIA + CONTACTOR DE EMERGENCIA A PLANTA DE HASTA 115A.\nCantidad estándar: según el área de la EB trazada para esta actividad.",
  },
];

// ─── Catálogo de Referencia: Actividades MO Frecuentes ────────────────────────
export const CATALOGO_ACTIVIDADES_FRECUENTES = [
  {
    codigo_sap: "3046152",
    texto_sap: "MO SE INST/RET PARARRAYO 9-10-27KV 10KA",
    alcance:
      "Instalación o retiro de pararrayos de 9 kV, 10 kV, 27 kV hasta 10 kA. Por unidad. Incluye el retiro y montaje de pararrayos de 9 kV, 10 kV, 27 kV hasta 10 kA. Por unidad. Incluye suministro e instalación de accesorios. Incluye la apertura y cierre de circuitos donde fuera necesario para ejecutar los trabajos.",
    comentarios: "",
  },
  {
    codigo_sap: "3045980",
    texto_sap: "MO SE CAMB CORTACIRC CAÑUELA SUBEST CONV",
    alcance:
      "Cambio cortacircuitos de cañuela en subestación convencional. Por unidad. Incluye conexionado y cambio de fusible, cables y conectores, cambio de terminales y/o cables de conexionado en caso necesario. Incluye adaptación del soporte y conexión a las barras o cambio de fusible y de conectores. Incluye reintegro a bodega del material retirado. Incluye la apertura y cierre de circuitos en donde fuera necesario para ejecutar el trabajo.",
    comentarios:
      "La cantidad está sometida de acuerdo a la configuración: doble pararrayo si es monofásico 4 y si es trifásico 6 pararrayos.",
  },
  {
    codigo_sap: "3046047",
    texto_sap: "MO SE INS CABLE COBRE THHN/THWN #2AWG",
    alcance: "Ins. Cable de cobre THHN/THWN # 2 AWG",
    comentarios:
      "MANO DE OBRA PARA EL CAMBIO DE LA ACOMETIDA DEL CONTADOR AL TOTALIZADOR + DESDE EL TOTALIZADOR A LA TRANSFERENCIA + CONTACTOR DE EMERGENCIA A PLANTA DE HASTA 115A. Deben presentar evidencias del metraje.",
  },
  {
    codigo_sap: "3046048",
    texto_sap: "MO SE INS CABLE DE COBRE THHN/THWN #4AWG",
    alcance: "INS. CABLE DE COBRE THHN/THWN # 4 AWG",
    comentarios: "PARA LA ALIMENTACIÓN DE SISTEMA DE RECTIFICACIÓN BIFÁSICO",
  },
  {
    codigo_sap: "3046049",
    texto_sap: "MO SE INS CABLE DE COBRE THHN/THWN #6AWG",
    alcance: "Ins. Cable de cobre THHN/THWN # 6 AWG",
    comentarios: "PARA LA ALIMENTACIÓN DEL POWER + PARA LA SERIE DE LOS PARARRAYOS",
  },
  {
    codigo_sap: "3045971",
    texto_sap: "MO SE CAMBIO DESCARGADOR SOBRETENS POST",
    alcance:
      "Cambio de descargador de sobretensiones en poste existente (sin cambio de cruceta). Por unidad. Incluye conexionado, cambio de cables y conectores en caso necesario. Incluye retiro, instalación y reintegro a bodega del material retirado. Incluye la apertura y cierre de circuitos en donde fuera necesario para ejecutar los trabajos.",
    comentarios: "Se requiere para la protección de sobretensiones transitorias.",
  },
  {
    codigo_sap: "3045987",
    texto_sap: "MO SE CAMBIO TRANSFORMADOR TRIFAS POSTE",
    alcance:
      "Cambio de transformador trifásico en poste. Incluye retiro e instalación de protecciones en MT y BT y todas las tareas complementarias necesarias para la realización del trabajo y la energización del transformador, reintegro del transformador y materiales retirados a bodega. Incluye también el cambio de abrazaderas, vigas de madera y herrajes en caso necesario.",
    comentarios:
      "En caso que aplique y con VoBo de jefes o ingenieros de soporte, montar evidencias del correo.",
  },
  {
    codigo_sap: "3046439",
    texto_sap: "MO SE INSTAL INTERRUPTOR PRINCI 3X125AMP",
    alcance:
      "Instalación de interruptor principal de 3x125 AMP Icc=45 KA. Marca Merlin Gerin o Siemens. Para sistema monofásico. Incluye desinstalación de breaker existente.",
    comentarios:
      "APLICA PARA SISTEMA TRIFÁSICO. MO DE PRINCIPAL Y 2 TOTALIZADORES DEL POWER. PARA SISTEMA BIFÁSICO CAPACIDAD MÁX. DE 125A DE DOS POLOS.",
  },
  {
    codigo_sap: "3045588",
    texto_sap: "MT AA SUM BREAKER TOTALIZAD IND 3X80AMP",
    alcance: "El proveedor deberá suministrar BREAKER TIPO TOTALIZADOR INDUSTRIAL DE 3x80 AMP. - 25 KA",
    comentarios:
      "APLICA PARA LOS POWER: 2 BREAKER DE 3X80A PARA TRIFÁSICO / 2 BREAKER DE 2X80A PARA BIFÁSICO / CUMPLIR EL ICC.",
  },
  {
    codigo_sap: "3046448",
    texto_sap: "MT SE SUM BREAKER TOTALIZ3*100A65KA RUPT",
    alcance: "BREAKER totalizador 3*100A, 65 Ka de Ruptura",
    comentarios: "APLICA PARA BREAKER PPAL EB Y DEL POWER.",
  },
  {
    codigo_sap: "3046457",
    texto_sap: "MT SE SUM CAJA CONTAD TRIF+TOTALIZAET918",
    alcance: "CAJA CONTADOR TRIFÁSICO + TOTALIZADOR ET918",
    comentarios: "APLICA PARA LA CAJA DEL CONTADOR Y DEL TOTALIZADOR.",
  },
  {
    codigo_sap: "3046140",
    texto_sap: "MT SE PROTECCION CLAS I+II SOBRETENS INV",
    alcance:
      "Protección Clase I+II Contra Sobretensiones Inversor: Suministro DPS Clase I+II, 3P+NPE, 150V, 12,5kA (10/350), 30kA (8/20) por vía, Up≤1000V. Incluye terminales, elementos de conexión y elementos de fijación.",
    comentarios: "Se requiere para la protección de sobretensiones transitorias.",
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
  unidad_medida: "UNIDAD",
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
  distancia_km: "",
  tiempo: "",
  descripcion: "",
  foto_antes_preview: undefined,
  foto_durante_preview: undefined,
  foto_despues_preview: undefined,
});

export const createDefaultJustificacionFoto = (index: number): JustificacionFotoItem => ({
  id: `justificacion-${Date.now()}-${index}`,
  previewUrl: undefined,
});

export const INITIAL_FORM_DATA_TIPOLOGIA_5: FormCapexTipologia5Data = {
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

  // 4. Panorámica de la Torre y Plano EB
  foto_panoramica_preview: undefined,
  foto_plano_preview: undefined,
  plano_recomendacion_aliado: "",

  // 5. Actividades Fuera del Estándar
  texto_justificacion: "",
  fotos_justificacion: [
    createDefaultJustificacionFoto(1),
    createDefaultJustificacionFoto(2),
    createDefaultJustificacionFoto(3),
    createDefaultJustificacionFoto(4),
  ],

  // 6. Recomendaciones de la Actividad
  recomendaciones_finales: "",
};
