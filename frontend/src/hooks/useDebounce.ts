// src/hooks/useDebounce.ts
//
// Devuelve `valor` RETRASADO: mientras el usuario escribe se entrega el valor
// inmediato y solo se propaga el último cuando deja de haber cambios durante
// `retardo` ms.
//
// Para qué sirve: acoplar un input de texto a una petición HTTP. Sin esto,
// cada tecla dispara un `GET` con su `COUNT(*)` — con la tabla de salidas
// (~253 mil filas) eso es innecesario y también paga el `router.replace` de
// la sincronización con la URL.
//
// Es genérico a propósito: cualquier filtro de texto puede usarlo.

import { useEffect, useState } from "react";

export const useDebounce = <T>(valor: T, retardo = 300): T => {
  const [diferido, setDiferido] = useState(valor);

  useEffect(() => {
    const temporizador = setTimeout(() => setDiferido(valor), retardo);
    return () => clearTimeout(temporizador);
  }, [valor, retardo]);

  return diferido;
};
