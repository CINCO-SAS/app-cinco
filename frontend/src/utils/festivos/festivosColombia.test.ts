import {
  calcularFestivosColombia,
  esDiaHabil,
  esFestivo,
  getFestivoColombia,
  sumarDiasHabiles,
} from "./festivosColombia";

function runTests() {
  const festivos2026 = calcularFestivosColombia(2026);
  if (festivos2026.length !== 18) {
    throw new Error(`Expected 18 holidays, got ${festivos2026.length}`);
  }

  // 1 de Enero (Año Nuevo)
  if (!esFestivo("2026-01-01") || getFestivoColombia("2026-01-01")?.nombre !== "Año Nuevo") {
    throw new Error("Año Nuevo check failed");
  }

  // Reyes Magos 2026: 6 de Enero cae martes -> se traslada al lunes 12 de Enero
  if (!esFestivo("2026-01-12") || getFestivoColombia("2026-01-12")?.nombre !== "Día de los Reyes Magos") {
    throw new Error("Reyes Magos check failed");
  }

  // Jueves Santo 2026: 2 de Abril
  if (!esFestivo("2026-04-02") || getFestivoColombia("2026-04-02")?.nombre !== "Jueves Santo") {
    throw new Error("Jueves Santo check failed");
  }

  // Viernes Santo 2026: 3 de Abril
  if (!esFestivo("2026-04-03") || getFestivoColombia("2026-04-03")?.nombre !== "Viernes Santo") {
    throw new Error("Viernes Santo check failed");
  }

  // 20 de Julio 2026 (Día de la Independencia)
  if (!esFestivo("2026-07-20") || getFestivoColombia("2026-07-20")?.nombre !== "Día de la Independencia") {
    throw new Error("Independencia check failed");
  }

  // 7 de Agosto 2026 (Batalla de Boyacá)
  if (!esFestivo("2026-08-07") || getFestivoColombia("2026-08-07")?.nombre !== "Batalla de Boyacá") {
    throw new Error("Boyaca check failed");
  }

  // 25 de Diciembre 2026 (Navidad)
  if (!esFestivo("2026-12-25")) {
    throw new Error("Navidad check failed");
  }

  // Domingos no hábiles
  if (esDiaHabil("2026-10-04")) {
    throw new Error("Domingo should not be habil");
  }

  // Festivo 12 Octubre no hábil
  if (esDiaHabil("2026-10-12")) {
    throw new Error("Festivo 12 Oct should not be habil");
  }

  // Martes 13 Octubre es hábil
  if (!esDiaHabil("2026-10-13")) {
    throw new Error("Martes 13 Oct should be habil");
  }

  // Sábados hábiles por defecto
  if (!esDiaHabil("2026-10-10")) {
    throw new Error("Sabado should be habil by default");
  }
  if (esDiaHabil("2026-10-10", { sabadoHabil: false })) {
    throw new Error("Sabado should not be habil if sabadoHabil is false");
  }

  // Sumar días hábiles
  if (sumarDiasHabiles("2026-10-09", 1) !== "2026-10-10") {
    throw new Error("sumarDiasHabiles failed from 09 to 10 Oct");
  }
  if (sumarDiasHabiles("2026-10-10", 1) !== "2026-10-13") {
    throw new Error("sumarDiasHabiles failed skipping Sun 11 and Holiday 12");
  }

  return true;
}

export { runTests };
