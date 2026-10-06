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
  Plus,
  Trash2,
  Zap,
  Gauge,
  BatteryCharging,
  Activity,
  Cpu,
  CheckCheck,
  MinusCircle,
  Search,
  Camera,
  Image as ImageIcon,
  Upload,
  FileCheck2,
  ShieldCheck,
  PenTool,
} from "lucide-react";
import { toast } from "sonner";
import { useFormSubmit } from "@/hooks/useFormSubmit";
import FotoSlotCard from "@/components/form/input/FotoSlotCard";
import FotoSlotWithDescripcion from "@/components/form/input/FotoSlotWithDescripcion";
import { liberarPreviewUrl } from "@/lib/fotos";
import {
  buildPreventivoPlantaPayload,
  subirPendientes,
  validarFechasEncabezado,
  SMU_ACTIVIDADES_ENDPOINT,
  type PendienteSubida,
  type SmuPayload,
} from "@/services/smu.service";
import { manejarErrorGuardado, toastErrorActividad } from "@/modules/smu/errors";
import { clonarEstadoInicial, liberarPreviews } from "@/modules/smu/reinicio";

// Opciones estándar para dropdowns de estado de la batería
const OPCIONES_ESTADO = [
  { value: "BUENO", label: "BUENO" },
  { value: "REGULAR", label: "REGULAR" },
  { value: "MALO", label: "MALO" },
  { value: "N/A", label: "N/A" },
];

// Valores sentinela de los filtros (checklist por sistema / fotos por
// categoría): al elegirlos no se filtra nada. Declarados una sola vez porque
// el valor se usa como id y como etiqueta del chip del dropdown.
const FILTRO_TODOS_SISTEMAS = "TODOS";
const FILTRO_TODAS_FOTOS = "TODAS";

export type ChecklistPlantaEstado = "OK" | "NO OK" | "N/A";

/** Servicio de filtración: mismo rango que `ESTADO_FILTRACION_CHOICES` (backend). */
export type EstadoFiltracion = "SÍ" | "NO" | "N/A";

// Listas de opciones de la ficha oficial. Única fuente dentro del archivo:
// alimentan los tipos de `PruebasFiltracionPlantaData` y los tres grupos de
// botones del paso de Pruebas/Filtración. Deben coincidir con
// ESTADO_PRUEBA_CHOICES y ESTADO_FILTRACION_CHOICES del modelo backend.
const ESTADOS_PRUEBA: ChecklistPlantaEstado[] = ["OK", "NO OK", "N/A"];
const ESTADOS_FILTRACION: EstadoFiltracion[] = ["SÍ", "NO", "N/A"];

// Configuración de los pasos del formulario de Planta (Nombres concisos)
const stepsConfig: StepItem[] = [
  { id: "datos_generales", title: "General" },
  { id: "datos_principales", title: "Datos Planta" },
  { id: "lista_chequeo", title: "Checklist" },
  { id: "pruebas_filtracion", title: "Pruebas" },
  { id: "anexos_fotograficos", title: "Fotos" },
  { id: "plan_mejora_firmas", title: "Cierre" },
];

// Estructura de cada Ítem de Chequeo de Planta
export interface ChecklistPlantaItemConfig {
  id: string;
  item_numero: number;
  sistema: string;
  componente: string;
}

