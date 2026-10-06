# Auditoría: función de guardado de imágenes (SMU)

_Fecha: 2026-09-29_
_Alcance: solo análisis (sin cambios de código), por decisión del usuario._
_Decisión registrada sobre la Fase 2: el binario se sube **al guardar el formulario**._

**Archivos analizados**

| Capa | Archivo |
|---|---|
| Slot de foto | `frontend/src/components/form/input/FotoSlotCard.tsx` |
| Slot + descripción | `frontend/src/components/form/input/FotoSlotWithDescripcion.tsx` |
| Sliders (6) | `capex/FormCapexTipologia1/3/5Slider.tsx`, `preventivos/FormPreventivoAASlider.tsx`, `preventivos/FormPreventivoPlantaSlider.tsx`, `correctivos/FormCorrectivoEmergenciaSlider.tsx` |
| Builder de payload | `frontend/src/services/smu.service.ts` |
| Cliente HTTP | `frontend/src/lib/api.ts` |
| Modelo | `backend/apps/smu/models/smu_actividades.py` (`SmuActividadEvidencia`, L220) |
| Serializer | `backend/apps/smu/serializers/smu_actividad_serializer.py` (L65) |
| Servicio | `backend/apps/smu/services/smu_actividad_service.py` (L76, L198) |
| Settings/URLs | `backend/config/settings.py` (L288-291), `backend/config/urls.py` |
| Estudio previo | `estudio_captura_fotos_smu_2026-09-29.md` |

---

## 1. Resumen (cómo funciona hoy)

1. **Selección**: `FotoSlotCard` valida `file.type` (jpeg/jpg/png/webp) y `file.size ≤ 5 MB`,
   avisa con `toast.error` y entrega el evento al slider.
2. **Preview**: el slider hace `URL.createObjectURL(file)` y guarda esa URL de blob en su
   estado (`foto_preview`, `foto_antes_preview`, `fotos[slot]`, …).
3. **Submit**: `smu.service.ts` convierte cada preview a una fila de `SmuActividadEvidencia`
   (`seccion`, `campo_origen`, `ruta_archivo`, `nombre_original`, `descripcion`, `orden`).
4. **Backend**: `crear_actividad_smu()` crea las filas de texto en una transacción atómica.

**El binario nunca sale del navegador.** No existe `MEDIA_ROOT`/`MEDIA_URL`
(`settings.py` solo define `STATIC_*`), ni endpoint multipart en SMU (el único
`MultiPartParser` del backend está en `apps/empleados`), ni servicio `subirEvidenciaSMU`.
La foto vive únicamente como preview efímera que muere al recargar.

---

## 2. Fallas encontradas

### 2.1 Críticas (lógicas / pérdida de datos)

1. **La foto no se guarda nunca.** Modelo, serializer y servicio ya existen, pero no hay
   endpoint de subida ni configuración de media → todo el "guardado" es metadata de texto.
2. **`ruta_archivo` persiste basura que aparenta ser una ruta** (`smu.service.ts`):

   | Caso | Valor enviado | Línea |
   |---|---|---|
   | CAPEX (todas las tipologías) | `blob:http://localhost:3000/uuid…` (URL de preview) | L741 / L749-790 |
   | Preventivo AA / Planta | nombre local del archivo (`IMG_4821.JPG`) | L227, L388 |
   | Correctivo / Emergencia | id efímero de React (`ev-171234`) | L557 |
   | Hallazgos de planta | nombre del campo (`evidencia_1`) | L404 |
   | Certificados | literales `foto_certificado`, `foto_sitio` | L293-298 |

   Consecuencia: la BD queda llena de registros de evidencia que no apuntan a ningún archivo
   real y que, si algún día se hidratan, rompen la UI. Agravante: `ruta_archivo`
   **no tiene `blank=True`** (`smu_actividades.py:245`), así que el campo es obligatorio y el
   frontend se ve forzado a rellenarlo; el fallback `?? "pendiente"` de `smu.service.ts:187`
   es **código muerto** (el argumento `campo_origen` ya viene con default `"campo"`).
