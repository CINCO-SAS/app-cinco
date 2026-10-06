// frontend/tests/smu.service.test.ts
//
// Tests de los builders de payload de SMU: son funciones puras que traducen el
// estado del formulario a las secciones anidadas que espera el serializer del
// backend. Aquí se protege lo que se pierde *silenciosamente*: campos que el
// backend exige, normalización de choices y descarte de basura (blob:/vacíos).
//
// Ejecución: node --import ./tests/register-alias.mjs --test tests/*.test.ts

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import {
  buildCapexTipologia1Payload,
  buildCapexTipologia3Payload,
  buildCapexTipologia5Payload,
  buildCorrectivoEmergenciaPayload,
  buildPreventivoAAPayload,
  buildPreventivoPlantaPayload,
  subirPendientes,
  ErrorSubidaFotos,
  preCargarFotoSMU,
  olvidarPrecargaSMU,
  limpiarPrecargasSMU,
  validarFechasEncabezado,
  type PendienteSubida,
} from "../src/services/smu.service";
import {
  fotoElegida,
  olvidarFotoElegida,
  registrarPrecargaFoto,
  desregistrarPrecargaFoto,
} from "../src/lib/precargaFoto";
import {
  CLAVES_ACCIONES_AA,
  ORIGEN_MATERIAL_OPERARIO,
} from "../src/modules/smu/constants";

import type { PreventivoAAFormData } from "../src/modules/smu/components/preventivos/FormPreventivoAASlider";
import type {
  ChecklistPlantaItemConfig,
  FormPreventivoPlantaData,
} from "../src/modules/smu/components/preventivos/FormPreventivoPlantaSlider";
import type { FormCorrectivoEmergenciaData } from "../src/modules/smu/components/correctivos/FormCorrectivoEmergenciaSlider";
import { quitarFotoEvidencia } from "../src/modules/smu/evidencias";
import type { FormCapexTipologia1Data } from "../src/modules/smu/components/capex/tipologia1/types";
import type { FormCapexTipologia3Data } from "../src/modules/smu/components/capex/tipologia3/types";
import type { FormCapexTipologia5Data } from "../src/modules/smu/components/capex/tipologia5/types";

const responsable = {
  cedula: "1020304050",
  nombre: "Ana",
  apellido: "Torres",
};

// ─── Preventivo Aire Acondicionado ────────────────────────────────────────────

describe("buildPreventivoAAPayload", () => {
  const baseAA = {
    nombre_estacion: "  ESTACIÓN CENTRO  ",
    codigo_ot: "   ",
    departamento: "Antioquia",
    responsable_1: responsable,
    fotos: {},
    checklist: { 1: "Si", 2: "No", 3: "No Aplica" },
    acciones_mantenimiento: [
      Object.fromEntries(
        CLAVES_ACCIONES_AA.map((clave, i) => [
          clave,
          i % 3 === 0 ? "SÍ" : i % 3 === 1 ? "NO" : "N/A",
        ]),
      ),
    ],
    compresores: [
      // El formulario llama `ampl1` (FormPreventivoAASlider.tsx:111);
      // el builder lo renombra a `amp_l1` para el backend.
      { marca: "Danfoss", ampl1: "12,5" },
      { marca: "", serial: "" },
    ],
    condensadoras: [],
    manejadoras: [],
    certificado: {},
    voltaje_entrada: "220,5",
    capacidad_btu: "18000",
    cantidad_compresores: "1.800",
    temp_cuarto: "21,5",
  };

  const build = (extra: Record<string, unknown> = {}) =>
    buildPreventivoAAPayload({
      ...baseAA,
      ...extra,
    } as unknown as PreventivoAAFormData);

  test("escribe la cabecera y recorta la estación", () => {
    const payload = build();

    assert.equal(payload.categoria, "preventivos");
    assert.equal(payload.tipo_formulario, "aire_acondicionado");
    assert.equal(payload.nombre_estacion, "ESTACIÓN CENTRO");
    assert.equal(payload.departamento, "Antioquia");
    // Campo con solo espacios: limpio() lo elimina en vez de enviar "".
    assert.ok(!("codigo_ot" in payload));
  });

  test("arma responsable desde el empleado (cedula + nombre completo)", () => {
    const payload = build();

    assert.equal(payload.responsable_cedula, "1020304050");
    assert.equal(payload.responsable_nombre, "Ana Torres");
    // El técnico principal de la ficha va a su propia colección.
    assert.deepEqual(payload.tecnicos, [
      { cedula: "1020304050", nombre: "Ana Torres", es_principal: true },
    ]);
  });

  test("sin responsable_1 cae en tecnico_nombre y no inventa cédula", () => {
    const payload = build({ responsable_1: null, tecnico_nombre: "Operador 9" });

    assert.equal(payload.responsable_nombre, "Operador 9");
    assert.ok(!("responsable_cedula" in payload));
    // tecnicos vacío también lo descarta limpio() en lugar de mandar [].
    assert.ok(!("tecnicos" in payload));
  });

  test("normaliza el checklist al rango del backend (SI/NO/NA)", () => {
    const payload = build();

    assert.deepEqual(payload.checklist_aa, [
      { item_numero: 1, estado: "SI" },
      { item_numero: 2, estado: "NO" },
      { item_numero: 3, estado: "NA" },
    ]);
  });

  test("emite las 11 claves de acciones AA con orden y sin tildes", () => {
    const payload = build();

    const acciones = payload.aa_acciones as Array<{
      clave: string;
      valor: string;
      orden: number;
    }>;
    assert.equal(acciones.length, CLAVES_ACCIONES_AA.length);
    assert.deepEqual(
      acciones.map((a) => a.clave),
      [...CLAVES_ACCIONES_AA],
    );
    assert.ok(acciones.every((a) => a.orden === 1));
    // opcion(): 'SÍ' → 'SI' y 'N/A' → 'NA' (choices del modelo).
    assert.deepEqual(
      new Set(acciones.map((a) => a.valor)),
      new Set(["SI", "NO", "NA"]),
    );
    assert.ok(!("id" in acciones[0]));
  });

  test("convierte números en formato español y descarta filas vacías", () => {
    const payload = build();
    const detalle = payload.detalle_preventivo_aa as Record<string, unknown>;

    assert.equal(detalle.voltaje_entrada, 220.5);
    assert.equal(detalle.capacidad_btu, 18000);
    assert.equal(detalle.temp_cuarto, 21.5);
    // "1.800" son mil, no 1.8
    assert.equal(detalle.cantidad_compresores, 1800);

    const compresores = payload.aa_compresores as Array<Record<string, unknown>>;
    assert.equal(compresores.length, 1);
    assert.equal(compresores[0].amp_l1, 12.5);
    assert.ok(!("temp_cuarto" in compresores[0]));
  });

  test("las colecciones vacías no viajan en el payload", () => {
    const payload = build();

    assert.ok(!("aa_condensadoras" in payload));
    assert.ok(!("aa_manejadoras" in payload));
    assert.ok(!("evidencias" in payload));
    assert.ok(!("firmas_cierre" in payload));
    assert.ok(!("certificados" in payload));
  });

  test("la descripción escrita para una foto viaja como su rótulo", () => {
    const payload = build({
      fotos: {
        condensadora_pos_mantenimiento: {
          previewUrl: "https://cdn.cinco.co/foto1.jpg",
          nombre: "foto1.jpg",
        },
      },
      fotos_descripciones: { condensadora_pos_mantenimiento: "Fuga en SC/PC" },
    });

    const evidencias = payload.evidencias as Array<Record<string, string>>;
    assert.equal(evidencias.length, 1);
    assert.equal(evidencias[0].campo_origen, "condensadora_pos_mantenimiento");
    assert.equal(evidencias[0].descripcion, "Fuga en SC/PC");
  });
});

