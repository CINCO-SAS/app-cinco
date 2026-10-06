# Estado de la auditoría SMU — 2026-09-30

Documento local de trabajo (sin commitear). Continúa de
`diagnostico_smu_2026-09-28.md`.

---

## 0. Arranque limpio — leer esto primero

**Qué es esto**: auditoría del módulo SMU (Django + React/TS) con los errores
ordenados por severidad y su estado. Se actualiza con cada avance.

### Cómo verificar el estado (comandos de siempre)

```powershell
# backend
cd backend
& ".\.venv\Scripts\python.exe" manage.py check --settings=config.settings_test
& ".\.venv\Scripts\python.exe" manage.py test apps.smu --settings=config.settings_test   # 29/29
& ".\.venv\Scripts\python.exe" manage.py spectacular --file schema.yml                   # 2 ops
# frontend
cd frontend
npx.cmd eslint src/lib/api.ts src/lib/fotos.ts src/services/smu.service.ts src/modules/smu tests
npx.cmd tsc --noEmit                                    # solo el preexistente AppSidebar.tsx TS7016
node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --import ./tests/register-alias.mjs --test "tests/*.test.ts"   # 27/27
```

Última corrida (30/09): `check` 0 issues · **29/29** backend · **27/27**
frontend · ESLint 0 · OpenAPI con 2 operaciones (`POST /smu/actividades/`,
`POST /smu/evidencias/`).

### Deuda de 3 errores (18 de 21 resueltos o aceptados)

| # | Sev. | Error | Estado |
|---|---|---|---|
| 1 | 🔴 | **Fotos** | ✅ **CERRADO** — backend + Fase 3 del front (sección 5) |
| 2 | 🔴 | Auditoría: falta `created_by` + log de creación | ⏸ **NO SE IMPLEMENTA** — decisión del usuario (30/09) |
| 3 | 🔴 | Timeout 10 s `frontend/src/lib/api.ts:12,21,30` | ✅ **CERRADO** — `TIMEOUT_MS = 30000`; subida de fotos con 120 s |
| 4 | 🟡 | CI sin tests (`ci-cd_example.yml:15-119` comentado; `frontend-ci_example.yml` sin paso de tests) | ❌ |
| 5 | 🟢 | E1 duplicación ×3 CAPEX (`diagnostico…:234-244`) | ❌ |
| 6 | 🟢 | E2 god-objects: sliders 2168/1714/1069 líneas (`diagnostico…:246-248`) | ❌ |

**Sobre el #2 (A2) — decisión del usuario (30/09):** *el responsable de la
actividad es quien la registra*. El `responsable_cedula` se elige del catálogo
en los 6 formularios (`responsable_1: null` al abrir → pick), llega como
`CharField` en `SmuActividad` (`smu_actividades.py:69`) y con eso la ficha ya
dice quién. No afecta al funcionamiento → **no se añade `created_by`, ni log,
ni migración**. Salvedad anotada (no es un error): es un dato auto-declarado,
no derivado de la sesión; si alguien llena la ficha por otro, el campo dirá el
declarado. Con M3 la API es solo-POST, así que nadie puede editar ni borrar lo
creado.

### Siguiente paso: la CI (única 🟡 media)

Las 🔴 altas quedan **todas resueltas**. Quedan:

1. **CI 🟡** — habilitar `manage.py test` y `spectacular --validation` en el
   backend, y el paso de tests en `frontend-ci_example.yml` (sin tocar
   `package.json`: el runner propio es `tests/register-alias.mjs`).
   *Antes hay que confirmar con el usuario cuál de los dos `*_example.yml` es
   el que se usa en real y si se pueden tocar.*
2. Deuda 🟢 E1/E2 (sin tocar, sin impacto funcional).

### Reglas de la sesión

- Trabajar en español; evidencia `archivo:línea`.
- **No hacer commit** ni tocar archivos ajenos sin pedirlo.
- **No correr `migrate`/`makemigrations` sin avisar** (aunque la `0001→0003`
  ya está aplicada en BD por el usuario).
- Archivos del usuario **ya autorizados para media**: `config/settings.py` y
  `config/urls.py`. Sin autorizar: `config/db_router.py`,
  `frontend/src/components/{layout/AppSidebar,form/Select}.tsx`, `backend/example.http`.
