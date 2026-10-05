/**
 * Cálculo de festivos en Colombia según la Ley 51 de 1983 (Ley Emiliani)
 * y cálculo eclesiástico del Domingo de Resurrección (Pascua).
 */

export interface Festivo {
  fecha: string; // Formato YYYY-MM-DD
  nombre: string;
}

export interface OpcionesDiaHabil {
  /**
   * Indica si el sábado se considera día hábil de trabajo.
   * En Operaciones y logística suele ser true por defecto.
   */
  sabadoHabil?: boolean;
}

// Cache en memoria por año para O(1) en llamadas repetidas
const cacheFestivosPorAnio = new Map<number, Festivo[]>();
const cacheFestivosMap = new Map<string, { nombre: string } | null>();

/**
 * Calcula la fecha del Domingo de Resurrección (Pascua) para un año dado
 * usando el algoritmo de Butcher / Meeus (Cálculo del Cómputo Gregoriano).
 */
function calcularPascua(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31); // 3 = Marzo, 4 = Abril
  const day = ((h + l - 7 * m + 114) % 31) + 1;

  return new Date(Date.UTC(year, month - 1, day));
}

/**
 * Traslada una fecha al siguiente lunes si aplica la Ley Emiliani.
 * Si ya cae en lunes, se mantiene.
 */
function aplicarLeyEmiliani(year: number, monthZeroIndexed: number, day: number): Date {
  const fecha = new Date(Date.UTC(year, monthZeroIndexed, day));
  const diaSemana = fecha.getUTCDay(); // 0 = Domingo, 1 = Lunes, ..., 6 = Sábado

  if (diaSemana === 1) {
    return fecha; // Ya es lunes
  }

  const diasParaLunes = diaSemana === 0 ? 1 : 8 - diaSemana;
  fecha.setUTCDate(fecha.getUTCDate() + diasParaLunes);
  return fecha;
}

/**
 * Suma días a una fecha UTC dada.
 */
function sumarDiasUtc(fecha: Date, dias: number): Date {
  const res = new Date(fecha.getTime());
  res.setUTCDate(res.getUTCDate() + dias);
  return res;
}

/**
 * Formatea un objeto Date en string YYYY-MM-DD en UTC.
 */