// ─── Preventivo Planta Eléctrica ──────────────────────────────────────────────

describe("buildPreventivoPlantaPayload", () => {
  const catalogo: ChecklistPlantaItemConfig[] = [
    {
      id: "s1",
      item_numero: 1,
      sistema: "Generación",
      componente: "Grupos electrógenos",
    },
    {
      id: "s2",
      item_numero: 2,
      sistema: "Transmisión",
      componente: "Línea MT",
    },
  ];

  const basePlanta = {
    nombre_estacion: "PLANTA NORTE",
    region: "Caribe",
    responsable_1: responsable,
    fotos: {},
    checklist: {},
    hallazgos: [],
    plantas: [],
    pruebas_filtracion: {
      prueba_vacio: "OK",
      prueba_con_carga: "NO OK",
      cambio_aceite: "SÍ",
      cambio_filtros_aire: "N/A",
    },
  };

  const build = (extra: Record<string, unknown> = {}, cat = catalogo) =>
    buildPreventivoPlantaPayload(
      { ...basePlanta, ...extra } as unknown as FormPreventivoPlantaData,
      cat,
    );

  test("usa tipo_formulario planta y mapea region → regional", () => {
    const payload = build();

    assert.equal(payload.categoria, "preventivos");
    assert.equal(payload.tipo_formulario, "planta");
    assert.equal(payload.regional, "Caribe");
    assert.equal(payload.responsable_cedula, "1020304050");
  });

  test("conserva las tildes de filtración (choices 'SÍ'/'NO'/'N/A')", () => {
    const payload = build();
    const detalle = payload.detalle_preventivo_planta as Record<string, unknown>;

    // Pruebas: OK/NO OK tal cual; filtración: con tilde (a diferencia de AA).
    assert.equal(detalle.prueba_con_carga, "NO OK");
    assert.equal(detalle.cambio_aceite, "SÍ");
    assert.equal(detalle.cambio_filtros_aire, "N/A");
  });

  test("solo emite ítems del checklist con estado y con sistema/componente", () => {
    const payload = build({
      checklist: {
        s1: { estado: "OK", causa: "Sin novedad" },
        // s2 sin estado → fuera; y una fila sin sistema no puede violar la unique.
      },
    });

    assert.deepEqual(payload.checklist_planta, [
      {
        sistema: "Generación",
        componente: "Grupos electrógenos",
        estado: "OK",
        causa: "Sin novedad",
      },
    ]);
  });

  test("los ítems del catálogo sin estado no viajan", () => {
    const payload = build();

    assert.ok(!("checklist_planta" in payload));
  });

  test("las fotos blob: se guardan como PENDIENTE_SUBIDA", () => {
    const payload = build({
      fotos: { foto_1: { nombre: "planta.jpg" } },
      hallazgos: [
        {
          descripcion: "Fuga en tablero",
          evidencia_1: "blob:http://localhost/abc-123",
        },
      ],
    });

    const evidencias = payload.evidencias as Array<Record<string, string>>;
    assert.equal(evidencias.length, 2);
    assert.equal(evidencias[0].seccion, "anexos_planta");
    assert.equal(evidencias[0].campo_origen, "foto_1");
    assert.equal(evidencias[0].ruta_archivo, "PENDIENTE_SUBIDA");
    assert.equal(evidencias[0].nombre_original, "planta.jpg");
    assert.equal(evidencias[1].seccion, "hallazgos_planta");
    assert.equal(evidencias[1].ruta_archivo, "PENDIENTE_SUBIDA");
    assert.equal(evidencias[1].descripcion, "Fuga en tablero");
    // conOrden(): numeración continua para el ordering del backend.
    assert.deepEqual(
      evidencias.map((e) => e.orden),
      ["1", "2"].map(Number),
    );

    assert.deepEqual(payload.hallazgos_planta, [
      { orden: 1, descripcion: "Fuga en tablero" },
    ]);
  });

  test("la descripción de la foto manda sobre la del hallazgo", () => {
    const payload = build({
      fotos: {
        panoramica_motor: {
          previewUrl: "https://cdn.cinco.co/panoramica.jpg",
          nombre: "panoramica.jpg",
        },
      },
      fotos_descripciones: { panoramica_motor: "Holgura en el acople" },
      hallazgos: [
        {
          descripcion: "Fuga en tablero",
          evidencia_1: "https://cdn.cinco.co/ev1.jpg",
          evidencia_2: "https://cdn.cinco.co/ev2.jpg",
          evidencia_1_descripcion: "Conector suelto",
        },
      ],
    });

    const evidencias = payload.evidencias as Array<Record<string, string>>;
    const porCampo = Object.fromEntries(
      evidencias.map((e) => [e.campo_origen, e]),
    );

    assert.equal(porCampo.panoramica_motor.descripcion, "Holgura en el acople");
    // Cada evidencia del hallazgo puede llevar su propio título...
    assert.equal(
      porCampo.hallazgo_1_evidencia_1.descripcion,
      "Conector suelto",
    );
    // ...y la que no lo tiene sigue usando el texto del hallazgo.
    assert.equal(
      porCampo.hallazgo_1_evidencia_2.descripcion,
      "Fuga en tablero",
    );
  });
});