- MySQL `192.168.79.10` inaccesible → tests con `--settings=config.settings_test`.

### Decisiones abiertas del usuario

1. Estructura de carpetas: usé `media/smu/evidencias/…`; existe tuya vacía
   `backend/media/imagenes/smu/` (29/09) — ¿cambiar?
2. `estado` sigue escribible en el serializer (`smu_actividad_serializer.py:417`)
   → ¿`read_only`?
3. Correr `makemigrations --check --dry-run` (solo lectura).
4. `backend/py` (archivo de 0 bytes en `git status`) → ¿borrar?
5. **Nada commiteado**: `backend/apps/smu/`, `frontend/tests/` y los docs siguen sin trackear.

---

## 1. Hecho en esta sesión — severidad 🔴 baja CERRADA

Orden seguido: **E5 → E4 → E6 → E7 → E8**.

### E5 · La completitud ya bloquea el envío
- `frontend/src/modules/smu/components/capex/FormCapexTipologia1Slider.tsx` (y 3, 5):
  `if (!isTipologiaXFormComplete(formData)) { toast.error(...); return; }`
  después de las validaciones de `nombre_estacion` y cédula.
- Antes solo alimentaba un `Alert` y el POST salía igual.

### Fixes ESLint (4 errores preexistentes, no SMU)
- `react-hooks/refs` ×3: `formDataRef.current = formData` movido a `useEffect([formData])`
  en los 3 sliders CAPEX.
- `react-hooks/set-state-in-effect` en `FormCorrectivoEmergenciaSlider.tsx`:
  patrón de React con `categoriaPrevia` (se quitó el import de `useEffect`).

### E4 · Código muerto eliminado
- `backend`: `normalizar_smu_values()` (+ import/`__all__`), `from django.utils import timezone`.
- `frontend`: `crearActividadSMU()`, `import api from "@/lib/api"` en `smu.service.ts`,
  props `errors` en `FormPreventivos/FormCorrectivosCapex/FormEmergenciaCorrectivos`,
  prop `error` en `SelectorTipoActividad` y en `RadioCardGroup`.
- **No se tocó** `SmuFormState.categoria/tipo_formulario`: es redundancia de diseño,
  los campos sí se usan.

### E6 · Strings de negocio con fuente única
- **Nuevo** `frontend/src/modules/smu/constants.ts` (sin imports → sin ciclos):
  `ORIGEN_MATERIAL_OPERARIO`, `CLAVES_ACCIONES_AA`, `ClaveAccionAA`.
- `AccionesMantenimientoAAData` pasó de `interface` a
  `{ id: string } & Record<ClaveAccionAA, string>` → tsc obliga a que la lista,
  la interfaz y los defaults coincidan (antes un campo nuevo **no se enviaba** y
  nadie lo marcaba).
- `FormPreventivoPlantaSlider.tsx`: `FILTRO_TODOS_SISTEMAS`/`FILTRO_TODAS_FOTOS`,
  tipos `EstadoFiltracion` y listas `ESTADOS_PRUEBA`/`ESTADOS_FILTRACION`
  (antes 7 + 3 repeticiones inline de las uniones).
- **No deduplicable sin API** (queda anotado): choices front↔back
  (`ESTADO_PRUEBA_CHOICES`/`ESTADO_FILTRACION_CHOICES`), `CLAVES_ACCIONES_AA` vs
  `help_text` de `SmuPreventivoAaAccion.clave` (exigiría `choices` + migración),
  catálogos SAP hardcodeados en el `constants.ts` de cada tipología.

### E7 · Manejo de errores
- **Nuevo** `getToastErrorMessage(errorDetail, fallback?)` en
  `frontend/src/lib/errorHandler.ts`: 1) `field_errors` de DRF como `campo: mensaje`
  (máx. 3 + `· (y N más)`), 2) `detail`, 3) `message` si no es ruido técnico de axios,
  4) genérico por tipo, 5) fallback si el tipo es `UNKNOWN`.
- **Nuevo** `frontend/src/modules/smu/errors.ts` → `toastErrorActividad(err)`.
- Los 6 submits ahora: `onError: toastErrorActividad,`
  (antes: `toast.error(err.message || "No se pudo guardar la actividad.")` ×6).
