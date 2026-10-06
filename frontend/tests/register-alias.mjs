// frontend/tests/register-alias.mjs
//
// Permite que `node --test` ejecute los tests TypeScript del frontend sin
// bundler ni dependencias extra: resuelve el alias `@/*` de tsconfig.json y
// añade las extensiones `.ts` que Node no infiere en ESM.
//
// Uso:
//   node --import ./tests/register-alias.mjs --test tests/*.test.ts

import { registerHooks } from "node:module";
import { statSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const SRC = path.resolve(import.meta.dirname, "..", "src");

const candidatos = (base) => [
  base,
  `${base}.ts`,
  `${base}.tsx`,
  path.join(base, "index.ts"),
  path.join(base, "index.tsx"),
];

const buscarArchivo = (base) => {
  for (const ruta of candidatos(base)) {
    try {
      if (statSync(ruta).isFile()) return ruta;
    } catch {
      // no existe: probamos el siguiente candidato
    }
  }
  return null;
};

registerHooks({
  resolve(specifier, context, nextResolve) {
    let base = null;

    if (specifier.startsWith("@/")) {
      base = path.join(SRC, specifier.slice(2));
    } else if (
      (specifier.startsWith("./") || specifier.startsWith("../")) &&
      !/\.[cm]?[jt]sx?$/.test(specifier)
    ) {
      const desde = context.parentURL
        ? fileURLToPath(context.parentURL)
        : SRC;
      base = path.resolve(path.dirname(desde), specifier);
    }

    if (base) {
      const resuelta = buscarArchivo(base);
      if (resuelta) {
        return { url: pathToFileURL(resuelta).href, shortCircuit: true };
      }
    }

    return nextResolve(specifier, context);
  },
});