// ─── Correctivo / Emergencia ──────────────────────────────────────────────────

describe("buildCorrectivoEmergenciaPayload", () => {
  const baseCorrectivo = {
    nombre_estacion: "ESTACIÓN SUR",
    responsable_1: responsable,
    implica_exclusion: "NO",
    evidencias: [],
    materiales: [
      {
        origen_material: "CINCO SAS",
        descripcion: "Filtro Aire",
        cantidad: "2",
        tipo_unidad: "UND",
      },
      {
        origen_material: ORIGEN_MATERIAL_OPERARIO,
        descripcion: "Cable 12mm",
        cantidad: "5,5",
        tipo_unidad: "METROS",
      },
      { descripcion: "   " },
    ],
  };

  const build = (
    categoria: "correctivos" | "emergencias",
    extra: Record<string, unknown> = {},
  ) =>
    buildCorrectivoEmergenciaPayload(
      { ...baseCorrectivo, ...extra } as unknown as FormCorrectivoEmergenciaData,
      categoria,
    );

  test("la categoría llega como parámetro y cambia el tipo de material", () => {
    const correctivo = build("correctivos");
    const emergencia = build("emergencias");

    assert.equal(correctivo.categoria, "correctivos");
    assert.equal(emergencia.categoria, "emergencias");
    assert.equal(correctivo.tipo_formulario, "estandar");

    const materiales = (p: Record<string, unknown>) =>
      (p.materiales as Array<Record<string, unknown>>).map(
        (m) => m.tipo_registro,
      );
    assert.deepEqual(materiales(correctivo), [
      "material_correctivo",
      "material_correctivo",
    ]);
    assert.deepEqual(materiales(emergencia), [
      "material_emergencia",
      "material_emergencia",
    ]);
  });

  test("comprado_operario solo se activa con el origen de sitio", () => {
    const payload = build("emergencias");
    const materiales = payload.materiales as Array<Record<string, unknown>>;

    // El tercer material está vacío: limpio() lo descarta.
    assert.equal(materiales.length, 2);
    assert.equal(materiales[0].comprado_operario, false);
    assert.equal(materiales[0].cantidad_real, 2);
    assert.equal(materiales[1].origen_material, ORIGEN_MATERIAL_OPERARIO);
    assert.equal(materiales[1].comprado_operario, true);
    assert.equal(materiales[1].cantidad_real, 5.5);
  });

  test("implica_exclusion y transporte condicional", () => {
    const sinTransporte = build("correctivos");
    assert.ok(!("transportes" in sinTransporte));
    assert.equal(sinTransporte.implica_exclusion, false);

    const conTransporte = build("correctivos", {
      implica_exclusion: "SI",
      distancia_km: "12,5",
      tiempo_desplazamiento: "40 min",
    });
    assert.equal(conTransporte.implica_exclusion, true);
    assert.deepEqual(conTransporte.transportes, [
      { distancia_km: 12.5, tiempo_traslado: "40 min" },
    ]);
  });

  test("las rutas http del servidor sí se conservan", () => {
    const payload = build("correctivos", {
      evidencias: [
        {
          id: "ev1",
          previewUrl: "https://cdn.cinco.co/fotos/tablero.jpg",
          nombre: "tablero.jpg",
          descripcion: "Estado inicial",
        },
      ],
    });

    assert.deepEqual(payload.evidencias, [
      {
        seccion: "evidencias",
        campo_origen: "ev1",
        ruta_archivo: "https://cdn.cinco.co/fotos/tablero.jpg",
        nombre_original: "tablero.jpg",
        descripcion: "Estado inicial",
        orden: 1,
      },
    ]);
  });

  test("las fotos del material van a su fila con el índice de la lista filtrada", () => {
    const pendientes: PendienteSubida[] = [];
    const payload = buildCorrectivoEmergenciaPayload(
      {
        ...baseCorrectivo,
        materiales: [
          // Sin descripción: no viaja al payload y NO debe numerar.
          { descripcion: "   " },
          {
            origen_material: "CINCO SAS",
            descripcion: "Cable 12mm",
            cantidad: "5",
            tipo_unidad: "METROS",
            foto_antes_preview: "blob:http://localhost/antes",
            foto_antes_file: new File(["x"], "antes.jpg"),
          },
          {
            origen_material: "PROVEEDOR / ALIADO",
            descripcion: "Conector SC",
            cantidad: "1",
            tipo_unidad: "UND",
            foto_despues_preview: "/media/smu/despues.jpg",
          },
        ],
      } as unknown as FormCorrectivoEmergenciaData,
      "emergencias",
      pendientes,
    );

    const evidencias = payload.evidencias as Array<Record<string, unknown>>;
    assert.deepEqual(
      evidencias.map((e) => `${e.seccion}/${e.campo_origen}`),
      [
        "materiales/material_1_foto_antes",
        "materiales/material_2_foto_despues",
      ],
    );
    // La recién elegida viaja como marcador y su File queda encolado para
    // subirla antes del POST (la subida pega la ruta real después).
    assert.equal(evidencias[0].ruta_archivo, "PENDIENTE_SUBIDA");
    assert.equal(evidencias[0].nombre_original, "antes.jpg");
    assert.deepEqual(
      pendientes.map((p) => [p.seccion, p.campo_origen]),
      [["materiales", "material_1_foto_antes"]],
    );
    // La del segundo material no tiene File: se conserva la ruta del servidor.
    assert.equal(evidencias[1].ruta_archivo, "/media/smu/despues.jpg");
    // Los materiales se emparejan por la MISMA lista filtrada que numeró las
    // fotos, así que fila y foto siempre van 1 a 1.
    assert.deepEqual(
      (payload.materiales as Array<Record<string, unknown>>).map(
        (m) => m.descripcion,
      ),
      ["Cable 12mm", "Conector SC"],
    );
  });

  test("los materiales sin foto no emiten filas de evidencia", () => {
    const payload = build("emergencias");

    assert.ok(!("evidencias" in payload));
  });
});