- El `catch {}` de los 6 **es necesario**: `useFormSubmit.ts:39` relanza el error
  después de `onError`; sin catch → unhandled rejection.

### E8 · Documentación
- `@extend_schema` de `list` (`views/smu_actividad_view.py`): + `departamento`
  (se filtraba pero no estaba declarado), + `search`, + `ordering`.
- **Nuevo** `backend/apps/smu/API_REST_REFERENCE.md` → **ignorado por git**
  (regla añadida en `.gitignore:137`).
- `.gitignore`: solo +3 líneas al final, sin tocar cambios previos del repo.

## 2. Hecho en esta sesión — oleada de tests (builders del frontend)

Alcance decidido: **solo builders del frontend** (backend se queda con sus 9
tests; el módulo es de creación, no de manipulación total).

- **Nuevo runner sin dependencias** `frontend/tests/register-alias.mjs`:
  hooks de `node:module` que resuelven el alias `@/*` de `tsconfig.json` y las
  extensiones `.ts` que Node no infiere en ESM. **No se tocó `package.json`.**
- **Nuevo** `frontend/tests/smu.service.test.ts` (19 tests) + `smoke.test.ts` (1).
- Comando (PowerShell, comillas porque Node hace el glob; `--test tests/` falla):
  ```
  node --disable-warning=MODULE_TYPELESS_PACKAGE_JSON --import ./tests/register-alias.mjs --test "tests/*.test.ts"
  ```
- Resultado: **20/20 OK**.

Cobertura por builder: cabecera `categoria`/`tipo_formulario`; recorte y
descarte de vacíos; responsable (cédula + nombre completo y fallback a
`tecnico_nombre`); checklist `SI/NO/NA`; las 11 claves de acciones AA con
`orden`; números en formato español (`220,5`→220.5, `1.800`→1800); colecciones
vacías omitidas; `region`→`regional`; tildes de filtración conservadas
(`SÍ`/`N/A` a diferencia de AA); checklist solo con `estado`; fotos `blob:` →
`PENDIENTE_SUBIDA` y `https://` conservado; `categoria` → `tipo_registro` del
material; `comprado_operario` según `ORIGEN_MATERIAL_OPERARIO`;
`implica_exclusion` booleano; transporte condicional; CAPEX t1/t3/t5
(cabecera, `inventario_capex`+`mano_obra_capex`, `spt_filas`, `detalle.tipologia`).

Hallazgos **sin cambios en `src`** (comportamiento correcto, ahora cubierto):
- `ampl1` (formulario, `FormPreventivoAASlider.tsx:111`) → `amp_l1` (payload,
  `smu.service.ts:328`): renombramiento intencional, ya tiene test.
- `spt_filas` no pasa por `limpio()` (`smu.service.ts:886-891`): en JS quedan
  claves `undefined`, que JSON descarta → sin impacto en la red (cosmético).
- Las colecciones vacías (`tecnicos`, `aa_condensadoras`, …) se eliminan del
  payload: el backend debe tolerar el campo ausente (y lo hace).

## 3. Hecho en esta sesión — severidad 🟠 media · M1 validación de negocio

**Cerrado B4** (enumeración, coherencia, exclusividad de detalles, rango):

- `backend/apps/smu/models/smu_actividades.py` → nueva constante de clase
  `TIPO_FORMULARIO_CHOICES` (los 6 formularios), junto a `CATEGORIA_CHOICES`.
  **No** se agregó `choices=` al campo `tipo_formulario`: eso haría que Django
  registrara un cambio de estado y dejara una migración pendiente sin
  generar; el enum se exige desde el serializer.
  *(Si prefieres `choices=` a nivel de modelo, hay que correr `makemigrations`
  — avísame; no lo corrí por regla de la sesión.)*
- `backend/apps/smu/serializers/smu_actividad_serializer.py`:
  - `tipo_formulario` pasó a `ChoiceField` con mensaje en español → el texto
    libre devuelve 400 y **aparece como enum en OpenAPI**
    (`TipoFormularioEnum` con los 6 valores).
  - Constantes `TIPOS_POR_CATEGORIA` y `DETALLES_POR_TIPO` + dos reglas en
    `validate()`: coherencia `categoria`↔`tipo_formulario` y "máximo un bloque
    de detalle, y debe corresponder al tipo enviado".
  - `item_numero` del checklist AA → `IntegerField(min_value=1, max_value=39)`
    (el `help_text` decía "Del 1 al 39" sin validador).
  - En PATCH parcial, lo que no llega en el payload se lee de la instancia
    para poder evaluar igual las reglas.