// ─── LISTADO EXACTO DE LOS 105 ÍTEMS DE LA FICHA OFICIAL DE PLANTA ────────────
export const CHECKLIST_PLANTA_ITEMS: ChecklistPlantaItemConfig[] = [
  // 1. SISTEMA LUBRICACIÓN DE PLANTA ELECTRICA (9 ítems)
  {
    id: "lub_1",
    item_numero: 1,
    sistema: "1. Lubricación",
    componente: "Alarmas activas que impidan el arranque y puesta en servicio",
  },
  {
    id: "lub_2",
    item_numero: 2,
    sistema: "1. Lubricación",
    componente:
      "Nivel de aceite de la planta está dentro de las marcas Max y Min",
  },
  {
    id: "lub_3",
    item_numero: 3,
    sistema: "1. Lubricación",
    componente: "Juntas del motor de la planta",
  },
  {
    id: "lub_4",
    item_numero: 4,
    sistema: "1. Lubricación",
    componente: "Empaque y Retenedores de Carter",
  },
  {
    id: "lub_5",
    item_numero: 5,
    sistema: "1. Lubricación",
    componente: "Estado Pera o sensor de Aceite",
  },
  {
    id: "lub_6",
    item_numero: 6,
    sistema: "1. Lubricación",
    componente: "Presión de Aceite Kg/Cm2 o PSI (Indicar lectura)",
  },
  {
    id: "lub_7",
    item_numero: 7,
    sistema: "1. Lubricación",
    componente: "Evidencia de Diluido o contaminación",
  },
  {
    id: "lub_8",
    item_numero: 8,
    sistema: "1. Lubricación",
    componente: "Existencia de Fugas",
  },
  {
    id: "lub_9",
    item_numero: 9,
    sistema: "1. Lubricación",
    componente: "Presión de aceite a la temperatura de operación",
  },

  // 2. SISTEMA DE COMBUSTIBLE DE PLANTA ELECTRICA (15 ítems)
  {
    id: "comb_1",
    item_numero: 1,
    sistema: "2. Combustible",
    componente: "Conexiones de combustible (adecuadas y no presentan fugas)",
  },
  {
    id: "comb_2",
    item_numero: 2,
    sistema: "2. Combustible",
    componente: "Abrazaderas",
  },
  {
    id: "comb_3",
    item_numero: 3,
    sistema: "2. Combustible",
    componente: "Tanques de combustible (anclados adecuadamente)",
  },
  {
    id: "comb_4",
    item_numero: 4,
    sistema: "2. Combustible",
    componente:
      "Cantidad de contaminación por agua otros materiales extraños así como su calidad (densidad específica)",
  },
  {
    id: "comb_5",
    item_numero: 5,
    sistema: "2. Combustible",
    componente:
      "Las líneas de suministro de combustible de BAJA presión por: fugas, condición y seguridad",
  },
  {
    id: "comb_6",
    item_numero: 6,
    sistema: "2. Combustible",
    componente:
      "Las líneas de combustible del motor, bomba y filtros por fugas, condición y seguridad",
  },
  {
    id: "comb_7",
    item_numero: 7,
    sistema: "2. Combustible",
    componente:
      "Las líneas de suministro de combustible de ALTA presión por fugas, condición y seguridad",
  },
  {
    id: "comb_8",
    item_numero: 8,
    sistema: "2. Combustible",
    componente: "Revisar y registrar la presión de combustible",
  },
  {
    id: "comb_9",
    item_numero: 9,
    sistema: "2. Combustible",
    componente: "La restricción de combustible de entrada",
  },
  {
    id: "comb_10",
    item_numero: 10,
    sistema: "2. Combustible",
    componente: "Mangueras",
  },
  {
    id: "comb_11",
    item_numero: 11,
    sistema: "2. Combustible",
    componente: "Resultado de Limpieza",
  },
  {
    id: "comb_12",
    item_numero: 12,
    sistema: "2. Combustible",
    componente: "Bomba de Inyección",
  },
  {
    id: "comb_13",
    item_numero: 13,
    sistema: "2. Combustible",
    componente: "Bomba de Transferencia",
  },
  {
    id: "comb_14",
    item_numero: 14,
    sistema: "2. Combustible",
    componente: "Nivel Combustible",
  },
  {
    id: "comb_15",
    item_numero: 15,
    sistema: "2. Combustible",
    componente:
      "Estado válvulas de drenaje tanques (libres de objetos y se accionan fácilmente)",
  },

  // 3. SISTEMA DE ASPIRACION (6 ítems)
  {
    id: "asp_1",
    item_numero: 1,
    sistema: "3. Aspiración",
    componente:
      "Inspecciona las condiciones de las tomas de aire y los ductos y su correcta operación",
  },
  {
    id: "asp_2",
    item_numero: 2,
    sistema: "3. Aspiración",
    componente:
      "Revisa los filtros de aire por condición y seguridad, apretar las abrazaderas y los soportes como lo requieran",
  },
  {
    id: "asp_3",
    item_numero: 3,
    sistema: "3. Aspiración",
    componente:
      "Inspección de salida de turbocargador (de existir), boquilla y tubos por condiciones y seguridad",
  },
  {
    id: "asp_4",
    item_numero: 4,
    sistema: "3. Aspiración",
    componente:
      "Dar servicio a los respiradores del cárter y drenaje de la caja de aire como se requiera",
  },
  {
    id: "asp_5",
    item_numero: 5,
    sistema: "3. Aspiración",
    componente: "Revisar y registrar la restricción de aire de admisión",
  },
  {
    id: "asp_6",
    item_numero: 6,
    sistema: "3. Aspiración",
    componente: "Revisar y registrar la presión del cárter",
  },

  // 4. SISTEMA REFRIGERACIÓN DE PLANTA ELECTRICA (15 ítems)
  {
    id: "ref_1",
    item_numero: 1,
    sistema: "4. Refrigeración",
    componente: "Bomba de Agua",
  },
  {
    id: "ref_2",
    item_numero: 2,
    sistema: "4. Refrigeración",
    componente: "Revisar el nivel de refrigerante, rellenar como se requiera",
  },
  {
    id: "ref_3",
    item_numero: 3,
    sistema: "4. Refrigeración",
    componente: "Realizar la prueba de presión y revisar posibles fugas",
  },
  {
    id: "ref_4",
    item_numero: 4,
    sistema: "4. Refrigeración",
    componente:
      "Revisar la banda de la polea del ventilador por condiciones y tensión adecuada y ajustar o remplazar si es necesario",
  },
  {
    id: "ref_5",
    item_numero: 5,
    sistema: "4. Refrigeración",
    componente:
      "Revisar las mangueras y tubos de refrigerante por condiciones adecuadas y seguridad",
  },
  {
    id: "ref_6",
    item_numero: 6,
    sistema: "4. Refrigeración",
    componente:
      "Revisar el panal del radiador por arreglo y limpieza, condiciones y seguridad",
  },
  {
    id: "ref_7",
    item_numero: 7,
    sistema: "4. Refrigeración",
    componente:
      "Revisar los rodamientos de la polea del ventilador y la polea loca, y revisar las condiciones y seguridad de los soportes",
  },
  {
    id: "ref_8",
    item_numero: 8,
    sistema: "4. Refrigeración",
    componente:
      "Inspeccionar las aspas del ventilador, guardas y soporte por condiciones de seguridad, apretar los sujetadores",
  },
  {
    id: "ref_9",
    item_numero: 9,
    sistema: "4. Refrigeración",
    componente: "Estado de Termostato",
  },
  {
    id: "ref_10",
    item_numero: 10,
    sistema: "4. Refrigeración",
    componente: "Nivel de Refrigerante",
  },
  {
    id: "ref_11",
    item_numero: 11,
    sistema: "4. Refrigeración",
    componente:
      "Revisar y registrar la temperatura del refrigerante bajo condiciones de operación",
  },
  {
    id: "ref_12",
    item_numero: 12,
    sistema: "4. Refrigeración",
    componente: "Sensor de nivel de Refrigerante",
  },
  {
    id: "ref_13",
    item_numero: 13,
    sistema: "4. Refrigeración",
    componente: "Precalentador",
  },
  {
    id: "ref_14",
    item_numero: 14,
    sistema: "4. Refrigeración",
    componente: "Sensor de temperatura",
  },
  {
    id: "ref_15",
    item_numero: 15,
    sistema: "4. Refrigeración",
    componente: "Estado de ventilador",
  },

  // 5. SISTEMA DE ESCAPE Y ADMISIÓN PLANTA ELECTRICA (8 ítems)
  {
    id: "esc_1",
    item_numero: 1,
    sistema: "5. Escape",
    componente: "Múltiple de Escape",
  },
  {
    id: "esc_2",
    item_numero: 2,
    sistema: "5. Escape",
    componente:
      "Revisar los tubos de escape y sus conexiones donde sean accesibles, apretar sujetadores y tornillos de bridas",
  },
  {
    id: "esc_3",
    item_numero: 3,
    sistema: "5. Escape",
    componente: "Turboalimentador",
  },
  {
    id: "esc_4",
    item_numero: 4,
    sistema: "5. Escape",
    componente: "Revisar los soportes del silenciador, operar sus drenajes",
  },
  {
    id: "esc_5",
    item_numero: 5,
    sistema: "5. Escape",
    componente: "Tubería de Escape Exhosto",
  },
  {
    id: "esc_6",
    item_numero: 6,
    sistema: "5. Escape",
    componente:
      "Templetes Sistema de Escape (ajustados y sin signos de oxidación)",
  },
  {
    id: "esc_7",
    item_numero: 7,
    sistema: "5. Escape",
    componente: "Mangueras del Turboalimentador",
  },
  {
    id: "esc_8",
    item_numero: 8,
    sistema: "5. Escape",
    componente: "Estado tubería del filtro de aire",
  },

  // 6. SISTEMA ELECTRICO DE MOTOR OTROS COMPONENTES DEL ELECTROGENO PARA OPERAR (19 ítems)
  {
    id: "elec_1",
    item_numero: 1,
    sistema: "6. Eléctrico",
    componente:
      "Revisar los cables de la marcha del motor, alambres y conectores por condición y seguridad",
  },
  {
    id: "elec_2",
    item_numero: 2,
    sistema: "6. Eléctrico",
    componente:
      "Revisar y registrar el voltaje de flotación de las baterías de arranque y nivel de electrolito",
  },
  {
    id: "elec_3",
    item_numero: 3,
    sistema: "6. Eléctrico",
    componente:
      "Revisar el cargador de baterías por operación y salida Bornes de Batería",
  },
  {
    id: "elec_4",
    item_numero: 4,
    sistema: "6. Eléctrico",
    componente:
      "Revisar y registrar la corriente de funcionamiento de la marcha",
  },
  {
    id: "elec_5",
    item_numero: 5,
    sistema: "6. Eléctrico",
    componente: "Revisar los controles eléctricos, terminales de sensores",
  },
  {
    id: "elec_6",
    item_numero: 6,
    sistema: "6. Eléctrico",
    componente:
      "Revisar la operación del precalentador del agua, termostatos de control y el contactor de desconexión",
  },
  {
    id: "elec_7",
    item_numero: 7,
    sistema: "6. Eléctrico",
    componente: "Probar todos los dispositivos de protección del motor",
  },
  {
    id: "elec_8",
    item_numero: 8,
    sistema: "6. Eléctrico",
    componente: "Alternador y Correas",
  },
  {
    id: "elec_9",
    item_numero: 9,
    sistema: "6. Eléctrico",
    componente: "Motor de Arranque",
  },
  {
    id: "elec_10",
    item_numero: 10,
    sistema: "6. Eléctrico",
    componente: "Arnés o cableado de control",
  },
  {
    id: "elec_11",
    item_numero: 11,
    sistema: "6. Eléctrico",
    componente: "Tarjeta de Control",
  },
  {
    id: "elec_12",
    item_numero: 12,
    sistema: "6. Eléctrico",
    componente: "Elementos de Medición",
  },
  {
    id: "elec_13",
    item_numero: 13,
    sistema: "6. Eléctrico",
    componente: "Magnetic-Pickup",
  },
  {
    id: "elec_14",
    item_numero: 14,
    sistema: "6. Eléctrico",
    componente: "AVR Generador",
  },
  {
    id: "elec_15",
    item_numero: 15,
    sistema: "6. Eléctrico",
    componente: "Totalizador Planta Y DIMENSIONAMIENTO",
  },
  {
    id: "elec_16",
    item_numero: 16,
    sistema: "6. Eléctrico",
    componente: "Test De Lámparas, Leds Y Pilotos",
  },
  {
    id: "elec_17",
    item_numero: 17,
    sistema: "6. Eléctrico",
    componente: "Fusibles y Protecciones",
  },
  {
    id: "elec_18",
    item_numero: 18,
    sistema: "6. Eléctrico",
    componente: "Tarjeta De Control De Velocidad",
  },
  {
    id: "elec_19",
    item_numero: 19,
    sistema: "6. Eléctrico",
    componente: "Sensores y Manómetros",
  },

  // 7. GENERADOR (MECANICO / ELECTRICO) (12 ítems)
  {
    id: "gen_1",
    item_numero: 1,
    sistema: "7. Generador",
    componente: "Revisar y verificar los pernos de anclaje",
  },
  {
    id: "gen_2",
    item_numero: 2,
    sistema: "7. Generador",
    componente: "Revisar los tornillos del acoplamiento flexible",
  },
  {
    id: "gen_3",
    item_numero: 3,
    sistema: "7. Generador",
    componente:
      "Revisar las guardas del ventilador por condiciones y seguridad",
  },
  {
    id: "gen_4",
    item_numero: 4,
    sistema: "7. Generador",
    componente:
      "Revisar la pantalla de la toma de aire por limpieza de las líneas, condiciones y seguridad",
  },
  {
    id: "gen_5",
    item_numero: 5,
    sistema: "7. Generador",
    componente: "Revisar rodamientos",
  },
  {
    id: "gen_6",
    item_numero: 6,
    sistema: "7. Generador",
    componente:
      "Revisar las conexiones mecánicas por apriete, condiciones y seguridad",
  },
  {
    id: "gen_7",
    item_numero: 7,
    sistema: "7. Generador",
    componente: "Revisar y registrar el voltaje residual, en vacío y con carga",
  },
  {
    id: "gen_8",
    item_numero: 8,
    sistema: "7. Generador",
    componente:
      "Revisar el ensamble del excitador, estator y campos por limpieza de las líneas e integridad física",
  },
  {
    id: "gen_9",
    item_numero: 9,
    sistema: "7. Generador",
    componente:
      "Revisar las terminales de cables y alambres en el generador por condición y seguridad",
  },
  {
    id: "gen_10",
    item_numero: 10,
    sistema: "7. Generador",
    componente:
      "Revisar el rectificador rotativo y el supresor de onda por condición, conexiones y apriete del montaje",
  },
  {
    id: "gen_11",
    item_numero: 11,
    sistema: "7. Generador",
    componente:
      "Revisar el extremo del alojamiento de la campana por limpieza de líneas e interferencia de dispositivos",
  },
  {
    id: "gen_12",
    item_numero: 12,
    sistema: "7. Generador",
    componente: "Probar los dispositivos de protección del generador",
  },

  // 8. MODULO DE CONTROL (5 ítems)
  {
    id: "mod_1",
    item_numero: 1,
    sistema: "8. Control",
    componente:
      "Verificar la operación de los controles de encendido automático y control remoto",
  },
  {
    id: "mod_2",
    item_numero: 2,
    sistema: "8. Control",
    componente:
      "Verificar la operación y calibración de los instrumentos del generador y el motor",
  },
  {
    id: "mod_3",
    item_numero: 3,
    sistema: "8. Control",
    componente:
      "Verificar la operación del equipo de generación indicadores asociados, luces y alarmas",
  },
  {
    id: "mod_4",
    item_numero: 4,
    sistema: "8. Control",
    componente:
      "Revisar y ajustar como se requiera para real control de potencia real y reactiva sincronizada",
  },
  {
    id: "mod_5",
    item_numero: 5,
    sistema: "8. Control",
    componente:
      "Revisar y ajustar como se requiera la frecuencia y el voltaje del sistema",
  },

  // 9. TRANSFERENCIA AUTOMATICA (16 ítems)
  {
    id: "trans_1",
    item_numero: 1,
    sistema: "9. Transferencia",
    componente: "Estado del Tablero Metálico (Gabinete o Cofre) Y Puerta",
  },
  {
    id: "trans_2",
    item_numero: 2,
    sistema: "9. Transferencia",
    componente: "Terminales de Conductores",
  },
  {
    id: "trans_3",
    item_numero: 3,
    sistema: "9. Transferencia",
    componente: "Cableado (estado y organización)",
  },
  {
    id: "trans_4",
    item_numero: 4,
    sistema: "9. Transferencia",
    componente: "Contactores Principales",
  },
  {
    id: "trans_5",
    item_numero: 5,
    sistema: "9. Transferencia",
    componente: "Vigilantes de Tensión",
  },
  {
    id: "trans_6",
    item_numero: 6,
    sistema: "9. Transferencia",
    componente: "Totalizador",
  },
  {
    id: "trans_7",
    item_numero: 7,
    sistema: "9. Transferencia",
    componente: "Temporizadores",
  },
  {
    id: "trans_8",
    item_numero: 8,
    sistema: "9. Transferencia",
    componente: "Relevos",
  },
  {
    id: "trans_9",
    item_numero: 9,
    sistema: "9. Transferencia",
    componente: "Fusibles o Minibreakers",
  },
  {
    id: "trans_10",
    item_numero: 10,
    sistema: "9. Transferencia",
    componente: "Selectores",
  },
  {
    id: "trans_11",
    item_numero: 11,
    sistema: "9. Transferencia",
    componente: "Pulsadores",
  },
  {
    id: "trans_12",
    item_numero: 12,
    sistema: "9. Transferencia",
    componente: "Pilotos",
  },
  {
    id: "trans_13",
    item_numero: 13,
    sistema: "9. Transferencia",
    componente: "Contactos Auxiliares",
  },
  {
    id: "trans_14",
    item_numero: 14,
    sistema: "9. Transferencia",
    componente: "Tarjeta de Control",
  },
  {
    id: "trans_15",
    item_numero: 15,
    sistema: "9. Transferencia",
    componente: "Display y Módulo de Comunicación",
  },
  {
    id: "trans_16",
    item_numero: 16,
    sistema: "9. Transferencia",
    componente: "Protección sobretensiones y Transientes",
  },
];

export interface ChecklistPlantaItemState {
  estado: ChecklistPlantaEstado;
  causa: string;
  detectar: string;
  corregir: string;
}