// ─── CAPEX ────────────────────────────────────────────────────────────────────

describe("builders CAPEX", () => {
  const insumo = {
    id: "i1",
    texto_sap: "Filtro seco",
    codigo_sap: "SAP-99",
    alcance: "4 unidades",
    comentarios: "Reposición",
    cantidad_estandar: "4",
    cantidad_real: "4,0",
    unidad_medida: "UND",
  };
  const insumoVacio = {
    id: "i2",
    texto_sap: "  ",
    codigo_sap: "",
    alcance: "",
    comentarios: "",
  };
  const actividadMo = {
    id: "a1",
    texto_sap: "Desmontaje",
    codigo_sap: "SAP-77",
    alcance: "1 visita",
    comentarios: "",
  };

  const cabeceraEsperada = (payload: Record<string, unknown>, tipo: string) => {
    assert.equal(payload.categoria, "correctivos_capex");
    assert.equal(payload.tipo_formulario, tipo);
    assert.equal(payload.nombre_estacion, "ESTACIÓN ORIENTE");
    assert.equal(payload.codigo_ot, "OT-CAPEX-001");
    assert.equal(payload.responsable_cedula, "11223344");
    assert.equal(payload.responsable_nombre, "Carlos Ruiz");
    assert.deepEqual(payload.tecnicos, [
      { cedula: "11223344", nombre: "Carlos Ruiz", es_principal: true },
    ]);
  };

  const cabeceraCapex = {
    nombre_estacion: "ESTACIÓN ORIENTE",
    ot: "OT-CAPEX-001",
    fecha_inicio: "2026-09-30",
    responsable_ejecuta: { cedula: "11223344", nombre: "Carlos", apellido: "Ruiz" },
    insumos: [insumo, insumoVacio],
    actividades: [actividadMo],
    fotos_justificacion: [],
  };

  test("tipologia1: cabecera, materiales de inventario y mano de obra", () => {
    const payload = buildCapexTipologia1Payload({
      ...cabeceraCapex,
      filas_spt: [
        { distancia: "5.0 m", medida_ohmio: "3.8", resistividad: "" },
        { distancia: "", medida_ohmio: "", resistividad: "" },
      ],
      detalle_general: undefined,
      descripcion_general_actividades: "Adecuación de puesta a tierra",
    } as unknown as FormCapexTipologia1Data);

    cabeceraEsperada(payload, "tipologia1");

    const materiales = payload.materiales as Array<Record<string, unknown>>;
    assert.deepEqual(
      materiales.map((m) => m.tipo_registro),
      ["inventario_capex", "mano_obra_capex"],
    );
    assert.equal(materiales[0].cantidad_estandar, 4);
    // El insumo vacío queda fuera.
    assert.equal(materiales.length, 2);

    // La fila SPT sin datos no viaja. El builder no pasa estas filas por
    // limpio(), así que en JS quedan claves `undefined` que JSON descarta
    // igualmente: validamos exactamente lo que sale por la red.
    assert.deepEqual(JSON.parse(JSON.stringify(payload.spt_filas)), [
      { orden: 1, distancia: "5.0 m", medida_ohmio: "3.8" },
    ]);

    const detalle = payload.detalle_capex as Record<string, unknown>;
    assert.equal(detalle.tipologia, "tipologia1");
    assert.equal(
      detalle.descripcion_general_actividades,
      "Adecuación de puesta a tierra",
    );
  });

  test("tipologia3: cabecera y detalle con su tipología", () => {
    const payload = buildCapexTipologia3Payload({
      ...cabeceraCapex,
      transportes: [],
      recomendaciones_finales: "Reemplazar conductores",
    } as unknown as FormCapexTipologia3Data);

    cabeceraEsperada(payload, "tipologia3");

    const detalle = payload.detalle_capex as Record<string, unknown>;
    assert.equal(detalle.tipologia, "tipologia3");
    assert.equal(detalle.recomendacion_final, "Reemplazar conductores");
    assert.ok(!("spt_filas" in payload));
  });

  test("tipologia5: convierte distancia y numera las evidencias", () => {
    const payload = buildCapexTipologia5Payload({
      ...cabeceraCapex,
      transportes: [
        { tipo: "Camión", codigo_sap: "", descripcion: "", distancia_km: "12,5" },
        { tipo: "", codigo_sap: "", descripcion: "", distancia_km: "" },
      ],
      foto_panoramica_preview: "https://cdn.cinco.co/panoramica.jpg",
    } as unknown as FormCapexTipologia5Data);

    cabeceraEsperada(payload, "tipologia5");

    assert.deepEqual(payload.transportes, [
      { tipo_transporte: "Camión", distancia_km: 12.5 },
    ]);

    const evidencias = payload.evidencias as Array<Record<string, unknown>>;
    assert.equal(evidencias.length, 1);
    assert.equal(evidencias[0].seccion, "panoramica");
    assert.equal(evidencias[0].orden, 1);

    const detalle = payload.detalle_capex as Record<string, unknown>;
    assert.equal(detalle.tipologia, "tipologia5");
  });

  test("la descripción de cada foto viaja para encabezar su caja", () => {
    const t1 = buildCapexTipologia1Payload({
      ...cabeceraCapex,
      insumos: [
        {
          ...insumo,
          foto_preview: "https://cdn.cinco.co/i1.jpg",
          foto_descripcion: "Filtro reemplazado",
        },
      ],
      foto_panoramica_preview: "https://cdn.cinco.co/panoramica.jpg",
      foto_panoramica_descripcion: "Vista general de la subestación",
      filas_spt: [],
    } as unknown as FormCapexTipologia1Data);
    const porCampo = (payload: Record<string, unknown>) =>
      Object.fromEntries(
        (payload.evidencias as Array<Record<string, string>>).map((e) => [
          e.campo_origen,
          e,
        ]),
      );

    const t1PorCampo = porCampo(t1);
    assert.equal(t1PorCampo.insumo_1_foto.descripcion, "Filtro reemplazado");
    assert.equal(
      t1PorCampo.foto_panoramica_preview.descripcion,
      "Vista general de la subestación",
    );

    const t5 = buildCapexTipologia5Payload({
      ...cabeceraCapex,
      transportes: [
        {
          tipo: "Camión",
          codigo_sap: "",
          descripcion: "",
          distancia_km: "12,5",
          foto_antes_preview: "https://cdn.cinco.co/t1-antes.jpg",
          foto_antes_descripcion: "Carga asegurada antes de salir",
        },
      ],
      fotos_justificacion: [
        {
          id: "j1",
          previewUrl: "https://cdn.cinco.co/just1.jpg",
          descripcion: "Obra mayor fuera de estándar",
        },
      ],
    } as unknown as FormCapexTipologia5Data);

    const t5PorCampo = porCampo(t5);
    assert.equal(
      t5PorCampo.transporte_1_foto_antes.descripcion,
      "Carga asegurada antes de salir",
    );
    assert.equal(
      t5PorCampo.fotos_justificacion_1.descripcion,
      "Obra mayor fuera de estándar",
    );
  });
});