- `backend/apps/smu/tests.py` → **+9 tests** (`SmuValidacionNegocioTests`)
  que van **al POST del ViewSet** (201/400 reales, no solo el serializer) y
  un test anti-deriva que obliga a que enum, `TIPOS_POR_CATEGORIA` y
  `DETALLES_POR_TIPO` sigan diciendo lo mismo.

Mensajes que ahora recibe el frontend (400, ya los formatea
`getToastErrorMessage`):
- `tipo_formulario: tipo_formulario no es válido. Opciones válidas: …`
- `tipo_formulario: El tipo de formulario 'estandar' no corresponde a la
  categoría 'preventivos'. Opciones válidas: aire_acondicionado, planta.`
- `Solo puede enviarse un bloque de detalle por actividad; se recibieron:
  detalle_preventivo_aa, detalle_capex.` (texto plano, sin prefijo de campo)
- `checklist_aa: item_numero debe estar entre 1 y 39.`

## 4. Hecho en esta sesión — severidad 🟠 media · M2 + M3 (API a solo POST)

**Decisión del usuario:** *SMU solo toma datos y guarda* → la API queda con
**un único endpoint**: `POST /smu/actividades/`.

- `backend/apps/smu/views/smu_actividad_view.py` (**reescrito**):
  `ModelViewSet` → `mixins.CreateModelMixin + viewsets.GenericViewSet`.
  Se eliminaron `list` (con sus filtros/`search`/`ordering` y el
  `@extend_schema` de E8), `retrieve`, `update`, `partial_update`, `destroy`,
  la acción `cambiar-estado` y el `prefetch_related` masivo.
  La ruta la define el `DefaultRouter` (`apps/smu/urls.py:6`): al exponer solo
  `create`, el router descarta el resto (`rest_framework/routers.py:280`).
- `services/smu_actividad_service.py`: **borrado** `actualizar_actividad_smu`
  (M2: 16 `delete()` + recreate) + su export en `services/__init__.py`.
  *(Decisión del usuario: "borrarlo con su test".)*
- `tests.py`: −1 test de update, −3 de `cambiar-estado`, **+4 guard tests**
  (`SmuApiSoloPostTests`): `POST` por URL = 201 · `GET/PUT/PATCH/DELETE` en la
  colección = 405 · ruta detalle = 404 · `cambiar-estado` = 404.

**Efecto en el backlog:**
- **M2 cerrado** (por retirada de ruta: el service ya ni existe).
- **M3 cerrado**: 1 endpoint en lugar de 8.
- **B2 cerrado de paso** (`cambiar-estado`: estaba en el diagnóstico
  `:162`, ni siquiera figuraba en el backlog de media).
- **A3 (sin paginación) deja de aplicar**: no queda ningún `GET`.
- **A2 se reduce**: ya no se puede editar ni borrar; queda la atribución
  (`SmuActividad` no tiene `created_by`) y el registro de auditoría.

**Coste asumido:** el trabajo de E8 sobre `list` (11 query params con
`@extend_schema`) queda anulado — OpenAPI ahora documenta **1 operación**.

**Frontend: 0 cambios** (los 6 formularios ya eran `method: "POST"`).

## 5. Hecho en esta sesión — severidad 🔴 alta · A1 fotos (backend + front)

**Decisión del usuario:** *solo backend en esta tanda* (la conexión del
frontend = Fase 3 queda pendiente), topar a **5 fotos por campo** como el PHP,
y permiso para editar `config/settings.py` y `config/urls.py`.

Base aprovechada: la **Fase 1** del 29/09 ya estaba completa — `lib/fotos.ts`
(magic bytes + `revokeObjectURL`), `useFotoSlot.ts`, `FotoSlotCard` con
validación y `onUpload(file)` conectado en los 6 sliders, y `sanitizeRuta()` →
`PENDIENTE_SUBIDA` en `smu.service.ts:183-190`.