// ─── CONFIGURACIÓN DE LAS CASILLAS FOTOGRÁFICAS DE PLANTA ────────────────────
export interface FotoSlotPlantaConfig {
  id: string;
  categoria: string;
  titulo: string;
}

export const FOTO_SLOTS_PLANTA: FotoSlotPlantaConfig[] = [
  // 1. Datos Principales de la Planta
  {
    id: "placa_planta",
    categoria: "1. Datos Principales",
    titulo: "1. Placa Planta",
  },
  {
    id: "placa_motor",
    categoria: "1. Datos Principales",
    titulo: "2. Placa Motor",
  },
  {
    id: "placa_generador",
    categoria: "1. Datos Principales",
    titulo: "3. Placa Generador",
  },
  {
    id: "panoramica_planta",
    categoria: "1. Datos Principales",
    titulo: "4. Panorámica de la Planta",
  },
  {
    id: "panoramica_motor",
    categoria: "1. Datos Principales",
    titulo: "5. Panorámica del Motor",
  },
  {
    id: "panoramica_generador",
    categoria: "1. Datos Principales",
    titulo: "6. Panorámica del Generador",
  },
  {
    id: "panoramica_cabina",
    categoria: "1. Datos Principales",
    titulo: "7. Panorámica de la Cabina",
  },
  {
    id: "panoramica_tarjeta_control",
    categoria: "1. Datos Principales",
    titulo: "8. Panorámica Tarjeta de Control",
  },
  {
    id: "horometro",
    categoria: "1. Datos Principales",
    titulo: "9. Horómetro",
  },

  // 2. Insumos del Preventivo
  {
    id: "insumos_filtros",
    categoria: "2. Insumos",
    titulo: "1. Panorámica de Filtros",
  },
  {
    id: "insumos_refrigerantes",
    categoria: "2. Insumos",
    titulo: "2. Panorámica de los Refrigerantes",
  },
  {
    id: "insumos_aceites",
    categoria: "2. Insumos",
    titulo: "3. Panorámica los Aceites",
  },

  // 3. Sistema de Combustible
  {
    id: "comb_mangueras_motor",
    categoria: "3. Combustible",
    titulo: "1. Mangueras Lado Motor",
  },
  {
    id: "comb_abrazaderas",
    categoria: "3. Combustible",
    titulo: "2. Abrazaderas",
  },
  {
    id: "comb_panoramica_tanque",
    categoria: "3. Combustible",
    titulo: "3. Panorámica Tanque de Combustible",
  },
  {
    id: "comb_drenaje_tanque",
    categoria: "3. Combustible",
    titulo: "4. Drenaje Tanque de Combustible",
  },
  {
    id: "comb_mangueras_tanque",
    categoria: "3. Combustible",
    titulo: "5. Mangueras Lado Tanque",
  },
  {
    id: "comb_nivel_combustible",
    categoria: "3. Combustible",
    titulo: "6. Nivel de Combustible",
  },
  {
    id: "comb_mirillas_nivel",
    categoria: "3. Combustible",
    titulo: "7. Estado Mirillas de Nivel Tanque",
  },
  {
    id: "comb_bomba_inyeccion",
    categoria: "3. Combustible",
    titulo: "8. Bomba de Inyección",
  },
  {
    id: "comb_filtro_en_tanque",
    categoria: "3. Combustible",
    titulo: "9. Filtro de Combustible en Tanque",
  },

  // 4. Sistema Refrigeración
  {
    id: "ref_drenaje_radiador",
    categoria: "4. Refrigeración",
    titulo: "1. Drenaje Refrigerante Radiador",
  },
  {
    id: "ref_liquido_drenado",
    categoria: "4. Refrigeración",
    titulo: "2. Líquido Drenado del Radiador",
  },
  {
    id: "ref_estado_refrigerante",
    categoria: "4. Refrigeración",
    titulo: "3. Estado del Refrigerante",
  },
  {
    id: "ref_suministro",
    categoria: "4. Refrigeración",
    titulo: "4. Suministro de Refrigerante",
  },
  {
    id: "ref_nivel",
    categoria: "4. Refrigeración",
    titulo: "5. Nivel del Refrigerante",
  },
  {
    id: "ref_temperatura",
    categoria: "4. Refrigeración",
    titulo: "6. Temperatura del Refrigerante",
  },

  // 5. Sistema de Escape y Admisión
  {
    id: "esc_multiple",
    categoria: "5. Escape y Admisión",
    titulo: "1. Múltiple de Escape",
  },
  {
    id: "esc_templetes",
    categoria: "5. Escape y Admisión",
    titulo: "2. Templetes Sistema de Escape",
  },
  {
    id: "esc_turboalimentador",
    categoria: "5. Escape y Admisión",
    titulo: "3. Turboalimentador",
  },

  // 6. Sistema Eléctrico Motor y Otros
  {
    id: "elec_panoramica_bateria",
    categoria: "6. Sistema Eléctrico",
    titulo: "1. Panorámica de la Batería",
  },
  {
    id: "elec_serial_bateria",
    categoria: "6. Sistema Eléctrico",
    titulo: "2. Serial de la Batería",
  },
  {
    id: "elec_voltaje_bateria",
    categoria: "6. Sistema Eléctrico",
    titulo: "3. Voltaje de la Batería",
  },
  {
    id: "elec_panoramica_arranque",
    categoria: "6. Sistema Eléctrico",
    titulo: "4. Panorámica del Arranque",
  },
  {
    id: "elec_panoramica_alternador",
    categoria: "6. Sistema Eléctrico",
    titulo: "5. Panorámica del Alternador",
  },
  {
    id: "elec_voltaje_alternador",
    categoria: "6. Sistema Eléctrico",
    titulo: "6. Voltaje del Alternador",
  },
  {
    id: "elec_panoramica_correa",
    categoria: "6. Sistema Eléctrico",
    titulo: "7. Panorámica de la Correa",
  },
  {
    id: "elec_panoramica_cargador",
    categoria: "6. Sistema Eléctrico",
    titulo: "8. Panorámica del Cargador",
  },
  {
    id: "elec_arnes_control",
    categoria: "6. Sistema Eléctrico",
    titulo: "9. Arnés o Cableado de Control",
  },
  {
    id: "elec_totalizador_dimensionamiento",
    categoria: "6. Sistema Eléctrico",
    titulo: "10. Totalizador y Dimensionamiento",
  },
  {
    id: "elec_spt",
    categoria: "6. Sistema Eléctrico",
    titulo: "11. SPT de la Planta",
  },
  {
    id: "elec_temporizador",
    categoria: "6. Sistema Eléctrico",
    titulo: "12. Temporizador",
  },

  // 7. Preventivo General (Cambio de Filtros)
  {
    id: "filtros_combustible_proceso",
    categoria: "7. Cambio Filtros",
    titulo: "1. Cambio Filtro Combustible (Antes)",
  },
  {
    id: "filtros_aceite_proceso",
    categoria: "7. Cambio Filtros",
    titulo: "2. Cambio Filtro Aceite (Antes)",
  },
  {
    id: "filtros_aire_proceso",
    categoria: "7. Cambio Filtros",
    titulo: "3. Cambio Filtro Aire (Antes)",
  },
  {
    id: "filtros_combustible_final",
    categoria: "7. Cambio Filtros",
    titulo: "4. Cambio Filtro Combustible (Final)",
  },
  {
    id: "filtros_aceite_final",
    categoria: "7. Cambio Filtros",
    titulo: "5. Cambio Filtro Aceite (Final)",
  },
  {
    id: "filtros_aire_final",
    categoria: "7. Cambio Filtros",
    titulo: "6. Cambio Filtro Aire (Final)",
  },

  // 8. Aceite y Lubricación
  {
    id: "lub_drenaje_aceite",
    categoria: "8. Aceite y Lubricación",
    titulo: "7. Drenaje de Aceite",
  },
  {
    id: "lub_suministro_aceite",
    categoria: "8. Aceite y Lubricación",
    titulo: "8. Suministro de Aceite",
  },
  {
    id: "lub_nivel_aceite",
    categoria: "8. Aceite y Lubricación",
    titulo: "9. Nivel de Aceite",
  },
  {
    id: "lub_presion_aceite",
    categoria: "8. Aceite y Lubricación",
    titulo: "10. Presión de Aceite",
  },

  // 9. Módulo de Control
  {
    id: "ctrl_velocidad_rpm",
    categoria: "9. Módulo Control",
    titulo: "1. Velocidad (RPM)",
  },
  {
    id: "ctrl_frecuencia_hz",
    categoria: "9. Módulo Control",
    titulo: "2. Frecuencia (Hz)",
  },
  { id: "ctrl_alarmas", categoria: "9. Módulo Control", titulo: "3. Alarmas" },

  // 10. Transferencia Automática
  {
    id: "trans_gabinete_cerrado",
    categoria: "10. Transferencia",
    titulo: "1. Gabinete Cerrado",
  },
  {
    id: "trans_gabinete_interno",
    categoria: "10. Transferencia",
    titulo: "2. Gabinete Interno",
  },
  {
    id: "trans_instrumentacion_control",
    categoria: "10. Transferencia",
    titulo: "3. Instrumentación / Tarjeta",
  },
  {
    id: "trans_contactores",
    categoria: "10. Transferencia",
    titulo: "4. Contactores",
  },
  {
    id: "trans_vigilante_tension",
    categoria: "10. Transferencia",
    titulo: "5. Vigilante de Tensión",
  },
  {
    id: "trans_totalizador",
    categoria: "10. Transferencia",
    titulo: "6. Totalizador",
  },
  {
    id: "trans_protector_dps",
    categoria: "10. Transferencia",
    titulo: "7. Protector DPS",
  },
  {
    id: "trans_spt",
    categoria: "10. Transferencia",
    titulo: "8. SPT Transferencia",
  },
  {
    id: "trans_fusibles_minibreakers",
    categoria: "10. Transferencia",
    titulo: "9. Fusibles / Minibreakers",
  },
  {
    id: "trans_pilotos_selectores",
    categoria: "10. Transferencia",
    titulo: "10. Pilotos / Selectores",
  },
  {
    id: "trans_ajuste_torque",
    categoria: "10. Transferencia",
    titulo: "11. Ajuste y Torque",
  },
  {
    id: "trans_borneras",
    categoria: "10. Transferencia",
    titulo: "12. Borneras",
  },

  // 11. Pruebas Realizadas
  {
    id: "prueba_carga_amp",
    categoria: "11. Pruebas",
    titulo: "1. Carga (AMP)",
  },
  {
    id: "prueba_voltaje_v",
    categoria: "11. Pruebas",
    titulo: "2. Voltaje (V)",
  },
  {
    id: "prueba_transferencia_automatica_foto",
    categoria: "11. Pruebas",
    titulo: "3. Transferencia Automática",
  },
  {
    id: "prueba_voltaje_l1_l2",
    categoria: "11. Pruebas",
    titulo: "4. Voltaje L1-L2",
  },
  {
    id: "prueba_voltaje_l1_l3",
    categoria: "11. Pruebas",
    titulo: "5. Voltaje L1-L3",
  },
  {
    id: "prueba_voltaje_l2_l3",
    categoria: "11. Pruebas",
    titulo: "6. Voltaje L2-L3",
  },
  {
    id: "prueba_carga_l1",
    categoria: "11. Pruebas",
    titulo: "7. Carga (AMP) L1",
  },
  {
    id: "prueba_carga_l2",
    categoria: "11. Pruebas",
    titulo: "8. Carga (AMP) L2",
  },
  {
    id: "prueba_carga_l3",
    categoria: "11. Pruebas",
    titulo: "9. Carga (AMP) L3",
  },
];