// ─── Subida de fotos (Fase 3 · A1) ────────────────────────────────────────────

describe("subida de fotos (Fase 3)", () => {
  const archivo = (nombre = "evidencia.jpg") =>
    new File(["contenido"], nombre, { type: "image/jpeg" });

  /** Subidor falso: `ruta` (con `{archivo}`) o un Error si se pasa un Error. */
  const subidorFalso =
    (ruta: string | Error) =>
    async (file: File): Promise<{ ruta_archivo: string }> => {
      if (ruta instanceof Error) throw ruta;
      return { ruta_archivo: ruta.replace("{archivo}", file.name) };
    };

  const cola = (pendientes: PendienteSubida[]) =>
    pendientes.map((p) => `${p.seccion}/${p.campo_origen}`);

  const baseAA: Record<string, unknown> = {
    nombre_estacion: "ESTACIÓN CENTRO",
    departamento: "Antioquia",
    responsable_1: responsable,
    fotos: {},
    checklist: {},
    acciones_mantenimiento: [
      Object.fromEntries(CLAVES_ACCIONES_AA.map((clave) => [clave, ""])),
    ],
    compresores: [],
    condensadoras: [],
    manejadoras: [],
    certificado: {},
  };

  const basePlanta: Record<string, unknown> = {
    nombre_estacion: "PLANTA NORTE",
    region: "Caribe",
    responsable_1: responsable,
    fotos: {},
    checklist: {},
    hallazgos: [],
    plantas: [],
    pruebas_filtracion: {},
  };

  const baseCorrectivo: Record<string, unknown> = {
    nombre_estacion: "ESTACIÓN SUR",
    responsable_1: responsable,
    implica_exclusion: "NO",
    evidencias: [],
    materiales: [],
  };

  test("AA: la ruta que devuelve el servidor se pega en la fila del payload", async () => {
    const pendientes: PendienteSubida[] = [];
    const file = archivo("aa.jpg");
    const payload = buildPreventivoAAPayload(
      {
        ...baseAA,
        fotos: {
          foto_1: { file, previewUrl: "blob:http://localhost/aa", nombre: "aa.jpg" },
        },
      } as unknown as PreventivoAAFormData,
      pendientes,
    );

    // Antes de subir: marcador honesto + un solo pendiente con su File.
    const evidencias = payload.evidencias as Array<Record<string, unknown>>;
    assert.equal(evidencias.length, 1);
    assert.equal(evidencias[0].ruta_archivo, "PENDIENTE_SUBIDA");
    assert.equal(pendientes.length, 1);
    assert.equal(pendientes[0].file, file);
    assert.deepEqual(cola(pendientes), ["anexos_fotograficos/foto_1"]);

    const ruta = "/media/smu/evidencias/borrador/anexos_fotograficos/{archivo}.webp";
    await subirPendientes(pendientes, subidorFalso(ruta));

    // conOrden() conserva la identidad de cada fila: la escritura aquí es la
    // misma fila que viaja en el payload (si se copiara, la foto se perdería).
    assert.equal(
      evidencias[0].ruta_archivo,
      "/media/smu/evidencias/borrador/anexos_fotograficos/aa.jpg.webp",
    );
  });

  test("sin File no hay pendiente: la ruta del servidor se conserva", () => {
    const pendientes: PendienteSubida[] = [];
    const payload = buildPreventivoAAPayload(
      {
        ...baseAA,
        fotos: {
          foto_1: {
            previewUrl: "https://cdn.cinco.co/fotos/aa.jpg",
            nombre: "aa.jpg",
          },
        },
      } as unknown as PreventivoAAFormData,
      pendientes,
    );

    assert.equal(pendientes.length, 0);
    const evidencias = payload.evidencias as Array<Record<string, unknown>>;
    assert.equal(evidencias[0].ruta_archivo, "https://cdn.cinco.co/fotos/aa.jpg");
    assert.equal(evidencias[0].nombre_original, "aa.jpg");
  });

  test("planta: la cola cubre anexos, hallazgos y certificado", async () => {
    const pendientes: PendienteSubida[] = [];
    const payload = buildPreventivoPlantaPayload(
      {
        ...basePlanta,
        fotos: {
          foto_1: { file: archivo("anexo.jpg"), previewUrl: "blob:a", nombre: "anexo.jpg" },
        },
        hallazgos: [
          {
            descripcion: "Fuga en tablero",
            evidencia_1: "blob:h",
            evidencia_1_file: archivo("hallazgo.jpg"),
          },
        ],
        certificado_tipo: "Retención",
        certificado_categoria: "Clase A",
        foto_certificado_preview: "blob:c",
        foto_certificado_file: archivo("certificado.jpg"),
      } as unknown as FormPreventivoPlantaData,
      [],
      pendientes,
    );

    assert.deepEqual(cola(pendientes), [
      "anexos_planta/foto_1",
      "hallazgos_planta/hallazgo_1_evidencia_1",
      "certificados/certificado_1_foto_certificado",
    ]);

    await subirPendientes(pendientes, subidorFalso("/media/fotos/{archivo}.webp"));

    const certificados = payload.certificados as Array<Record<string, unknown>>;
    assert.equal(certificados[0].ruta_certificado, "/media/fotos/certificado.jpg.webp");
  });

  test("certificado blob: sin file queda PENDIENTE_SUBIDA (no el literal)", () => {
    const pendientes: PendienteSubida[] = [];
    const payload = buildPreventivoAAPayload(
      {
        ...baseAA,
        certificado: {
          tipo_certificado: "ISO 9001",
          foto_certificado_preview: "blob:c",
        },
      } as unknown as PreventivoAAFormData,
      pendientes,
    );

    assert.equal(pendientes.length, 0);
    const certificados = payload.certificados as Array<Record<string, unknown>>;
    assert.equal(certificados[0].ruta_certificado, "PENDIENTE_SUBIDA");
  });

  test("correctivo: sube cada evidencia en orden, una por una", async () => {
    const pendientes: PendienteSubida[] = [];
    const payload = buildCorrectivoEmergenciaPayload(
      {
        ...baseCorrectivo,
        evidencias: [
          { id: "ev1", previewUrl: "blob:1", file: archivo("uno.jpg") },
          { id: "ev2", previewUrl: "blob:2", file: archivo("dos.jpg") },
        ],
      } as unknown as FormCorrectivoEmergenciaData,
      "correctivos",
      pendientes,
    );

    const subidas: string[] = [];
    await subirPendientes(pendientes, async (file) => {
      subidas.push(file.name);
      return { ruta_archivo: `/media/${file.name}` };
    });

    assert.deepEqual(subidas, ["uno.jpg", "dos.jpg"]);
    const evidencias = payload.evidencias as Array<Record<string, unknown>>;
    assert.deepEqual(
      evidencias.map((e) => e.ruta_archivo),
      ["/media/uno.jpg", "/media/dos.jpg"],
    );
  });

  test("correctivo: sube la foto del material a su fila", async () => {
    const pendientes: PendienteSubida[] = [];
    const payload = buildCorrectivoEmergenciaPayload(
      {
        ...baseCorrectivo,
        materiales: [
          {
            origen_material: "CINCO SAS",
            descripcion: "Cable 12mm",
            cantidad: "5",
            tipo_unidad: "METROS",
            foto_antes_preview: "blob:1",
            foto_antes_file: archivo("antes.jpg"),
          },
        ],
      } as unknown as FormCorrectivoEmergenciaData,
      "correctivos",
      pendientes,
    );

    await subirPendientes(pendientes, async (file) => ({
      ruta_archivo: `/media/${file.name}`,
    }));

    const evidencias = payload.evidencias as Array<Record<string, unknown>>;
    assert.deepEqual(
      evidencias.map((e) => [e.seccion, e.campo_origen, e.ruta_archivo]),
      [["materiales", "material_1_foto_antes", "/media/antes.jpg"]],
    );
  });

  test("un fallo de subida aborta con ErrorSubidaFotos y no sigue subiendo", async () => {
    const pendientes: PendienteSubida[] = [];
    const payload = buildCorrectivoEmergenciaPayload(
      {
        ...baseCorrectivo,
        evidencias: [
          { id: "ev1", previewUrl: "blob:1", file: archivo("uno.jpg") },
          { id: "ev2", previewUrl: "blob:2", file: archivo("dos.jpg") },
        ],
      } as unknown as FormCorrectivoEmergenciaData,
      "correctivos",
      pendientes,
    );

    let llamadas = 0;
    await assert.rejects(
      subirPendientes(pendientes, async () => {
        llamadas += 1;
        throw new Error("500 interno");
      }),
      (err: unknown) => {
        assert.ok(err instanceof ErrorSubidaFotos);
        assert.match(err.message, /uno\.jpg/);
        assert.match(err.message, /500 interno/);
        return true;
      },
    );

    // Se detiene en la primera: nada de fotos a medias ni POST a medias.
    assert.equal(llamadas, 1);
    const evidencias = payload.evidencias as Array<Record<string, unknown>>;
    assert.equal(evidencias[0].ruta_archivo, "PENDIENTE_SUBIDA");
  });

  test("CAPEX T1: las fotos genéricas suben desde su campo compañero", () => {
    const pendientes: PendienteSubida[] = [];
    buildCapexTipologia1Payload(
      {
        nombre_estacion: "ESTACIÓN ORIENTE",
        ot: "OT-1",
        fecha_inicio: "2026-09-30",
        responsable_ejecuta: { cedula: "11223344", nombre: "Carlos", apellido: "Ruiz" },
        insumos: [],
        actividades: [],
        fotos_justificacion: [],
        filas_spt: [],
        transporte_foto_antes: "blob:t",
        transporte_foto_antes_file: archivo("traslado.jpg"),
        foto_panoramica_preview: "blob:p",
        foto_panoramica_file: archivo("panoramica.jpg"),
      } as unknown as FormCapexTipologia1Data,
      pendientes,
    );

    assert.deepEqual(cola(pendientes), [
      "transporte/transporte_foto_antes",
      "panoramica/foto_panoramica_preview",
    ]);
  });
});