- `backend/config/settings.py` (**tuyo, con permiso**): `MEDIA_URL='/media/'`,
  `MEDIA_ROOT=<BASE_DIR>/media`, `FILE_UPLOAD_MAX_MEMORY_SIZE=6 MB` y
  `DATA_UPLOAD_MAX_MEMORY_SIZE=10 MB` (por defecto Django rechaza >2,5 MB y
  una foto de 5 MB moría antes de llegar a la vista).
- `backend/config/urls.py` (**tuyo, con permiso**): `urlpatterns += static(…)`
  → sirve `/media/` **solo con DEBUG** (fuera de dev lo sirve el servidor web).
- `.gitignore`: + `media/`.
- **Nuevo** `apps/smu/services/smu_evidencia_service.py`:
  `validar_archivo_foto()` (magic bytes con Pillow → niega SVG/GIF/HTML
  renombrado; ≤5 MB; JPG/PNG/WebP) y `guardar_evidencia()` → nombre `uuid4`,
  **WebP calidad 80** + corrección EXIF (equivalente del `saveFiles()` del PHP)
  en `media/smu/evidencias/{actividad_id | 'borrador'}/{seccion}/`.
  Lee sobre `BytesIO` para que la validación sea repetible: la llaman el
  serializer y el servicio y Pillow dejaba cerrado el stream del upload
  *(bug que pillaron los tests: el PNG iba bien y el 2º chequeo rechazaba)*.
- **Nuevo** `serializers/smu_evidencia_upload_serializer.py` +
  **Nuevo** `views/smu_evidencia_view.py` → **`POST /smu/evidencias/`**
  (multipart, patrón de `apps/empleados`).
- `serializers/smu_actividad_serializer.py`: `validate_ruta_archivo()` rechaza
  `blob:`/`data:` (400 con instrucción de subirlo primero) y
  `_validar_tope_evidencias()` → ≤5 por `campo_origen`.
- `apps/smu/urls.py`: router registra `evidencias` (solo `create`).
- **+11 tests** (`SmuEvidenciaUploadTests`) → **29**.

### Fase 3 (frontend) — ✅ CERRADA el 30/09 · cierra el #1

**Diseño**: los builders siguen **síncronos** (no se rompieron sus tests); los
`File` se recogen en una lista de *pendientes* y el submit los sube **antes**
del `POST /smu/actividades/` — la API es solo-POST, no hay PUT que adjunte
fotos después. Un `blob:` jamás viaja por la red: `sanitizeRuta()`
(`smu.service.ts:212`) lo convierte en el marcador `PENDIENTE_SUBIDA` y
`subirPendientes()` lo pisa con la ruta real.

- `frontend/src/services/smu.service.ts`:
  - `SMU_EVIDENCIAS_ENDPOINT` + `subirEvidenciaSMU(file, {seccion, campo_origen})`
    → `POST /smu/evidencias/` multipart, `timeout: 120000`. Carga `lib/api` con
    **import dinámico** a propósito: los tests de los builders no deben
    arrastrar axios ni `errorHandler` (usa `enum`, ilegible para el strip-only
    de Node — lo destapó la primera corrida de los tests).
  - `PendienteSubida` + `subirPendientes(pendientes, subir?)`: sube **en orden**
    (una por una) y al primer fallo lanza `ErrorSubidaFotos` → **no se crea la
    actividad**; mejor abortar que persistir fotos perdidas.
  - `conOrden()` ya **no copia** las filas: conserva la identidad de cada
    objeto para que `aplicar(ruta)` escriba en la fila exacta que viaja en el
    payload (antes hacía `{...item}` y el parcheo se habría perdido).
  - `certificados()`: acepta `file_certificado`/`file_sitio`; los placeholders
    `"foto_certificado"`/`"foto_sitio"` pasaron a `sanitizeRuta()` (marcador
    honesto en vez de un literal que se guardaba en BD).
  - Los 6 builders aceptan `pendientes?: PendienteSubida[]` **como último
    parámetro opcional** → los 19 tests originales siguen intactos.
  - AA ahora usa `foto.previewUrl` como ruta (antes `foto.nombre`, que nunca es
    una ruta navegable), igual que planta y correctivo.
