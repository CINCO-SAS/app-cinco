// src/modules/transporte/transporteModulos.ts
//
// Organización del módulo Transporte en el sidebar.
//
// Fuente única de verdad de la estructura: la consume el AppSidebar y las
// páginas. Si se quiere reorganizar (añadir, quitar o renombrar una
// pantalla), se cambia AQUÍ y se propaga.
//
// Los 3 grupos replican el sentido del legacy, que agrupaba por QUÉ se hace
// y QUIÉN lo usa:
//   · base_salida_transporte.php  → Administración (gestión/informes/liquidaciones)
//   · transporte_salida.php       → Operación (registro diario)
//   · base_transportadores.php    → Maestros (flota y conductores)

export type IdModulo = "operacion" | "maestros" | "administracion";

export interface PantallaTransporte {
  /** Segmento de la ruta, p. ej. `salidas` → `/transporte/operacion/salidas`. */
  segmento: string;
  /** Nombre visible en el sidebar. */
  etiqueta: string;
  /** Si la pantalla todavía no existe, el enlace se omite. */
  disponible?: boolean;
}

export interface ModuloTransporte {
  id: IdModulo;
  /** Nombre del grupo en el sidebar. */
  etiqueta: string;
  /** Segmento raíz del módulo, p. ej. `operacion`. */
  segmento: string;
  /** Pantalla por defecto al entrar al módulo. */
  pantallaInicial: string;
  /** Pantallas del módulo, en orden de aparición. */
  pantallas: PantallaTransporte[];
}

/**
 * Los 3 módulos. `disponible: false` marca pantallas cuyo front aún no se
 * construye: el sidebar las omite hasta que existan (evita enlaces muertos).
 */
export const MODULOS_TRANSPORTE: ModuloTransporte[] = [
  {
    id: "operacion",
    etiqueta: "Transporte · Operación",
    segmento: "operacion",
    pantallaInicial: "salidas",
    pantallas: [
      // F3/B2: alta S6 + consulta B1 + Ítem L (acciones de fila: aprobar,
      // rechazar, novedad, historial). El corazón del uso diario.
      { segmento: "salidas", etiqueta: "Registro de Salidas", disponible: true },
      // F3/S1-S4: kiosco de despacho vehicular.
      { segmento: "kiosco", etiqueta: "Kiosco de Despacho", disponible: true },
      // F3/B3: reporte fotográfico diario (ventana 10:00–16:00 + agenda).
      {
        segmento: "reporte-fotografico",
        etiqueta: "Reporte Fotográfico",
        disponible: true,
      },
    ],
  },
  {
    id: "maestros",
    etiqueta: "Transporte · Maestros",
    segmento: "maestros",
    pantallaInicial: "flota",
    pantallas: [
      // F2: catálogo de flota con semáforo SOAT/CDA (front construido).
      { segmento: "flota", etiqueta: "Flota Vehicular", disponible: true },
      // F2: transportadores externos (no están en nómina). Front construido.
      { segmento: "conductores", etiqueta: "Conductores", disponible: true },
      // F2/Duenos: propietarios de vehículos (1 dueño → N vehículos + datos bancarios)
      { segmento: "duenos", etiqueta: "Dueños de Vehículos", disponible: true },
    ],
  },
  {
    id: "administracion",
    etiqueta: "Transporte · Administración",
    segmento: "administracion",
    pantallaInicial: "gestion",
    pantallas: [
      // F4/B4: backoffice (Tab 1 del legacy).
      { segmento: "gestion", etiqueta: "Gestión de Salidas", disponible: true },
      // F5: sábana de informes y nómina (Tab 2). Pasos 2 completos
      // (Transporte Día y Transporte Mes); el resto de bloques avanzan
      // por pasos y quedan marcados dentro de la vista.
      { segmento: "informes", etiqueta: "Informes", disponible: true },
      // F5: liquidaciones financieras (Tab 3).
      { segmento: "liquidaciones", etiqueta: "Liquidaciones", disponible: true },
      // F5-6: planilla oficial de salida F-104.
      { segmento: "planillas", etiqueta: "Planilla F-104", disponible: true },
    ],
  },
];

/** Ruta de una pantalla concreta. */
export const rutaPantalla = (idModulo: IdModulo, segmento: string): string =>
  `/transporte/${idModulo}/${segmento}`;

/** Ruta raíz de un módulo (su pantalla inicial). */
export const rutaModulo = (modulo: ModuloTransporte): string =>
  rutaPantalla(modulo.id, modulo.pantallaInicial);

/**
 * Devuelve UNA entrada de menú "Transporte" con todas las pantallas como
 * sub-items, en el orden de los 3 grupos (los títulos de grupo se omiten
 * para no ensuciar el menú).
 */
export const navItemsDeTransporte = (): {
  name: string;
  subItems: { name: string; path: string }[];
}[] => [
  {
    name: "Transporte",
    subItems: MODULOS_TRANSPORTE.flatMap((modulo) =>
      modulo.pantallas
        .filter((pantalla) => pantalla.disponible !== false)
        .map((pantalla) => ({
          name: pantalla.etiqueta,
          path: rutaPantalla(modulo.id, pantalla.segmento),
        })),
    ),
  },
];