// ─── Precarga: la foto se sube en cuanto el usuario la elige ─────────────────
//
// Con muchos formularios llenos de fotos, subirlas todas al guardar retrasa el
// envío. La precarga sube cada foto al elegirla y `subirPendientes` solo
// *espera* la ruta (casi siempre ya resuelta). Un fallo de precarga nunca
// bloquea: el guardado reintenta con la sección/campo reales.

describe("precarga de fotos (elegir ya sube)", () => {
  const archivo = (nombre = "precarga.jpg") =>
    new File(["contenido"], nombre, { type: "image/jpeg" });

  test("sube una sola vez y al guardar solo se espera la ruta", async () => {
    limpiarPrecargasSMU();
    const file = archivo();
    let subidas = 0;
    const subidor = async (f: File): Promise<{ ruta_archivo: string }> => {
      subidas += 1;
      return { ruta_archivo: `/media/borrador/precarga/${f.name}.webp` };
    };

    const ruta = await preCargarFotoSMU(file, subidor);
    // Re-elegir la misma foto no repite la subida (misma clave = mismo File).
    await preCargarFotoSMU(file, subidor);
    assert.equal(subidas, 1);

    // Al guardar: no se vuelve a subir, se reutiliza la ruta precargada.
    let aplicada = "";
    const pendientes: PendienteSubida[] = [
      {
        file,
        seccion: "anexos_fotograficos",
        campo_origen: "foto_1",
        aplicar: (r) => {
          aplicada = r;
        },
      },
    ];
    await subirPendientes(pendientes, async () => {
      throw new Error("no debe subir de nuevo");
    });

    assert.equal(aplicada, ruta);
    assert.equal(subidas, 1);
    limpiarPrecargasSMU();
  });

  test("si la precarga falló, el guardado reintenta la subida", async () => {
    limpiarPrecargasSMU();
    const file = archivo("intermitente.jpg");

    await assert.rejects(
      preCargarFotoSMU(file, async () => {
        throw new Error("red caída");
      }),
      /red caída/,
    );

    // El fallo no quedó cacheado: al guardar se sube de nuevo, sin errores
    // residuales de la precarga.
    let aplicada = "";
    const pendientes: PendienteSubida[] = [
      {
        file,
        seccion: "inventario",
        campo_origen: "material_1",
        aplicar: (r) => {
          aplicada = r;
        },
      },
    ];
    await subirPendientes(pendientes, async () => ({
      ruta_archivo: "/media/reintento.webp",
    }));

    assert.equal(aplicada, "/media/reintento.webp");
    limpiarPrecargasSMU();
  });

  test("mezcla: solo sube la foto que no estaba precargada", async () => {
    limpiarPrecargasSMU();
    const ya = archivo("lista.jpg");
    const falta = archivo("pendiente.jpg");
    await preCargarFotoSMU(ya, async () => ({
      ruta_archivo: "/media/lista.webp",
    }));

    const aplicadas: Record<string, string> = {};
    const pendientes: PendienteSubida[] = [
      {
        file: ya,
        seccion: "transporte",
        campo_origen: "antes",
        aplicar: (r) => {
          aplicadas.lista = r;
        },
      },
      {
        file: falta,
        seccion: "transporte",
        campo_origen: "durante",
        aplicar: (r) => {
          aplicadas.pendiente = r;
        },
      },
    ];

    const subidas: string[] = [];
    await subirPendientes(pendientes, async (f) => {
      subidas.push(f.name);
      return { ruta_archivo: `/media/${f.name}.webp` };
    });

    assert.deepEqual(subidas, ["pendiente.jpg"]);
    assert.equal(aplicadas.lista, "/media/lista.webp");
    assert.equal(aplicadas.pendiente, "/media/pendiente.jpg.webp");
    limpiarPrecargasSMU();
  });

  test("olvidarPrecargaSMU obliga a subir de nuevo (foto quitada)", async () => {
    limpiarPrecargasSMU();
    const file = archivo("quitada.jpg");
    let subidas = 0;
    const subidor = async (): Promise<{ ruta_archivo: string }> => {
      subidas += 1;
      return { ruta_archivo: `/media/${subidas}.webp` };
    };

    await preCargarFotoSMU(file, subidor);
    olvidarPrecargaSMU(file);
    const segunda = await preCargarFotoSMU(file, subidor);

    assert.equal(subidas, 2);
    assert.equal(segunda, "/media/2.webp");
    limpiarPrecargasSMU();
  });
});