3. **El `File` se descarta en la mayoría de formularios.** CAPEX tipologías 1/3/5 (todos los
   handlers) y Correctivo/Emergencia guardan solo `previewUrl`; el binario se pierde.
   En AA y Planta sí se guarda `file` en el estado, pero **jamás se usa**: la prop
   `onFileChange` de `FotoSlotCard` **no está conectada en ningún slider** (grep: 0 usos),
   es API muerta.
4. **No hay lectura de vuelta**: ningún componente consume `evidencias` al editar/consultar.
   Tras guardar y recargar, las fotos desaparecen de la UI **sin ningún aviso**
   (pérdida silenciosa para el usuario).
5. **`actualizar_actividad_smu` borra y recrea todas las evidencias** en cada edición
   (`smu_actividad_service.py:198-201`). Cuando existan archivos en disco, cada edición
   deja huérfanos y elimina el historial de evidencias.

### 2.2 Validación / seguridad

6. **6 inputs crudos con `accept="image/*"` que no pasan por `validarFoto`** → sin límite de
   5 MB, aceptan GIF/BMP/TIFF/**SVG**:
   `FormPreventivoPlantaSlider.tsx` L1838, L1963, L2121, L2155 (certificado, evidencias de
   hallazgos, foto en sitio) y `FormPreventivoAASlider.tsx` L1650, L1701 (certificado, foto
   en sitio).
7. **La validación confía en `file.type` del navegador** (`FotoSlotCard.tsx:32`): es
   falsificable y vacío en algunos renombrados/cámaras Android. No hay lectura de magic
   bytes en el front **ni en el backend** (no existe validación server-side alguna).
8. **`FOTO_ACCEPT = "image/*"`** (`FotoSlotCard.tsx:22`) es más permisivo que la lista de
   tipos permitidos → el usuario elige un GIF y recién ahí ve el error. Además `image/jpg`
   **no es un MIME estándar** (debería ser solo `image/jpeg`).
9. **Archivos de 0 bytes pasan la validación** (no se verifica `size > 0`).
10. **Sin tope de cantidad de fotos**: `handleAddEvidencia`, `handleAddHallazgo`,
    `handleAddJustificacion` son ilimitados. El `maxArchivos = 5` del PHP no se portó y el
    backend no limita filas.
11. **Backend sin límites de upload**: no hay `FILE_UPLOAD_MAX_MEMORY_SIZE` ni
    `DATA_UPLOAD_MAX_MEMORY_SIZE` (cuando exista el endpoint, un upload de 100 MB entraría
    igual y llenaría el temp dir).

### 2.3 Memoria / rendimiento

12. **Fuga de memoria**: hay 20 llamadas a `URL.createObjectURL` en los 6 sliders y **cero**
    `revokeObjectURL` en todo el flujo de fotos (los 4 `revoke` del repo son de CSV/PDF).
    Cada cambio/eliminación de foto y cada montaje/desmontaje de slider deja el blob vivo.
13. **Al cambiar una foto no se libera la anterior** en AA/Planta (solo se sobreescribe la URL).

### 2.4 UX / correctitud del componente

14. **`FotoSlotCard` no limpia `input.value` tras una selección válida** (solo en el error,
    L96) → elegir **el mismo archivo** otra vez (botón "Cambiar" o tras eliminar) no dispara
    `change` y el slot no responde. Bug clásico de inputs file.
15. Los 6 inputs crudos no muestran ningún error si el archivo no cumple reglas.
16. El slot se pone con acento de marca (estado "cargado") aunque solo sea un preview local:
    **la UI暗示 que la foto está guardada** cuando no lo está.
17. Los errores de validación viven solo en el componente que los usa; los sliders no tienen
    forma de saber que la selección falló (no hay estado de error compartido).

### 2.5 Coherencia de datos / mantenibilidad

18. **`nombre_original` solo se llena en AA/Planta**; en CAPEX y correctivos se pierde.
19. **El FK `material` de `SmuActividadEvidencia` (`smu_actividades.py:236`) nunca se envía**
    → las fotos de insumos no quedan vinculadas a su fila; el vínculo es por índice
    (`insumo_${index+1}_foto`), frágil ante reordenamientos/eliminaciones.
20. **`firmas_cierre.ruta_firma` recibe un nombre digitado por el usuario**, no una ruta, y
    `ruta_foto` de técnicos jamás se envía: campos con nombre de archivo y contenido de texto.
21. **`api.ts` romperá la subida futura**: instancia axios con
    `Content-Type: "application/json"` fijo (L10-17) y `timeout: 10000` → el multipart
    requiere sobreescribir el header y un timeout mayor para 5 MB.
22. **Duplicación**: ~8 handlers de foto casi idénticos + 6 inputs crudos duplicados entre
    AA y Planta; la lógica de validación está en un componente que no todos usan.
23. **Reglas del legacy PHP no portadas**: MIME real (`finfo_file`), tope 5 fotos/campo,
    nombre único en disco, errores devueltos al usuario.

---

## 3. Plan de mejora (fases)

### Fase 1 — Frontend: robustez y honestidad (sin migración, sin endpoint)

1. Módulo único de validación (`lib/fotos.ts`): tipos MIME reales, `size > 0`, límite MB y
   **lectura de magic bytes** (JPEG/PNG/WebP); `accept` estricto
   (`image/jpeg,image/png,image/webp`); eliminar `image/jpg`.
2. `FotoSlotCard`: resetear `input.value` también en el caso válido; exponer estado de
   error al formulario; consumir la nueva validación.
3. Hook `useFotoPreview`: crea/revoca object URLs (revoke al cambiar, al eliminar y al
   desmontar) → cierra la fuga de memoria en los 6 sliders.
4. Guardar el `File` en **todos** los formularios (CAPEX y correctivos hoy lo descartan) y
   conectar `onFileChange` en los sliders que hoy no lo usan.
5. **Payload honesto**: `evidencia()` no debe escribir `blob:`, ids React ni literales en
   `ruta_archivo`; mientras no exista endpoint se envía un marcador explícito
   (`PENDIENTE_SUBIDA`) y se conserva `nombre_original` en todos los builders.
6. Tope de fotos por sección compartido front/back (constante única) + aviso visible.
7. Migrar los 6 inputs crudos al `FotoSlotCard`/`FotoSlotWithDescripcion` (elimina la
   ruta sin validación y la duplicación).

### Fase 2 — Backend: subida real (subida **al guardar**)

1. `settings.py`: `MEDIA_ROOT` + `MEDIA_URL` y serving en `urls.py` (solo en dev/BACKEND).
2. **Instalar Pillow** (no está en `requirements.txt`) para validar contenido y recomprimir.
3. `POST /smu/evidencias/` (multipart, patrón de `apps/empleados`): valida MIME real +
   magic bytes + `size ≤ 5 MB` + tope de cantidad; nombre `uuid4()`; guarda en
   `media/smu/evidencias/{actividad|borrador}/{seccion}/`; WebP calidad 80 (equivalente de
   `saveFiles()`); devuelve `ruta_archivo`.
4. Serializer: rechazar `blob:`/`data:` en `ruta_archivo`; `blank=True` en el modelo
   (**requiere migración → avisar antes de `migrate`**, regla de sesión).
5. Límites de upload globales (`FILE_UPLOAD_MAX_MEMORY_SIZE`, `DATA_UPLOAD_MAX_MEMORY_SIZE`).

### Fase 3 — Conexión y ciclo de vida

1. `smu.service.ts`: `subirEvidenciaSMU(file, meta)`; al **submit** subir primero las fotos
   y luego crear la actividad (o `FormData` mixto) con reintento y mensajes de error.
2. axios: header multipart y timeout dedicado para uploads.
3. Edición: **no** borrar/recrear filas con archivo físico; sincronizar por `campo_origen`
   y limpiar huérfanos en disco (decisión: qué pasa con fotos de filas eliminadas).
4. Vincular `material_id` en fotos de insumos (aprovecha el FK existente).

### Fase 4 — Visibilidad y garantías

1. Hidratar `evidencias` al editar/consultar (mostrar la foto guardada, no el preview).
2. Feedback honesto en el slot: "pendiente de subir" / "subida correcta".
3. Tests: validación de magic bytes, límites, builders de payload y la view de subida.

---

## 4. Decisiones abiertas restantes

1. ¿Comprimir en el cliente (canvas → WebP) antes de subir para bajar el payload?
2. ¿Carpeta por actividad o por usuario/fecha? (afecta el borrado posterior)
3. ¿Servir `/media/` públicamente o solo mediante un endpoint autenticado?
4. ¿Límite final de fotos por sección: 5 (como el PHP) u otro?