// Estructura de Hallazgo
export interface HallazgoPlantaData {
  id: string;
  descripcion: string;
  evidencia_1?: string;
  evidencia_1_file?: File;
  evidencia_2?: string;
  evidencia_2_file?: File;
  evidencia_3?: string;
  evidencia_3_file?: File;
  /**
   * Título de la caja de cada evidencia en el Excel; si está vacío manda la
   * `descripcion` del hallazgo (que hoy comparten las 3 fotos).
   */
  evidencia_1_descripcion?: string;
  evidencia_2_descripcion?: string;
  evidencia_3_descripcion?: string;
}

// Estructura de cada Planta Eléctrica
export interface PlantaElectricaData {
  id: string;
  nombre_unidad: string;

  // Fila 1: Equipo
  equipo_marca: string;
  equipo_modelo: string;
  equipo_serial: string;
  equipo_velocidad_motor: string;
  equipo_admision_aire: string;
  equipo_rpm: string;

  // Fila 2: Operación y Potencia
  equipo_horas_trabajo: string;
  equipo_frecuencia_hz: string;
  equipo_capacidad_kva: string;
  equipo_capacidad_kw: string;
  equipo_derrateo: string;
  equipo_capacidad_derrateo: string;

  // Fila 3: Motor
  motor_marca: string;
  motor_modelo: string;
  motor_serial: string;
  motor_presion_aceite: string;
  motor_temp_aceite: string;
  motor_temp_refrigerante: string;

  // Fila 4: Generador
  generador_marca: string;
  generador_modelo: string;
  generador_serial: string;
  generador_temp_ambiente: string;

  // Fila 5: Sistema de Baterías
  bateria_voltaje: string;
  bateria_capacidad: string;
  bateria_tipo: string;
  bateria_cantidad: string;
  bateria_estado: string;
  bateria_estado_cargador: string;

  // Fila 6: Parámetros Eléctricos
  param_vac_l1_l2: string;
  param_vac_l1_l3: string;
  param_vac_l2_l3: string;
  param_amp_l1: string;
  param_amp_l2: string;
  param_amp_l3: string;

  // Fila 7: Dimensionamiento / Cargabilidad
  dimensionamiento_capacidad_amp: string;
  dimensionamiento_carga_demanda: string;
  dimensionamiento_porc_carga: string;
}

export interface PruebasFiltracionPlantaData {
  // 4. Resultado de Pruebas
  prueba_vacio: ChecklistPlantaEstado;
  prueba_con_carga: ChecklistPlantaEstado;
  prueba_transferencia_automatica: ChecklistPlantaEstado;
  prueba_planta_forzada: ChecklistPlantaEstado;
  observaciones_pruebas: string;

  // 5. Servicio de Filtración
  cambio_aceite: EstadoFiltracion;
  cambio_filtros_aire: EstadoFiltracion;
  cambio_filtros_combustible: EstadoFiltracion;
  cambio_filtros_aceite: EstadoFiltracion;
  cambio_mangueras_precalentador: EstadoFiltracion;
  cambio_refrigerante: EstadoFiltracion;
  cambio_baterias: EstadoFiltracion;
  observaciones_filtracion: string;
}

export interface FormPreventivoPlantaData {
  // Paso 1: Datos Generales
  nombre_estacion: string;
  direccion: string;
  jefatura: string;
  zona_om: string;
  modalidad: string;
  estructura: string;
  orden_trabajo_tas: string;
  site_owner: string;
  region: string;
  cantidad_plantas: string;

  // Técnicos y Fechas
  responsable_1: Empleado | null;
  responsable_2: Empleado | null;
  coordinador_aliado: string;
  fecha_inicio: string;
  fecha_fin: string;

  // Paso 2: Datos Principales de Plantas (Dinámico)
  plantas: PlantaElectricaData[];

  // Paso 3: Lista de Chequeo General de Planta (105 ítems)
  checklist: Record<string, ChecklistPlantaItemState>;

  // Paso 4: Resultado de Pruebas y Servicio de Filtración
  pruebas_filtracion: PruebasFiltracionPlantaData;

  // Paso 5: Anexos Fotográficos
  fotos: Record<string, { file?: File; previewUrl?: string; nombre?: string }>;
  /**
   * Descripción escrita por el técnico para cada foto del paso 5: es el
   * título que encabeza su caja en el Excel (`rotulo_evidencia`). Va aparte
   * de `fotos` para que no cuente como foto cargada ni se pierda al
   * reemplazarla.
   */
  fotos_descripciones: Record<string, string>;

  // Paso 6: Plan de Mejora, Firmas y Certificaciones
  plan_mejora_estado: string;
  hallazgos: HallazgoPlantaData[];
  tecnico_nombre: string;
  tecnico_firma: string;
  reviso_nombre: string;
  reviso_firma: string;
  empresa: string;
  fecha_elaboracion_informe: string;
  certificado_tipo: string;
  certificado_categoria: string;
  foto_certificado_preview?: string;
  foto_certificado_file?: File;
  foto_sitio_preview?: string;
  foto_sitio_file?: File;
}

const defaultPlanta = (index: number): PlantaElectricaData => ({
  id: `planta-${Date.now()}-${index}`,
  nombre_unidad: `PLANTA ELÉCTRICA ${index}`,

  equipo_marca: "",
  equipo_modelo: "",
  equipo_serial: "",
  equipo_velocidad_motor: "",
  equipo_admision_aire: "",
  equipo_rpm: "",

  equipo_horas_trabajo: "",
  equipo_frecuencia_hz: "",
  equipo_capacidad_kva: "",
  equipo_capacidad_kw: "",
  equipo_derrateo: "",
  equipo_capacidad_derrateo: "",

  motor_marca: "",
  motor_modelo: "",
  motor_serial: "",
  motor_presion_aceite: "",
  motor_temp_aceite: "",
  motor_temp_refrigerante: "",

  generador_marca: "",
  generador_modelo: "",
  generador_serial: "",
  generador_temp_ambiente: "",

  bateria_voltaje: "",
  bateria_capacidad: "",
  bateria_tipo: "",
  bateria_cantidad: "",
  bateria_estado: "BUENO",
  bateria_estado_cargador: "BUENO",

  param_vac_l1_l2: "",
  param_vac_l1_l3: "",
  param_vac_l2_l3: "",
  param_amp_l1: "",
  param_amp_l2: "",
  param_amp_l3: "",

  dimensionamiento_capacidad_amp: "",
  dimensionamiento_carga_demanda: "",
  dimensionamiento_porc_carga: "",
});

const defaultChecklistInitialState = (): Record<
  string,
  ChecklistPlantaItemState
> => {
  return CHECKLIST_PLANTA_ITEMS.reduce<
    Record<string, ChecklistPlantaItemState>
  >((acc, item) => {
    acc[item.id] = {
      estado: "OK",
      causa: "",
      detectar: "",
      corregir: "",
    };
    return acc;
  }, {});
};

const initialPruebasFiltracion: PruebasFiltracionPlantaData = {
  prueba_vacio: "OK",
  prueba_con_carga: "OK",
  prueba_transferencia_automatica: "OK",
  prueba_planta_forzada: "OK",
  observaciones_pruebas: "",

  cambio_aceite: "SÍ",
  cambio_filtros_aire: "SÍ",
  cambio_filtros_combustible: "SÍ",
  cambio_filtros_aceite: "SÍ",
  cambio_mangueras_precalentador: "NO",
  cambio_refrigerante: "SÍ",
  cambio_baterias: "NO",
  observaciones_filtracion: "",
};

const initialFormData: FormPreventivoPlantaData = {
  nombre_estacion: "",
  direccion: "",
  jefatura: "",
  zona_om: "",
  modalidad: "",
  estructura: "",
  orden_trabajo_tas: "",
  site_owner: "",
  region: "",
  cantidad_plantas: "1",

  responsable_1: null,
  responsable_2: null,
  coordinador_aliado: "",
  fecha_inicio: "",
  fecha_fin: "",

  plantas: [defaultPlanta(1)],
  checklist: defaultChecklistInitialState(),
  pruebas_filtracion: initialPruebasFiltracion,

  fotos: {},
  fotos_descripciones: {},

  plan_mejora_estado: "",
  hallazgos: [
    {
      id: `hallazgo-1`,
      descripcion: "",
    },
  ],
  tecnico_nombre: "",
  tecnico_firma: "",
  reviso_nombre: "",
  reviso_firma: "",
  empresa: "",
  fecha_elaboracion_informe: "",
  certificado_tipo: "",
  certificado_categoria: "",
};