describe("registro de precarga (lib/precargaFoto)", () => {
  test("delega en el subidor registrado y desregistrar lo apaga", async () => {
    const file = new File(["x"], "registro.jpg", { type: "image/jpeg" });
    let olvidado = "";

    registrarPrecargaFoto(
      async (f) => `/ruta/${f.name}`,
      (f) => {
        olvidado = f.name;
      },
    );

    const promesa = fotoElegida(file);
    assert.ok(promesa);
    assert.equal(await promesa, "/ruta/registro.jpg");

    olvidarFotoElegida(file);
    assert.equal(olvidado, "registro.jpg");

    // Sin registrador no hay precarga: el flujo clásico (subir al guardar).
    desregistrarPrecargaFoto();
    assert.equal(fotoElegida(file), null);
  });
});

// ─── Fechas: DRF solo acepta ISO ──────────────────────────────────────────────
//
// `fecha_inicio`/`fecha_fin` son DateTimeField y `firmas_cierre[].fecha`,
// `fecha_elaboracion_informe` y `matricula_fecha` son DateField. Un valor
// fuera de ISO ("", "01/10/2026", el toString() de un Date) hace fallar el
// guardado entero con «Fecha/hora con formato erróneo».

describe("fechas de los payloads", () => {
  const baseCorrectivo = {
    nombre_estacion: "ESTACIÓN ORION",
    responsable_1: responsable,
    fecha_inicio: "2026-10-01T08:00",
    fecha_fin: "",
    tipo_actividad: "CORRECTIVO",
    materiales: [],
    evidencias: [],
  };

  const build = (extra: Record<string, unknown> = {}) =>
    buildCorrectivoEmergenciaPayload(
      {
        ...baseCorrectivo,
        ...extra,
      } as unknown as FormCorrectivoEmergenciaData,
      "correctivos",
      [],
    );

  test("la fecha del input datetime-local viaja tal cual y la vacía no viaja", () => {
    const payload = build();

    assert.equal(payload.fecha_inicio, "2026-10-01T08:00");
    assert.ok(!("fecha_fin" in payload));
  });

  test("convierte el formato local 01/10/2026 08:00 a ISO", () => {
    const payload = build({
      fecha_inicio: "01/10/2026 08:00",
      fecha_fin: "02/10/2026",
    });

    assert.equal(payload.fecha_inicio, "2026-10-01T08:00:00");
    assert.equal(payload.fecha_fin, "2026-10-02T00:00:00");
  });

  test("un Date se serializa en hora local, no con toString()", () => {
    const payload = build({ fecha_inicio: new Date(2026, 9, 1, 8, 5) });

    assert.equal(payload.fecha_inicio, "2026-10-01T08:05:00");
  });

  test("texto ilegible se descarta en vez de tumbar el guardado", () => {
    const payload = build({ fecha_inicio: "ayer a las 8", fecha_fin: "  " });

    assert.ok(!("fecha_inicio" in payload));
    assert.ok(!("fecha_fin" in payload));
  });

  test("fecha solo (DateField) de firma y de matrícula CAPEX llega YYYY-MM-DD", () => {
    const payload = buildCapexTipologia1Payload(
      {
        nombre_estacion: "ESTACIÓN ORION",
        ot: "OT-1",
        fecha_inicio: "01/10/2026",
        responsable_ejecuta: responsable,
        responsable_entrega_nombre: "Carlos Ruiz",
        responsable_entrega_fecha: "31/12/2026 14:30",
        matricula_fecha: "fecha no válida",
        insumos: [],
        actividades: [],
        fotos_justificacion: [],
        filas_spt: [],
      } as unknown as FormCapexTipologia1Data,
      [],
    );

    assert.equal(payload.fecha_inicio, "2026-10-01T00:00:00");
    assert.deepEqual(
      (payload.firmas_cierre as Array<Record<string, unknown>>).map((f) => f.fecha),
      ["2026-12-31"],
    );
    // Ilegible: el campo no viaja (antes llegaba el literal y el backend
    // respondía 400 «Fecha/hora con formato erróneo»).
    assert.ok(
      !("matricula_fecha" in (payload.detalle_capex as Record<string, unknown>)),
    );
  });
});

