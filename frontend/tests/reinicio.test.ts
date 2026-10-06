// frontend/tests/reinicio.test.ts
//
// Reinicio del formulario tras un guardado exitoso: el estado vuelve al
// inicial sin compartir estructuras con él (una actualización in-place no
// podría corromper `initialFormData`) y las vistas previas blob: se liberan.
//
// Ejecución: node --import ./tests/register-alias.mjs --test tests/*.test.ts

import { describe, test } from "node:test";
import assert from "node:assert/strict";

import {
  clonarEstadoInicial,
  liberarPreviews,
} from "../src/modules/smu/reinicio";

interface Estado {
  nombre: string;
  fotos: Record<string, string>;
  lista: Array<{ id: number }>;
  responsable: { nombre: string };
}

const baseEstado = (): Estado => ({
  nombre: "",
  fotos: {},
  lista: [{ id: 1 }],
  responsable: { nombre: "" },
});

describe("clonarEstadoInicial", () => {
  test("devuelve copias de los objetos y colecciones de primer nivel", () => {
    const base = baseEstado();
    const copia = clonarEstadoInicial(base);

    assert.notEqual(copia, base);
    assert.notEqual(copia.fotos, base.fotos);
    assert.notEqual(copia.lista, base.lista);
    assert.notEqual(copia.responsable, base.responsable);
    assert.deepEqual(copia, base);
  });

  test("mutar la copia no toca el estado inicial", () => {
    const base = baseEstado();
    const copia = clonarEstadoInicial(base);

    copia.fotos.slot_1 = "blob:http://localhost/nueva";
    copia.lista.push({ id: 2 });
    copia.responsable.nombre = "Técnico";

    assert.deepEqual(base.fotos, {});
    assert.equal(base.lista.length, 1);
    assert.equal(base.responsable.nombre, "");
  });
});

describe("liberarPreviews", () => {
  test("revoca todas las URLs blob: anidadas", () => {
    const revocadas: string[] = [];
    const original = URL.revokeObjectURL;
    URL.revokeObjectURL = (url: string) => {
      revocadas.push(url);
    };

    try {
      liberarPreviews({
        fotos: [{ previewUrl: "blob:http://localhost/uno" }],
        certificado: { foto_preview: "blob:http://localhost/dos" },
        suelto: "blob:http://localhost/tres",
      });
    } finally {
      URL.revokeObjectURL = original;
    }

    assert.deepEqual(revocadas.sort(), [
      "blob:http://localhost/dos",
      "blob:http://localhost/tres",
      "blob:http://localhost/uno",
    ]);
  });

  test("deja las rutas del servidor y el marcador intactos", () => {
    const revocadas: string[] = [];
    const original = URL.revokeObjectURL;
    URL.revokeObjectURL = (url: string) => {
      revocadas.push(url);
    };

    try {
      liberarPreviews({
        ruta: "/media/smu/foto.jpg",
        remota: "https://cdn.cinco.co/foto.jpg",
        pendiente: "PENDIENTE_SUBIDA",
      });
    } finally {
      URL.revokeObjectURL = original;
    }

    assert.deepEqual(revocadas, []);
  });

  test("no entra en bucle con referencias circulares", () => {
    const revocadas: string[] = [];
    const original = URL.revokeObjectURL;
    URL.revokeObjectURL = (url: string) => {
      revocadas.push(url);
    };

    const circular: Record<string, unknown> = {
      foto: "blob:http://localhost/a",
    };
    circular.self = circular;

    try {
      assert.doesNotThrow(() => liberarPreviews(circular));
    } finally {
      URL.revokeObjectURL = original;
    }

    assert.deepEqual(revocadas, ["blob:http://localhost/a"]);
  });

  test("ignora File, Blob y Date sin intentar recorrerlos", () => {
    const archivo = new File(["x"], "foto.jpg", { type: "image/jpeg" });

    assert.doesNotThrow(() =>
      liberarPreviews({
        archivo,
        blob: new Blob(["x"]),
        fecha: new Date(),
        nulo: null,
        indefinido: undefined,
        numero: 12,
      }),
    );
  });
});