function formatearUtcYmd(fecha: Date): string {
  const y = fecha.getUTCFullYear();
  const m = String(fecha.getUTCMonth() + 1).padStart(2, "0");
  const d = String(fecha.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/**
 * Retorna la lista oficial de los 18 festivos de Colombia para un año específico.
 */
export function calcularFestivosColombia(year: number): Festivo[] {
  if (cacheFestivosPorAnio.has(year)) {
    return cacheFestivosPorAnio.get(year)!;
  }

  const pascua = calcularPascua(year);
  const festivos: Festivo[] = [];

  // 1. Festivos Fijos (Inamovibles)
  festivos.push({ fecha: `${year}-01-01`, nombre: "Año Nuevo" });
  festivos.push({ fecha: `${year}-05-01`, nombre: "Día del Trabajo" });
  festivos.push({ fecha: `${year}-07-20`, nombre: "Día de la Independencia" });
  festivos.push({ fecha: `${year}-08-07`, nombre: "Batalla de Boyacá" });
  festivos.push({ fecha: `${year}-12-08`, nombre: "Inmaculada Concepción" });
  festivos.push({ fecha: `${year}-12-25`, nombre: "Navidad" });

  // 2. Festivos con Ley Emiliani (traslado al lunes siguiente)
  festivos.push({
    fecha: formatearUtcYmd(aplicarLeyEmiliani(year, 0, 6)),
    nombre: "Día de los Reyes Magos",
  });
  festivos.push({
    fecha: formatearUtcYmd(aplicarLeyEmiliani(year, 2, 19)),
    nombre: "Día de San José",
  });
  festivos.push({
    fecha: formatearUtcYmd(aplicarLeyEmiliani(year, 5, 29)),
    nombre: "San Pedro y San Pablo",
  });
  festivos.push({
    fecha: formatearUtcYmd(aplicarLeyEmiliani(year, 7, 15)),
    nombre: "Asunción de la Virgen",
  });
  festivos.push({
    fecha: formatearUtcYmd(aplicarLeyEmiliani(year, 9, 12)),
    nombre: "Día de la Raza",
  });
  festivos.push({
    fecha: formatearUtcYmd(aplicarLeyEmiliani(year, 10, 1)),
    nombre: "Todos los Santos",
  });
  festivos.push({
    fecha: formatearUtcYmd(aplicarLeyEmiliani(year, 10, 11)),
    nombre: "Independencia de Cartagena",
  });

  // 3. Festivos relativos a Pascua
  // Jueves Santo: Pascua - 3 días
  festivos.push({
    fecha: formatearUtcYmd(sumarDiasUtc(pascua, -3)),
    nombre: "Jueves Santo",
  });
  // Viernes Santo: Pascua - 2 días
  festivos.push({
    fecha: formatearUtcYmd(sumarDiasUtc(pascua, -2)),
    nombre: "Viernes Santo",
  });
  // Ascensión del Señor: Pascua + 40 días, trasladado al lunes siguiente (+43 días)
  festivos.push({
    fecha: formatearUtcYmd(sumarDiasUtc(pascua, 43)),
    nombre: "Ascensión del Señor",
  });
  // Corpus Christi: Pascua + 60 días, trasladado al lunes siguiente (+64 días)
  festivos.push({
    fecha: formatearUtcYmd(sumarDiasUtc(pascua, 64)),
    nombre: "Corpus Christi",
  });
  // Sagrado Corazón de Jesús: Pascua + 68 días, trasladado al lunes siguiente (+71 días)
  festivos.push({
    fecha: formatearUtcYmd(sumarDiasUtc(pascua, 71)),
    nombre: "Sagrado Corazón de Jesús",
  });

  // Ordenar cronológicamente
  festivos.sort((a, b) => a.fecha.localeCompare(b.fecha));

  // Guardar en caché
  cacheFestivosPorAnio.set(year, festivos);
  festivos.forEach((f) => cacheFestivosMap.set(f.fecha, { nombre: f.nombre }));

  return festivos;
}

/**
 * Obtiene la información de un festivo si la fecha YYYY-MM-DD corresponde a uno, o null.
 */
export function getFestivoColombia(ymd: string): { nombre: string } | null {
  if (!ymd || typeof ymd !== "string") return null;
  const cleanYmd = ymd.slice(0, 10);

  if (cacheFestivosMap.has(cleanYmd)) {
    return cacheFestivosMap.get(cleanYmd) || null;
  }

  const parts = cleanYmd.split("-");
  if (parts.length < 3) return null;
  const year = parseInt(parts[0], 10);
  if (isNaN(year)) return null;

  // Generar festivos del año (llenará el cacheFestivosMap)
  calcularFestivosColombia(year);

  return cacheFestivosMap.get(cleanYmd) || null;
}

/**
 * Determina si una fecha YYYY-MM-DD es festivo en Colombia.
 */
export function esFestivo(ymd: string): boolean {
  return getFestivoColombia(ymd) !== null;
}

/**
 * Obtiene todos los festivos de un año dado.
 */
export function getFestivosDelAnio(year: number): Festivo[] {
  return calcularFestivosColombia(year);
}

/**
 * Determina si una fecha es día hábil.
 * Por defecto:
 * - Domingos: No hábil
 * - Festivos Colombia: No hábil
 * - Sábados: Hábil (sabadoHabil: true por defecto)
 */
export function esDiaHabil(ymd: string, opciones?: OpcionesDiaHabil): boolean {
  if (!ymd) return false;
  const cleanYmd = ymd.slice(0, 10);
  const parts = cleanYmd.split("-");
  if (parts.length < 3) return false;

  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const d = parseInt(parts[2], 10);
  if (isNaN(y) || isNaN(m) || isNaN(d)) return false;

  // Usar Date UTC para evitar problemas de zona horaria local
  const fechaObj = new Date(Date.UTC(y, m - 1, d));
  const diaSemana = fechaObj.getUTCDay(); // 0 = Domingo, 6 = Sábado

  // Domingo nunca es hábil
  if (diaSemana === 0) return false;

  // Sábado configurable (default true)
  const sabadoHabil = opciones?.sabadoHabil ?? true;
  if (diaSemana === 6 && !sabadoHabil) return false;

  // Si es festivo, no es hábil
  if (esFestivo(cleanYmd)) return false;

  return true;
}

/**
 * Suma N días hábiles a una fecha YYYY-MM-DD.
 */
export function sumarDiasHabiles(ymd: string, n: number, opciones?: OpcionesDiaHabil): string {
  if (!ymd || n === 0) return ymd;
  const cleanYmd = ymd.slice(0, 10);
  const parts = cleanYmd.split("-");
  const y = parseInt(parts[0], 10);
  const m = parseInt(parts[1], 10);
  const d = parseInt(parts[2], 10);

  const curr = new Date(Date.UTC(y, m - 1, d));
  let agregados = 0;
  const paso = n > 0 ? 1 : -1;
  const total = Math.abs(n);

  while (agregados < total) {
    curr.setUTCDate(curr.getUTCDate() + paso);
    const currYmd = formatearUtcYmd(curr);
    if (esDiaHabil(currYmd, opciones)) {
      agregados++;
    }
  }

  return formatearUtcYmd(curr);
}