// ─── Fechas del encabezado: bloquear en vez de guardar basura ────────────────
//
// Un registro sin fecha de inicio o con un año imposible ("12/12/1212")
// aparece en la columna "INICIO" del historial como "-": la digitación rara
// se guardaba sin avisar. Ahora el submit valida y la API también.

describe("validación de fechas del encabezado", () => {
  test("sin fecha de inicio se bloquea con mensaje", () => {
    assert.match(validarFechasEncabezado("", "") ?? "", /obligatoria/);
    assert.match(
      validarFechasEncabezado(undefined, undefined) ?? "",
      /obligatoria/,
    );
    assert.equal(validarFechasEncabezado("2026-10-01T08:00"), null);
  });

  test("años fuera de rango (1212) no pasan ni en inicio ni en fin", () => {
    assert.match(
      validarFechasEncabezado("1212-12-12T00:12:00") ?? "",
      /no es válida/,
    );
    assert.match(validarFechasEncabezado("12/12/1212") ?? "", /no es válida/);
    assert.match(
      validarFechasEncabezado("2026-10-01T08:00", "12/12/1212") ?? "",
      /Fecha de Fin/,
    );
  });

  test("fin anterior al inicio se bloquea; fin vacía es opcional", () => {
    assert.match(
      validarFechasEncabezado("2026-10-05T08:00", "2026-10-01T08:00") ?? "",
      /anterior/,
    );
    assert.equal(
      validarFechasEncabezado("2026-10-01T08:00", "2026-10-05T08:00"),
      null,
    );
    assert.equal(validarFechasEncabezado("2026-10-01T08:00", ""), null);
  });

  test("el builder no arrastra una fecha fuera de rango", () => {
    const payload = buildPreventivoAAPayload(
      {
        nombre_estacion: "ESTACIÓN CENTRO",
        departamento: "Antioquia",
        responsable_1: responsable,
        fecha_inicio: "1212-12-12T00:12:00",
        fotos: {},
        checklist: {},
        acciones_mantenimiento: [
          Object.fromEntries(CLAVES_ACCIONES_AA.map((clave) => [clave, ""])),
        ],
        compresores: [],
        condensadoras: [],
        manejadoras: [],
        certificado: {},
      } as unknown as PreventivoAAFormData,
      [],
    );

    assert.ok(!("fecha_inicio" in payload));
  });
});

// ─── Evidencias: baja de la foto ─────────────────────────────────────────────

describe("quitarFotoEvidencia (regresión: la foto eliminada se subía igual)", () => {
  const archivo = new File(["binario"], "evidencia.png", {
    type: "image/png",
  });

  const evidenciaConFoto = {
    id: "ev-1",
    previewUrl: "blob:http://localhost/abc",
    file: archivo,
    nombre: "evidencia.png",
    descripcion: "Tablero sin proteger",
  };

  const payloadDe = (
    evidencias: FormCorrectivoEmergenciaData["evidencias"],
    pendientes: PendienteSubida[],
  ) =>
    buildCorrectivoEmergenciaPayload(
      {
        nombre_estacion: "ESTACIÓN SUR",
        responsable_1: responsable,
        implica_exclusion: "NO",
        evidencias,
        materiales: [],
      } as unknown as FormCorrectivoEmergenciaData,
      "emergencias",
      pendientes,
    );

  test("limpia preview, File y nombre y conserva fila y descripción", () => {
    const lista = quitarFotoEvidencia([evidenciaConFoto], "ev-1");

    assert.equal(lista.length, 1);
    assert.equal(lista[0].id, "ev-1");
    assert.equal(lista[0].descripcion, "Tablero sin proteger");
    assert.equal(lista[0].previewUrl, undefined);
    assert.equal(lista[0].file, undefined);
    assert.equal(lista[0].nombre, undefined);
  });

  test("no toca las demás evidencias", () => {
    const otra = { ...evidenciaConFoto, id: "ev-2" };
    const lista = quitarFotoEvidencia([evidenciaConFoto, otra], "ev-1");

    assert.equal(lista[1].file, archivo);
    assert.equal(lista[1].previewUrl, "blob:http://localhost/abc");
  });

  test("tras la baja el builder no encola ninguna subida", () => {
    const pendientes: PendienteSubida[] = [];
    const quitada = quitarFotoEvidencia([evidenciaConFoto], "ev-1");
    const payload = payloadDe(quitada, pendientes);

    assert.equal(pendientes.length, 0);

    // Con descripción la fila sigue (es texto del técnico), pero ya no arrastra
    // el nombre del archivo que el usuario quitó.
    const filas = payload.evidencias as Array<Record<string, unknown>>;
    assert.equal(filas.length, 1);
    assert.equal(filas[0].nombre_original, undefined);
  });

  test("sin descripción ni foto la evidencia desaparece del payload", () => {
    const pendientes: PendienteSubida[] = [];
    const payload = payloadDe(
      quitarFotoEvidencia([{ ...evidenciaConFoto, descripcion: "" }], "ev-1"),
      pendientes,
    );

    assert.equal(pendientes.length, 0);
    // Convención del builder: las colecciones vacías no viajan.
    assert.ok(!("evidencias" in payload));
  });
});