- `frontend/src/lib/api.ts`: `TIMEOUT_MS = 30000` en las 3 instancias → **#3
  (A4) cerrado**; antes `timeout: 10000`.
- `frontend/src/lib/fotos.ts`: `campoArchivoDeFoto()`
  (`foto_panoramica_preview` → `foto_panoramica_file`).
- `frontend/src/modules/smu/errors.ts`: `toastErrorFotos(err)` — solo avisa si
  el error es `ErrorSubidaFotos`; los de `useFormSubmit` ya los cubre `onError`
  (por eso el `catch` no puede ser un toast genérico: se duplicaría).
- Los 6 sliders: arman el payload con `pendientes`, hacen `await
  subirPendientes(...)` y en el `catch` llaman a `toastErrorFotos`.
- **Hueco real encontrado y cerrado**: CAPEX T1 y T5 **tiraban el `File`** de las
  fotos genéricas (`handleGenericPhotoUpload` solo guardaba el `blob:` de
  preview → eran 9 fotos imposibles de subir). Ahora se guardan en el campo
  compañero (`tipologia1/types.ts`, `tipologia5/types.ts`).
- **+7 tests** → **27/27** (suite `subida de fotos (Fase 3)`): identidad de la
  fila tras subir, cola por sección/campo, orden secuencial, fallo que aborta
  sin seguir subiendo, certificados y campos compañeros de CAPEX.
- Compresión en cliente: **NO** por ahora (el servidor ya re-encripta a WebP
  q80; comprimir dos veces degrada la calidad). Anotado por si se revisa.

**Pendiente de *deploy* (configuración, no de código)**:

- Servir `/media/` fuera de DEBUG: `config/urls.py:43-44` solo lo hace con
  DEBUG → en producción hace falta `alias` en nginx hacia `MEDIA_ROOT`.
- `MEDIA_ROOT` en un volumen persistente (con FS efímero las fotos desaparecen
  al recrear el contenedor).
- `client_max_body_size ≥ 6m` en nginx: por defecto es `1m` y devolvería 413
  aunque el backend acepta 5 MB (`settings.py:296-301`).
- Podar `media/smu/evidencias/borrador/` huérfanos (usuario que cancela el
  guardado tras haber subido fotos); reorganizarlos tras crear exigiría un PUT
  que la API no tiene por diseño.

**Ojo:** existe `backend/media/imagenes/smu/` (vacía, creada el 29/09, sin
referencias en el código). Si prefieres esa estructura en vez de
`smu/evidencias/`, se cambia en el servicio y en los tests.

## 6. Verificación (última corrida)

| Comando | Resultado |
|---|---|
| `npx.cmd eslint src/lib/api.ts src/lib/fotos.ts src/services/smu.service.ts src/modules/smu tests` | exit 0 |
| `npx.cmd tsc --noEmit` | solo el preexistente `AppSidebar.tsx` |
| `node … --import ./tests/register-alias.mjs --test "tests/*.test.ts"` | **27/27 OK** (19 builders + 7 Fase 3 + smoke) |
| `manage.py check` | 0 issues |
| `manage.py test apps.smu --settings=config.settings_test` | **29/29 OK** (3 crear + 2 serializer + 9 M1 + 4 guard POST + 11 subida de fotos) |
| `manage.py spectacular --file …` | exit 0 · **2 operaciones**: `POST /smu/actividades/` y `POST /smu/evidencias/` (multipart), sin `{id}` ni `cambiar-estado` |
| `PIL features.check('webp')` | `True` (la conversión a WebP funciona; hay fallback por si acaso) |
| Smoke test `getToastErrorMessage` (13 casos) | 13/13 OK |