const FormPreventivoPlantaSlider: React.FC = () => {
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] =
    useState<FormPreventivoPlantaData>(initialFormData);
  const [checklistSearch, setChecklistSearch] = useState("");
  const [selectedSistemaFilter, setSelectedSistemaFilter] = useState<string>(
    FILTRO_TODOS_SISTEMAS,
  );
  const [selectedFotoCategory, setSelectedFotoCategory] =
    useState<string>(FILTRO_TODAS_FOTOS);
  const { submit, isLoading } = useFormSubmit<SmuPayload>();
  // Cubre TODO el guardado (subida de fotos + POST): `isLoading` de
  // useFormSubmit solo está en true durante el POST.
  const [enviando, setEnviando] = useState(false);

  const updateField = <K extends keyof FormPreventivoPlantaData>(
    field: K,
    value: FormPreventivoPlantaData[K],
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  // Sincronizar cantidad de plantas con el número de plantas en el formulario
  const handleCantidadPlantasChange = (val: string) => {
    const num = parseInt(val, 10);
    updateField("cantidad_plantas", val);
    if (!isNaN(num) && num >= 1 && num <= 10) {
      setFormData((prev) => {
        const currentCount = prev.plantas.length;
        if (num > currentCount) {
          const toAdd = Array.from({ length: num - currentCount }, (_, i) =>
            defaultPlanta(currentCount + i + 1),
          );
          return { ...prev, plantas: [...prev.plantas, ...toAdd] };
        } else if (num < currentCount) {
          return { ...prev, plantas: prev.plantas.slice(0, num) };
        }
        return prev;
      });
    }
  };

  // Handlers para agregar/eliminar/actualizar plantas manualmente
  const handleAddPlanta = () => {
    setFormData((prev) => {
      const newPlantas = [
        ...prev.plantas,
        defaultPlanta(prev.plantas.length + 1),
      ];
      return {
        ...prev,
        cantidad_plantas: String(newPlantas.length),
        plantas: newPlantas,
      };
    });
  };

  const handleRemovePlanta = (id: string) => {
    if (formData.plantas.length <= 1) return;
    setFormData((prev) => {
      const filtered = prev.plantas.filter((p) => p.id !== id);
      return {
        ...prev,
        cantidad_plantas: String(filtered.length),
        plantas: filtered,
      };
    });
  };

  const handleUpdatePlanta = (
    id: string,
    field: keyof PlantaElectricaData,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      plantas: prev.plantas.map((p) =>
        p.id === id ? { ...p, [field]: value } : p,
      ),
    }));
  };

  // Handler Pruebas y Filtración
  const handleUpdatePruebasFiltracion = (
    field: keyof PruebasFiltracionPlantaData,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      pruebas_filtracion: {
        ...prev.pruebas_filtracion,
        [field]: value,
      },
    }));
  };

  // Handlers Checklist Planta
  const handleUpdateChecklist = (
    itemId: string,
    field: keyof ChecklistPlantaItemState,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      checklist: {
        ...prev.checklist,
        [itemId]: {
          ...(prev.checklist[itemId] || {
            estado: "OK",
            causa: "",
            detectar: "",
            corregir: "",
          }),
          [field]: value,
        },
      },
    }));
  };

  const handleSetAllChecklistEstado = (estado: ChecklistPlantaEstado) => {
    setFormData((prev) => {
      const updated = { ...prev.checklist };
      CHECKLIST_PLANTA_ITEMS.forEach((item) => {
        updated[item.id] = {
          ...(updated[item.id] || { causa: "", detectar: "", corregir: "" }),
          estado,
        };
      });
      return { ...prev, checklist: updated };
    });
  };

  // Handlers Fotos
  const handleFotoDescripcion = (slotId: string, descripcion: string) => {
    setFormData((prev) => ({
      ...prev,
      fotos_descripciones: {
        ...prev.fotos_descripciones,
        [slotId]: descripcion,
      },
    }));
  };

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

  // Handlers Hallazgos
  const handleAddHallazgo = () => {
    setFormData((prev) => ({
      ...prev,
      hallazgos: [
        ...prev.hallazgos,
        { id: `hallazgo-${Date.now()}`, descripcion: "" },
      ],
    }));
  };

  const handleRemoveHallazgo = (id: string) => {
    if (formData.hallazgos.length <= 1) return;
    const hallazgo = formData.hallazgos.find((h) => h.id === id);
    if (hallazgo) {
      liberarPreviewUrl(hallazgo.evidencia_1);
      liberarPreviewUrl(hallazgo.evidencia_2);
      liberarPreviewUrl(hallazgo.evidencia_3);
    }
    setFormData((prev) => ({
      ...prev,
      hallazgos: prev.hallazgos.filter((h) => h.id !== id),
    }));
  };

  const handleUpdateHallazgo = (
    id: string,
    field: keyof HallazgoPlantaData,
    value: string,
  ) => {
    setFormData((prev) => ({
      ...prev,
      hallazgos: prev.hallazgos.map((h) =>
        h.id === id ? { ...h, [field]: value } : h,
      ),
    }));
  };

  const handleHallazgoFotoUpload = (
    hallazgoId: string,
    evidenciaKey: "evidencia_1" | "evidencia_2" | "evidencia_3",
    file: File,
  ) => {
    const hallazgo = formData.hallazgos.find((h) => h.id === hallazgoId);
    if (hallazgo && hallazgo[evidenciaKey]) {
      liberarPreviewUrl(hallazgo[evidenciaKey]);
    }
    const previewUrl = URL.createObjectURL(file);
    const fileKey = `${evidenciaKey}_file` as keyof HallazgoPlantaData;
    setFormData((prev) => ({
      ...prev,
      hallazgos: prev.hallazgos.map((h) =>
        h.id === hallazgoId
          ? { ...h, [evidenciaKey]: previewUrl, [fileKey]: file }
          : h,
      ),
    }));
  };

  const handleCertificadoFotoUpload = (
    field: "foto_certificado_preview" | "foto_sitio_preview",
    file: File,
  ) => {
    liberarPreviewUrl(formData[field]);
    const previewUrl = URL.createObjectURL(file);
    const fileField =
      field === "foto_certificado_preview"
        ? "foto_certificado_file"
        : "foto_sitio_file";
    setFormData((prev) => ({
      ...prev,
      [field]: previewUrl,
      [fileField]: file,
    }));
  };

  const handleCertificadoFotoRemove = (
    field: "foto_certificado_preview" | "foto_sitio_preview",
  ) => {
    liberarPreviewUrl(formData[field]);
    const fileField =
      field === "foto_certificado_preview"
        ? "foto_certificado_file"
        : "foto_sitio_file";
    setFormData((prev) => ({
      ...prev,
      [field]: undefined,
      [fileField]: undefined,
    }));
  };

  const sistemasList = [
    FILTRO_TODOS_SISTEMAS,
    ...Array.from(new Set(CHECKLIST_PLANTA_ITEMS.map((i) => i.sistema))),
  ];

  const filteredChecklistItems = CHECKLIST_PLANTA_ITEMS.filter((item) => {
    const matchesSistema =
      selectedSistemaFilter === FILTRO_TODOS_SISTEMAS ||
      item.sistema === selectedSistemaFilter;
    const matchesSearch =
      checklistSearch === "" ||
      item.componente.toLowerCase().includes(checklistSearch.toLowerCase()) ||
      item.sistema.toLowerCase().includes(checklistSearch.toLowerCase());
    return matchesSistema && matchesSearch;
  });

  const fotoCategories = [
    FILTRO_TODAS_FOTOS,
    ...Array.from(new Set(FOTO_SLOTS_PLANTA.map((f) => f.categoria))),
  ];

  const filteredFotoSlots = FOTO_SLOTS_PLANTA.filter((slot) => {
    if (selectedFotoCategory === FILTRO_TODAS_FOTOS) return true;
    return slot.categoria === selectedFotoCategory;
  });

  const fotosCargadasCount = Object.keys(formData.fotos).length;

  const tecnicoNombreMostrado = formData.responsable_1
    ? `${formData.responsable_1.nombre} ${formData.responsable_1.apellido}`
    : formData.tecnico_nombre;

  /**
   * Tras un guardado exitoso el formulario queda vacío y en el paso 1, listo
   * para una nueva actividad; si no, el botón seguiría activo con los mismos
   * datos y un segundo clic duplicaría el registro.
   */
  const reiniciarFormulario = () => {
    liberarPreviews(formData);
    setFormData(clonarEstadoInicial(initialFormData));
    setCurrentStep(0);
    setChecklistSearch("");
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
      const payload = buildPreventivoPlantaPayload(
        formData,
        CHECKLIST_PLANTA_ITEMS,
        pendientes,
      );
      await subirPendientes(pendientes);

      await submit(payload, {
        endpoint: SMU_ACTIVIDADES_ENDPOINT,
        method: "POST",
        onSuccess: (res) => {
          toast.success(
            `Preventivo de planta guardado${
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
    <FormStepSlider
      steps={stepsConfig}
      currentStep={currentStep}
      onStepChange={setCurrentStep}
      onSubmit={handleSubmit}
      submitLabel="Guardar Preventivo Planta"
      isSubmitting={isLoading || enviando}
    >
      {/* ── PASO 1: Datos Generales ── */}
      {currentStep === 0 && (
        <div className="space-y-6">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              Datos Generales de la Estación y Planta
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Complete la información básica del sitio, orden de trabajo y
              responsables.
            </p>
          </div>

          {/* Grilla 2 columnas alineada a la estructura de la ficha */}
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
            {/* Columna Izquierda */}
            <div className="space-y-4 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]">
              <h5 className="text-xs font-semibold tracking-wider text-gray-500 uppercase dark:text-gray-400">
                Ubicación y Clasificación
              </h5>

              <div>
                <Label>Nombre Estación Base *</Label>
                <Input
                  placeholder="Nombre de la estación base"
                  value={formData.nombre_estacion}
                  onChange={(e) =>
                    updateField("nombre_estacion", e.target.value)
                  }
                />
              </div>

              <div>
                <Label>Dirección o Ubicación</Label>
                <Input
                  placeholder="Dirección del sitio"
                  value={formData.direccion}
                  onChange={(e) => updateField("direccion", e.target.value)}
                />
              </div>

              <div>
                <Label>Nombre Jefatura</Label>
                <Input
                  placeholder="Nombre de la jefatura"
                  value={formData.jefatura}
                  onChange={(e) => updateField("jefatura", e.target.value)}
                />
              </div>

              <div>
                <Label>Zona O&M Claro</Label>
                <Input
                  placeholder="Zona O&M Claro"
                  value={formData.zona_om}
                  onChange={(e) => updateField("zona_om", e.target.value)}
                />
              </div>

              <div>
                <Label>Modalidad</Label>
                <Input
                  placeholder="Modalidad"
                  value={formData.modalidad}
                  onChange={(e) => updateField("modalidad", e.target.value)}
                />
              </div>
            </div>

            {/* Columna Derecha */}
            <div className="space-y-4 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]">
              <h5 className="text-xs font-semibold tracking-wider text-gray-500 uppercase dark:text-gray-400">
                Detalles Operativos y Estructura
              </h5>

              <div>
                <Label>Estructura</Label>
                <Input
                  placeholder="Tipo de estructura"
                  value={formData.estructura}
                  onChange={(e) => updateField("estructura", e.target.value)}
                />
              </div>

              <div>
                <Label>Orden de Trabajo o TAS</Label>
                <Input
                  placeholder="Número de OT o TAS"
                  value={formData.orden_trabajo_tas}
                  onChange={(e) =>
                    updateField("orden_trabajo_tas", e.target.value)
                  }
                />
              </div>

              <div>
                <Label>Site Owner</Label>
                <Input
                  placeholder="Propietario del sitio"
                  value={formData.site_owner}
                  onChange={(e) => updateField("site_owner", e.target.value)}
                />
              </div>

              <div>
                <Label>Región</Label>
                <Input
                  placeholder="Región"
                  value={formData.region}
                  onChange={(e) => updateField("region", e.target.value)}
                />
              </div>

              <div>
                <Label>Cantidad de Plantas</Label>
                <Input
                  type="number"
                  min="1"
                  max="10"
                  placeholder="1"
                  value={formData.cantidad_plantas}
                  onChange={(e) => handleCantidadPlantasChange(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Sección de Responsables y Fechas */}
          <div className="space-y-4 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]">
            <h5 className="text-xs font-semibold tracking-wider text-gray-500 uppercase dark:text-gray-400">
              Personal Técnico y Período de Ejecución
            </h5>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <Label>Responsable Técnico 1 *</Label>
                <EmployeeSearchInput
                  value={formData.responsable_1}
                  onChange={(emp) => updateField("responsable_1", emp)}
                  placeholder="Buscar técnico por nombre o cédula..."
                />
              </div>
              <div>
                <Label>Responsable Técnico 2</Label>
                <EmployeeSearchInput
                  value={formData.responsable_2}
                  onChange={(emp) => updateField("responsable_2", emp)}
                  placeholder="Buscar técnico por nombre o cédula..."
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <Label>Coordinador / Aliado</Label>
                <Input
                  placeholder="Nombre del coordinador"
                  value={formData.coordinador_aliado}
                  onChange={(e) =>
                    updateField("coordinador_aliado", e.target.value)
                  }
                />
              </div>
              <div>
                <Label>Fecha de Inicio</Label>
                <Input
                  type="datetime-local"
                  value={formData.fecha_inicio}
                  onChange={(e) => updateField("fecha_inicio", e.target.value)}
                />
              </div>
              <div>
                <Label>Fecha de Fin</Label>
                <Input
                  type="datetime-local"
                  value={formData.fecha_fin}
                  onChange={(e) => updateField("fecha_fin", e.target.value)}
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 2: Datos Principales de Plantas ── */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
                Datos Principales de Plantas
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Registro técnico del equipo, motor, generador, baterías,
                parámetros eléctricos y dimensionamiento.
              </p>
            </div>
            <button
              type="button"
              onClick={handleAddPlanta}
              className="border-brand-500/30 bg-brand-50/60 text-brand-600 hover:bg-brand-100/70 hover:border-brand-500 dark:border-brand-500/20 dark:bg-brand-950/40 dark:text-brand-400 dark:hover:bg-brand-900/60 inline-flex items-center gap-1.5 rounded-xl border px-3.5 py-2 text-xs font-semibold transition-all"
            >
              <Plus className="h-4 w-4" />
              Agregar Otra Planta
            </button>
          </div>

          {/* Listado dinámico de Plantas */}
          <div className="space-y-8">
            {formData.plantas.map((planta, index) => (
              <div
                key={planta.id}
                className="space-y-6 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition-all dark:border-gray-800 dark:bg-white/[0.02]"
              >
                {/* Cabecera de la Planta */}
                <div className="flex items-center justify-between border-b border-gray-100 pb-3 dark:border-gray-800">
                  <div className="flex items-center gap-2">
                    <span className="bg-brand-500/10 text-brand-600 dark:bg-brand-500/20 dark:text-brand-400 flex h-7 w-7 items-center justify-center rounded-lg text-xs font-bold">
                      {index + 1}
                    </span>
                    <h5 className="text-sm font-bold tracking-wider text-gray-800 uppercase dark:text-white/90">
                      PLANTA ELÉCTRICA {index + 1}
                    </h5>
                  </div>
                  {formData.plantas.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemovePlanta(planta.id)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-red-500 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
                    >
                      <Trash2 className="h-4 w-4" />
                      Eliminar Planta
                    </button>
                  )}
                </div>

                {/* Sub-bloque 1: Datos del Equipo y Capacidad */}
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
                    <Cpu className="text-brand-500 h-4 w-4" />
                    <span>Datos del Equipo y Potencia</span>
                  </div>

                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
                    <div>
                      <Label>Marca Equipo</Label>
                      <Input
                        placeholder="Marca del equipo"
                        value={planta.equipo_marca}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_marca",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Modelo</Label>
                      <Input
                        placeholder="Modelo"
                        value={planta.equipo_modelo}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_modelo",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Serial Nº</Label>
                      <Input
                        placeholder="Número de serial"
                        value={planta.equipo_serial}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_serial",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Velocidad Motor</Label>
                      <Input
                        placeholder="Velocidad del motor"
                        value={planta.equipo_velocidad_motor}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_velocidad_motor",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Admisión de Aire</Label>
                      <Input
                        placeholder="Estado admisión"
                        value={planta.equipo_admision_aire}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_admision_aire",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Velocidad (RPM)</Label>
                      <Input
                        placeholder="RPM"
                        value={planta.equipo_rpm}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_rpm",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                  </div>

                  {/* Fila 2: Horas, Frecuencia, Capacidad, Derrateo */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
                    <div>
                      <Label>Horas de Trabajo</Label>
                      <Input
                        placeholder="Horas"
                        value={planta.equipo_horas_trabajo}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_horas_trabajo",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Frecuencia (Hz)</Label>
                      <Input
                        placeholder="Frecuencia Hz"
                        value={planta.equipo_frecuencia_hz}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_frecuencia_hz",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Capacidad KVA</Label>
                      <Input
                        placeholder="KVA"
                        value={planta.equipo_capacidad_kva}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_capacidad_kva",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Capacidad KW</Label>
                      <Input
                        placeholder="KW"
                        value={planta.equipo_capacidad_kw}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_capacidad_kw",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>% Derrateo</Label>
                      <Input
                        placeholder="% Derrateo"
                        value={planta.equipo_derrateo}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_derrateo",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Capacidad c/ Derrateo</Label>
                      <Input
                        placeholder="Capacidad derrateada"
                        value={planta.equipo_capacidad_derrateo}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "equipo_capacidad_derrateo",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                  </div>
                </div>

                {/* Sub-bloque 2: Motor y Generador */}
                <div className="space-y-4 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]">
                  {/* Motor */}
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
                      <Gauge className="h-4 w-4 text-blue-500" />
                      <span>Motor</span>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
                      <div>
                        <Label>Marca Motor</Label>
                        <Input
                          placeholder="Marca del motor"
                          value={planta.motor_marca}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "motor_marca",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Modelo</Label>
                        <Input
                          placeholder="Modelo del motor"
                          value={planta.motor_modelo}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "motor_modelo",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Serial Nº</Label>
                        <Input
                          placeholder="Serial del motor"
                          value={planta.motor_serial}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "motor_serial",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Presión de Aceite</Label>
                        <Input
                          placeholder="Presión de aceite"
                          value={planta.motor_presion_aceite}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "motor_presion_aceite",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Temp. Aceite</Label>
                        <Input
                          placeholder="Temp. aceite"
                          value={planta.motor_temp_aceite}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "motor_temp_aceite",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Temp. Refrigerante</Label>
                        <Input
                          placeholder="Temp. refrigerante"
                          value={planta.motor_temp_refrigerante}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "motor_temp_refrigerante",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                    </div>
                  </div>

                  {/* Generador */}
                  <div className="space-y-3 border-t border-gray-200/60 pt-2 dark:border-gray-800/60">
                    <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
                      <Zap className="h-4 w-4 text-amber-500" />
                      <span>Generador</span>
                    </div>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
                      <div>
                        <Label>Marca Generador</Label>
                        <Input
                          placeholder="Marca del generador"
                          value={planta.generador_marca}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "generador_marca",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Modelo</Label>
                        <Input
                          placeholder="Modelo del generador"
                          value={planta.generador_modelo}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "generador_modelo",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Serial Nº</Label>
                        <Input
                          placeholder="Serial del generador"
                          value={planta.generador_serial}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "generador_serial",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                      <div>
                        <Label>Temperatura Ambiente</Label>
                        <Input
                          placeholder="Temp. ambiente"
                          value={planta.generador_temp_ambiente}
                          onChange={(e) =>
                            handleUpdatePlanta(
                              planta.id,
                              "generador_temp_ambiente",
                              e.target.value,
                            )
                          }
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Sub-bloque 3: Sistema de Baterías */}
                <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]">
                  <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
                    <BatteryCharging className="h-4 w-4 text-emerald-500" />
                    <span>Sistema de Baterías</span>
                  </div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
                    <div>
                      <Label>Voltaje Batería</Label>
                      <Input
                        placeholder="Voltaje (V)"
                        value={planta.bateria_voltaje}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "bateria_voltaje",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Capacidad Batería</Label>
                      <Input
                        placeholder="Capacidad (Ah / A)"
                        value={planta.bateria_capacidad}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "bateria_capacidad",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Tipo de Batería</Label>
                      <Input
                        placeholder="Tipo de batería"
                        value={planta.bateria_tipo}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "bateria_tipo",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Cantidad Batería</Label>
                      <Input
                        placeholder="Cantidad"
                        value={planta.bateria_cantidad}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "bateria_cantidad",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Estado Batería</Label>
                      <Select
                        options={OPCIONES_ESTADO}
                        value={planta.bateria_estado}
                        onChange={(val) =>
                          handleUpdatePlanta(planta.id, "bateria_estado", val)
                        }
                      />
                    </div>
                    <div>
                      <Label>Estado Cargador</Label>
                      <Select
                        options={OPCIONES_ESTADO}
                        value={planta.bateria_estado_cargador}
                        onChange={(val) =>
                          handleUpdatePlanta(
                            planta.id,
                            "bateria_estado_cargador",
                            val,
                          )
                        }
                      />
                    </div>
                  </div>
                </div>

                {/* Sub-bloque 4: Parámetros Eléctricos */}
                <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]">
                  <div className="flex items-center gap-2 text-xs font-semibold tracking-wider text-gray-600 uppercase dark:text-gray-300">
                    <Activity className="h-4 w-4 text-purple-500" />
                    <span>Parámetros Eléctricos</span>
                  </div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6">
                    <div>
                      <Label>VAC L1 - L2</Label>
                      <Input
                        placeholder="VAC L1-L2"
                        value={planta.param_vac_l1_l2}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "param_vac_l1_l2",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>VAC L1 - L3</Label>
                      <Input
                        placeholder="VAC L1-L3"
                        value={planta.param_vac_l1_l3}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "param_vac_l1_l3",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>VAC L2 - L3</Label>
                      <Input
                        placeholder="VAC L2-L3"
                        value={planta.param_vac_l2_l3}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "param_vac_l2_l3",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Amperios L1</Label>
                      <Input
                        placeholder="A L1"
                        value={planta.param_amp_l1}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "param_amp_l1",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Amperios L2</Label>
                      <Input
                        placeholder="A L2"
                        value={planta.param_amp_l2}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "param_amp_l2",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Amperios L3</Label>
                      <Input
                        placeholder="A L3"
                        value={planta.param_amp_l3}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "param_amp_l3",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                  </div>
                </div>

                {/* Sub-bloque 5: Dimensionamiento / Cargabilidad */}
                <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]">
                  <h5 className="text-xs font-semibold tracking-wider text-gray-500 uppercase dark:text-gray-400">
                    Dimensionamiento / Cargabilidad
                  </h5>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    <div>
                      <Label>Capacidad AMP (Nom)</Label>
                      <Input
                        placeholder="Capacidad nominal"
                        value={planta.dimensionamiento_capacidad_amp}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "dimensionamiento_capacidad_amp",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Carga Demandada (AMP)</Label>
                      <Input
                        placeholder="Carga demandada"
                        value={planta.dimensionamiento_carga_demanda}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "dimensionamiento_carga_demanda",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>% de Carga Planta</Label>
                      <Input
                        placeholder="Porcentaje de carga"
                        value={planta.dimensionamiento_porc_carga}
                        onChange={(e) =>
                          handleUpdatePlanta(
                            planta.id,
                            "dimensionamiento_porc_carga",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── PASO 3: Lista de Chequeo General Planta (105 Ítems Exactos) ── */}
      {currentStep === 2 && (
        <div className="space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
                Lista de Chequeo General de Planta (105 Puntos)
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Evaluación integral de los 9 subsistemas de planta eléctrica.
              </p>
            </div>

            {/* Acciones Rápidas */}
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => handleSetAllChecklistEstado("OK")}
                className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-500/30 bg-emerald-50/60 px-3 py-1.5 text-xs font-semibold text-emerald-700 transition-all hover:bg-emerald-100 dark:border-emerald-500/20 dark:bg-emerald-950/40 dark:text-emerald-400"
              >
                <CheckCheck className="h-4 w-4" />
                Marcar Todos OK
              </button>
              <button
                type="button"
                onClick={() => handleSetAllChecklistEstado("N/A")}
                className="inline-flex items-center gap-1.5 rounded-xl border border-gray-300 bg-gray-100 px-3 py-1.5 text-xs font-semibold text-gray-700 transition-all hover:bg-gray-200 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
              >
                <MinusCircle className="h-4 w-4" />
                Marcar Todos N/A
              </button>
            </div>
          </div>

          {/* Barra de Filtros y Búsqueda */}
          <div className="space-y-3">
            <div className="relative w-full">
              <Search className="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por nombre de componente o número de ítem..."
                value={checklistSearch}
                onChange={(e) => setChecklistSearch(e.target.value)}
                className="focus:border-brand-500 w-full rounded-xl border border-gray-200 bg-white py-2 pr-4 pl-9 text-xs text-gray-800 placeholder-gray-400 transition-colors focus:outline-none dark:border-gray-800 dark:bg-white/5 dark:text-white/90"
              />
            </div>

            {/* Selector de Sistema / Filtro */}
            <div className="flex scrollbar-thin items-center gap-1.5 overflow-x-auto pb-2">
              {sistemasList.map((sis) => (
                <button
                  key={sis}
                  type="button"
                  onClick={() => setSelectedSistemaFilter(sis)}
                  className={`rounded-lg px-2.5 py-1 text-xs font-medium whitespace-nowrap transition-colors ${
                    selectedSistemaFilter === sis
                      ? "bg-brand-500 text-white shadow-sm"
                      : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10"
                  }`}
                >
                  {sis}
                </button>
              ))}
            </div>
          </div>

          {/* Tabla / Lista de Chequeo Estilizada */}
          <div className="space-y-4">
            {filteredChecklistItems.map((item) => {
              const itemState = formData.checklist[item.id] || {
                estado: "OK",
                causa: "",
                detectar: "",
                corregir: "",
              };
              const isNoOk = itemState.estado === "NO OK";

              return (
                <div
                  key={item.id}
                  className={`rounded-2xl border p-4 transition-all ${
                    isNoOk
                      ? "border-red-200 bg-red-50/30 dark:border-red-900/40 dark:bg-red-950/10"
                      : "border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.02]"
                  }`}
                >
                  {/* Fila Principal: Sistema, Componente y Selector de Estado */}
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="flex flex-1 items-start gap-3">
                      <span className="flex h-6 min-w-[24px] shrink-0 items-center justify-center rounded-md bg-gray-100 px-1.5 text-xs font-semibold text-gray-600 dark:bg-white/10 dark:text-gray-300">
                        {item.item_numero}
                      </span>
                      <div>
                        <span className="text-brand-600 dark:text-brand-400 inline-block text-[11px] font-semibold tracking-wider uppercase">
                          {item.sistema}
                        </span>
                        <p className="text-sm font-medium text-gray-800 dark:text-white/90">
                          {item.componente}
                        </p>
                      </div>
                    </div>

                    {/* Botones de Estado Rápidos */}
                    <div className="flex shrink-0 items-center gap-1.5">
                      {ESTADOS_PRUEBA.map((est) => {
                        const isSelected = itemState.estado === est;
                        let btnStyle =
                          "bg-gray-100 text-gray-600 dark:bg-white/5 dark:text-gray-400";
                        if (isSelected) {
                          if (est === "OK")
                            btnStyle =
                              "bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-400/30";
                          else if (est === "NO OK")
                            btnStyle =
                              "bg-red-600 text-white shadow-sm ring-2 ring-red-400/30";
                          else
                            btnStyle =
                              "bg-gray-700 text-white shadow-sm ring-2 ring-gray-400/30 dark:bg-gray-600";
                        }

                        return (
                          <button
                            key={est}
                            type="button"
                            onClick={() =>
                              handleUpdateChecklist(item.id, "estado", est)
                            }
                            className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition-all ${btnStyle}`}
                          >
                            {est}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Campos adicionales: Causa Posible, Forma de Detectarlo, Forma de Corregirlo */}
                  <div className="mt-4 grid grid-cols-1 gap-3 border-t border-gray-100 pt-3 sm:grid-cols-3 dark:border-gray-800">
                    <div>
                      <Label>Causa Posible</Label>
                      <Input
                        placeholder="Descripción de la causa"
                        value={itemState.causa}
                        onChange={(e) =>
                          handleUpdateChecklist(
                            item.id,
                            "causa",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Forma de Detectarlo</Label>
                      <Input
                        placeholder="Método de detección"
                        value={itemState.detectar}
                        onChange={(e) =>
                          handleUpdateChecklist(
                            item.id,
                            "detectar",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                    <div>
                      <Label>Forma de Corregirlo</Label>
                      <Input
                        placeholder="Acción correctiva"
                        value={itemState.corregir}
                        onChange={(e) =>
                          handleUpdateChecklist(
                            item.id,
                            "corregir",
                            e.target.value,
                          )
                        }
                      />
                    </div>
                  </div>
                </div>
              );
            })}

            {filteredChecklistItems.length === 0 && (
              <div className="rounded-2xl border border-dashed border-gray-200 p-8 text-center dark:border-gray-800">
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  No se encontraron componentes que coincidan con la búsqueda o
                  filtro.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── PASO 4: Resultado de Pruebas y Servicio de Filtración ── */}
      {currentStep === 3 && (
        <div className="space-y-8">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              Resultado de Pruebas Operativas y Servicio de Filtración
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Registre las pruebas de funcionamiento de la planta y las
              actividades de cambio de insumos/filtros ejecutadas.
            </p>
          </div>

          {/* 4. Resultado de Pruebas */}
          <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.02]">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-3 dark:border-gray-800">
              <Activity className="text-brand-500 h-5 w-5" />
              <h5 className="text-sm font-bold tracking-wider text-gray-800 uppercase dark:text-white/90">
                4. Resultado de Pruebas
              </h5>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {[
                {
                  key: "prueba_vacio",
                  label: "1. Funcionamiento de la Planta en Vacío",
                },
                {
                  key: "prueba_con_carga",
                  label: "2. Funcionamiento de la Planta con Carga",
                },
                {
                  key: "prueba_transferencia_automatica",
                  label:
                    "3. Transferencia automática entre Red Comercial y Planta",
                },
                {
                  key: "prueba_planta_forzada",
                  label:
                    "4. Funcionamiento de planta forzada desde Transferencia (Manual)",
                },
              ].map((p) => {
                const val = formData.pruebas_filtracion[
                  p.key as keyof PruebasFiltracionPlantaData
                ] as string;
                return (
                  <div
                    key={p.key}
                    className="flex flex-col justify-between rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]"
                  >
                    <p className="mb-3 text-xs font-semibold text-gray-700 dark:text-gray-200">
                      {p.label}
                    </p>
                    <div className="flex items-center gap-2">
                      {ESTADOS_PRUEBA.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() =>
                            handleUpdatePruebasFiltracion(
                              p.key as keyof PruebasFiltracionPlantaData,
                              opt,
                            )
                          }
                          className={`flex-1 rounded-xl py-2 text-xs font-semibold transition-all ${
                            val === opt
                              ? opt === "OK"
                                ? "bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-400/30"
                                : opt === "NO OK"
                                  ? "bg-red-600 text-white shadow-sm ring-2 ring-red-400/30"
                                  : "bg-gray-700 text-white shadow-sm dark:bg-gray-600"
                              : "border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 dark:border-gray-700 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10"
                          }`}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            <div>
              <Label>Observaciones de Pruebas</Label>
              <Input
                placeholder="Observaciones adicionales de las pruebas de operación"
                value={formData.pruebas_filtracion.observaciones_pruebas}
                onChange={(e) =>
                  handleUpdatePruebasFiltracion(
                    "observaciones_pruebas",
                    e.target.value,
                  )
                }
              />
            </div>
          </div>

          {/* 5. Servicio de Filtración */}
          <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.02]">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-3 dark:border-gray-800">
              <Cpu className="text-brand-500 h-5 w-5" />
              <h5 className="text-sm font-bold tracking-wider text-gray-800 uppercase dark:text-white/90">
                5. Servicio de Filtración y Mantenimiento
              </h5>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { key: "cambio_aceite", label: "Cambio de Aceite" },
                {
                  key: "cambio_filtros_aire",
                  label: "Cambio de Filtros de Aire",
                },
                {
                  key: "cambio_filtros_combustible",
                  label: "Cambio de Filtros de Combustible",
                },
                {
                  key: "cambio_filtros_aceite",
                  label: "Cambio de Filtros de Aceite",
                },
                {
                  key: "cambio_mangueras_precalentador",
                  label: "Cambio Mangueras Precalentador",
                },
                {
                  key: "cambio_refrigerante",
                  label: "Cambio o Ajuste Refrigerante Diésel",
                },
                { key: "cambio_baterias", label: "Cambio de Baterías" },
              ].map((f) => {
                const val = formData.pruebas_filtracion[
                  f.key as keyof PruebasFiltracionPlantaData
                ] as string;
                return (
                  <div
                    key={f.key}
                    className="flex flex-col justify-between rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]"
                  >
                    <p className="mb-3 text-xs font-semibold text-gray-700 dark:text-gray-200">
                      {f.label}
                    </p>
                    <div className="flex items-center gap-2">
                      {ESTADOS_FILTRACION.map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() =>
                            handleUpdatePruebasFiltracion(
                              f.key as keyof PruebasFiltracionPlantaData,
                              opt,
                            )
                          }
                          className={`flex-1 rounded-xl py-1.5 text-xs font-semibold transition-all ${
                            val === opt
                              ? opt === "SÍ"
                                ? "bg-emerald-600 text-white shadow-sm ring-2 ring-emerald-400/30"
                                : opt === "NO"
                                  ? "bg-gray-600 text-white shadow-sm"
                                  : "bg-gray-700 text-white shadow-sm dark:bg-gray-600"
                              : "border border-gray-200 bg-white text-gray-600 hover:bg-gray-100 dark:border-gray-700 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10"
                          }`}
                        >
                          {opt}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            <div>
              <Label>Observaciones de Filtración</Label>
              <Input
                placeholder="Observaciones adicionales sobre cambios de filtros y fluidos"
                value={formData.pruebas_filtracion.observaciones_filtracion}
                onChange={(e) =>
                  handleUpdatePruebasFiltracion(
                    "observaciones_filtracion",
                    e.target.value,
                  )
                }
              />
            </div>
          </div>
        </div>
      )}

      {/* ── PASO 5: Anexos Fotográficos de Planta ── */}
      {currentStep === 4 && (
        <div className="space-y-6">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
                6. Soportes de Mantenimiento (Anexos Fotográficos)
              </h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Suba las evidencias fotográficas requeridas según cada categoría
                y sistema de la planta.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="rounded-xl border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-medium text-gray-700 dark:border-gray-800 dark:bg-white/5 dark:text-gray-300">
                📷{" "}
                <strong className="text-brand-600 dark:text-brand-400">
                  {fotosCargadasCount}
                </strong>{" "}
                de {FOTO_SLOTS_PLANTA.length} fotos cargadas
              </span>
            </div>
          </div>

          {/* Filtros de Categoría Fotográfica */}
          <div className="flex scrollbar-thin items-center gap-1.5 overflow-x-auto pb-2">
            {fotoCategories.map((cat) => (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedFotoCategory(cat)}
                className={`rounded-lg px-2.5 py-1 text-xs font-medium whitespace-nowrap transition-colors ${
                  selectedFotoCategory === cat
                    ? "bg-brand-500 text-white shadow-sm"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-white/5 dark:text-gray-300 dark:hover:bg-white/10"
                }`}
              >
                {cat}
              </button>
            ))}
          </div>

          {/* Grilla de Casillas de Fotos */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filteredFotoSlots.map((slot, idx) => {
              const foto = formData.fotos[slot.id];
              const inputId = `foto-input-${slot.id}`;

              return (
                <FotoSlotWithDescripcion
                  key={slot.id}
                  index={idx + 1}
                  titulo={`[${slot.categoria}] ${slot.titulo}`}
                  inputId={inputId}
                  previewUrl={foto?.previewUrl}
                  onUpload={(file) => file && handleFotoUpload(slot.id, file)}
                  onRemove={() => handleFotoRemove(slot.id)}
                  descripcion={formData.fotos_descripciones[slot.id] ?? ""}
                  onDescripcionChange={(valor) =>
                    handleFotoDescripcion(slot.id, valor)
                  }
                  descripcionLabel={`Descripción de la foto ${idx + 1}`}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* ── PASO 6: Plan de Mejora, Firmas y Certificaciones ── */}
      {currentStep === 5 && (
        <div className="space-y-8">
          <div>
            <h4 className="text-base font-semibold text-gray-800 dark:text-white/90">
              7. Plan de Mejora, Firmas y Certificaciones
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Registre el estado final del equipo, hallazgos fotográficos,
              firmas y validaciones técnicas.
            </p>
          </div>

          {/* Bloque 1: Plan de Mejora y Estado */}
          <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.02]">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-3 dark:border-gray-800">
              <FileCheck2 className="text-brand-500 h-5 w-5" />
              <h5 className="text-sm font-bold tracking-wider text-gray-800 uppercase dark:text-white/90">
                Plan de Mejora
              </h5>
            </div>

            <div>
              <Label>Estado Final de la Estación / EB</Label>
              <Input
                placeholder="Ej: Queda EB operativa"
                value={formData.plan_mejora_estado}
                onChange={(e) =>
                  updateField("plan_mejora_estado", e.target.value)
                }
              />
            </div>
          </div>

          {/* Bloque 2: Hallazgos con Evidencias Fotográficas */}
          <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.02]">
            <div className="flex items-center justify-between border-b border-gray-100 pb-3 dark:border-gray-800">
              <div className="flex items-center gap-2">
                <ShieldCheck className="text-brand-500 h-5 w-5" />
                <h5 className="text-sm font-bold tracking-wider text-gray-800 uppercase dark:text-white/90">
                  Hallazgos y Evidencias
                </h5>
              </div>
              <button
                type="button"
                onClick={handleAddHallazgo}
                className="border-brand-500/30 bg-brand-50/60 text-brand-600 hover:bg-brand-100 dark:border-brand-500/20 dark:bg-brand-950/40 dark:text-brand-400 inline-flex items-center gap-1.5 rounded-xl border px-3 py-1.5 text-xs font-semibold transition-all"
              >
                <Plus className="h-4 w-4" />
                Agregar Hallazgo
              </button>
            </div>

            <div className="space-y-6">
              {formData.hallazgos.map((h, hIdx) => (
                <div
                  key={h.id}
                  className="space-y-4 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800/80 dark:bg-white/[0.02]"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold tracking-wider text-gray-700 uppercase dark:text-gray-300">
                      Hallazgo #{hIdx + 1}
                    </span>
                    {formData.hallazgos.length > 1 && (
                      <button
                        type="button"
                        onClick={() => handleRemoveHallazgo(h.id)}
                        className="inline-flex items-center gap-1 text-xs text-red-500 hover:text-red-700"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                        Eliminar
                      </button>
                    )}
                  </div>

                  <div>
                    <Label>Descripción del Hallazgo</Label>
                    <TextArea
                      rows={2}
                      placeholder="Descripción detallada de la anomalía o trabajo requerido..."
                      value={h.descripcion}
                      onChange={(e) =>
                        handleUpdateHallazgo(
                          h.id,
                          "descripcion",
                          e.target.value,
                        )
                      }
                    />
                  </div>

                  {/* 3 Casillas de Evidencia por Hallazgo */}
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    {(
                      ["evidencia_1", "evidencia_2", "evidencia_3"] as const
                    ).map((evKey, evNum) => {
                      const inputEvId = `ev-${h.id}-${evKey}`;
                      const evUrl = h[evKey];

                      return (
                        <FotoSlotWithDescripcion
                          key={evKey}
                          index={evNum + 1}
                          titulo={`Evidencia ${evNum + 1}`}
                          inputId={inputEvId}
                          previewUrl={evUrl}
                          onUpload={(file) =>
                            file && handleHallazgoFotoUpload(h.id, evKey, file)
                          }
                          onRemove={() => {
                            liberarPreviewUrl(evUrl);
                            handleUpdateHallazgo(h.id, evKey, "");
                          }}
                          descripcion={
                            h[`${evKey}_descripcion`] ?? h.descripcion
                          }
                          onDescripcionChange={(valor) =>
                            handleUpdateHallazgo(
                              h.id,
                              `${evKey}_descripcion`,
                              valor,
                            )
                          }
                          descripcionLabel={`Descripción de la evidencia ${evNum + 1}`}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Bloque 3: Firmas y Personal Responsable */}
          <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.02]">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-3 dark:border-gray-800">
              <PenTool className="text-brand-500 h-5 w-5" />
              <h5 className="text-sm font-bold tracking-wider text-gray-800 uppercase dark:text-white/90">
                Firmas y Responsables de Entrega
              </h5>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {/* Personal quien ejecuta */}
              <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/[0.02]">
                <span className="text-brand-600 dark:text-brand-400 text-xs font-bold tracking-wider uppercase">
                  PERSONAL QUIEN EJECUTA
                </span>
                <div>
                  <Label>Nombre Técnico</Label>
                  <Input
                    value={tecnicoNombreMostrado}
                    onChange={(e) =>
                      updateField("tecnico_nombre", e.target.value)
                    }
                    placeholder="Nombre completo"
                  />
                </div>
                <div>
                  <Label>Firma del Técnico</Label>
                  <Input
                    value={formData.tecnico_firma}
                    onChange={(e) =>
                      updateField("tecnico_firma", e.target.value)
                    }
                    placeholder="Firma / Registro"
                  />
                </div>
              </div>

              {/* Personal quien revisa */}
              <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/[0.02]">
                <span className="text-brand-600 dark:text-brand-400 text-xs font-bold tracking-wider uppercase">
                  PERSONAL QUIEN REVISA
                </span>
                <div>
                  <Label>Nombre de quien revisa</Label>
                  <Input
                    value={formData.reviso_nombre}
                    onChange={(e) =>
                      updateField("reviso_nombre", e.target.value)
                    }
                    placeholder="Nombre de quien revisa"
                  />
                </div>
                <div>
                  <Label>Firma</Label>
                  <Input
                    value={formData.reviso_firma}
                    onChange={(e) =>
                      updateField("reviso_firma", e.target.value)
                    }
                    placeholder="Firma de quien revisa"
                  />
                </div>
              </div>

              {/* Empresa y Fecha */}
              <div className="space-y-3 rounded-xl border border-gray-100 bg-gray-50/50 p-4 dark:border-gray-800 dark:bg-white/[0.02]">
                <span className="text-brand-600 dark:text-brand-400 text-xs font-bold tracking-wider uppercase">
                  EMPRESA Y FECHA
                </span>
                <div>
                  <Label>Empresa quien ejecuta</Label>
                  <Input
                    value={formData.empresa}
                    onChange={(e) => updateField("empresa", e.target.value)}
                    placeholder="Nombre de la empresa"
                  />
                </div>
                <div>
                  <Label>Fecha Elaboración del Informe</Label>
                  <Input
                    type="date"
                    value={formData.fecha_elaboracion_informe}
                    onChange={(e) =>
                      updateField("fecha_elaboracion_informe", e.target.value)
                    }
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Bloque 4: Certificado Técnico (Tarjeta CONTE) y Foto en Sitio */}
          <div className="space-y-4 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-800 dark:bg-white/[0.02]">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-3 dark:border-gray-800">
              <ShieldCheck className="text-brand-500 h-5 w-5" />
              <h5 className="text-sm font-bold tracking-wider text-gray-800 uppercase dark:text-white/90">
                Certificación y Evidencia en Sitio
              </h5>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div>
                <Label>Certificado</Label>
                <Input
                  value={formData.certificado_tipo}
                  onChange={(e) =>
                    updateField("certificado_tipo", e.target.value)
                  }
                  placeholder="Tipo de certificado"
                />
              </div>

              <div>
                <Label>Técnico Certificado</Label>
                <Input
                  value={tecnicoNombreMostrado}
                  disabled
                  placeholder="Nombre del técnico"
                  className="bg-gray-100/60 dark:bg-gray-800/60"
                />
              </div>

              <div>
                <Label>Categoría / Matrícula</Label>
                <Input
                  value={formData.certificado_categoria}
                  onChange={(e) =>
                    updateField("certificado_categoria", e.target.value)
                  }
                  placeholder="Categoría"
                />
              </div>

              {/* Foto Certificado */}
              <FotoSlotCard
                index={1}
                titulo="Foto Certificado / Tarjeta"
                previewUrl={formData.foto_certificado_preview}
                inputId="foto-certificado-input"
                onUpload={(file) =>
                  file &&
                  handleCertificadoFotoUpload("foto_certificado_preview", file)
                }
                onRemove={() =>
                  handleCertificadoFotoRemove("foto_certificado_preview")
                }
              />
            </div>

            {/* Foto Después / Técnico en Sitio */}
            <div className="border-t border-gray-100 pt-2 dark:border-gray-800">
              <div className="max-w-xs">
                <FotoSlotCard
                  index={2}
                  titulo="Foto Después / Técnico en Sitio"
                  previewUrl={formData.foto_sitio_preview}
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
        </div>
      )}
    </FormStepSlider>
  );
};

export default FormPreventivoPlantaSlider;