Herramientas de verificación guardadas en
`%TEMP%\opencode\` (`test.js` con los 13 casos de error de DRF, `tsconfig.json`
para compilar `errorHandler.ts`; *`check_schema.py` quedó obsoleto: ya no existe
`GET /smu/actividades/`*).

**Nada está commiteado.** Todo el trabajo SMU sigue como `??`/` M` en `git status`.

## 7. Pendiente — severidad 🟠 media y 🟢 baja

### 🟠 Media

*Queda **un solo ítem**: la CI.*

1. ~~**Validación de negocio (B4)**~~ → **CERRADO** en la sección 3
   (enumeración, coherencia `categoria`↔`tipo_formulario`, exclusividad de
   detalles, rango de `item_numero`).
2. ~~**`delete+recreate` de subtablas (M2)**~~ → **CERRADO** en la sección 4:
   `actualizar_actividad_smu` fue borrado con su test (decisión del usuario).
3. ~~**Tests backend**~~ → **18/18**, cubren el POST end-to-end (6 formularios
   por par `categoria`↔`tipo_formulario` + 4 rechazos de validación) y la
   superficie de la API (`SmuApiSoloPostTests`).
4. **CI sin backend**: no corre `manage.py test` ni `spectacular --validation`.
5. ~~**Endpoints sin consumidor (M3)**~~ → **CERRADO** en la sección 4:
   la API solo expone `POST` (8 endpoints → 1).

### 🟢 Baja — deuda técnica (sin tocar)

1. **E1 · Duplicación ×3 en CAPEX**: `Paso1General.tsx` casi idéntico en las
   3 tipologías, 4 catálogos por cada `constants.ts`, `completion.ts` ×3,
   evidencias/transportes T3 vs T5 y los 6 `handleSubmit` iguales
   (`diagnostico…:234-244`).
2. **E2 · God-objects**: `FormPreventivoPlantaSlider.tsx` (2168 líneas),
   `FormPreventivoAASlider.tsx` (1714), `FormCorrectivoEmergenciaSlider.tsx`
   (1069) (`diagnostico…:246-248`).
3. ~~**E3 · Fuga de blob URLs**~~ → **CERRADO** por el trabajo del 29/09:
   los 6 sliders importan `liberarPreviewUrl` de `lib/fotos.ts` y la llaman al
   cambiar, eliminar y desmontar (86 usos; `revokeObjectURL` centralizado en
   `lib/fotos.ts:187`).

## 8. Severidad 🔴 alta — ✅ sin pendientes

1. ~~**Fotos**~~ → **CERRADO** (sección 5): backend (`MEDIA_*`,
   `POST /smu/evidencias/`, WebP q80, tope 5, 29/29) + Fase 3 del frontend
   (subida al guardar en los 6 formularios, 27/27).
2. ~~**Auditoría / `created_by`**~~ → **NO SE IMPLEMENTA** por decisión del
   usuario (30/09): *el responsable de la actividad es quien la registra* →
   `responsable_cedula` basta como registro de quién, no afecta al
   funcionamiento. Con M3 la API es solo-POST (nadie edita ni borra). Salvedad
   en el §0: el campo es auto-declarado, no derivado de la sesión.
3. ~~**Sin paginación (A3)**~~ → **NO APLICA**: no queda ningún `GET`, así que
   no hay array que paginar. Revivir si algún día aparece un listado/tablero.
4. ~~**Timeout 10s**~~ → **CERRADO** en la Fase 3:
   `lib/api.ts:14` (`TIMEOUT_MS = 30000`) y 120 s para la subida de fotos.

> **Conclusión: cero pendientes de severidad 🔴.** Lo que queda en pie es
> la CI (🟡, sección 7) y la deuda técnica E1/E2 (🟢).

## 9. Reglas de la sesión (recordatorio)

- Trabajar en español; evidencia `archivo:línea`.
- **No hacer commit** ni tocar archivos ajenos sin pedirlo.
- **No correr `migrate`/`makemigrations` sin avisar** (BD ajena).
- Comandos: frontend con `npx.cmd`; backend con
  `& ".\.venv\Scripts\python.exe"`; tests con `--settings=config.settings_test`
  (MySQL `192.168.79.10` inaccesible, timeout 10060).
- Archivos del usuario: `backend/config/settings.py` y `config/urls.py`
  **tocados con permiso** (media, sección 5). **No tocados**: `config/db_router.py`,
  `frontend/src/components/{layout/AppSidebar,form/Select}.tsx`, `backend/example.http`.

## 10. Ruido preexistente a ignorar

- `TS7016` de `@tabler/icons-react` en `AppSidebar.tsx`.
- Avisos `python-dotenv` líneas 141-150, `RequestsDependencyWarning`,
  `mysql.W002` (strict mode).
- `manage.py spectacular`: warnings/errores globales de `ia_dev`/auth/enums
  (ninguno del módulo SMU).
