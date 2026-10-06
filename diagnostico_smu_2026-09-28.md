# Diagnóstico del área SMU

Fecha: 2026-09-28
Rama: `feat/smu_gestion_actividades`
Alcance: `backend/apps/smu/**`, `frontend/src/modules/smu/**`, `frontend/src/services/smu.service.ts`, y su montaje en `backend/config/`.
Método: revisión estática de código + greps de verificación sobre los hallazgos. **No se ejecutó la aplicación ni se tocó la base de datos.**

> Convención de este documento: **SMU es un área organizativa**, no un módulo ni una tecnología (`CONTEXT.md:15-18`). Las rutas citadas son literales.

---

## 1. Resumen ejecutivo

El área tiene un backend y un frontend bastante completos: 20 modelos, un ViewSet con 8 endpoints, un service transaccional, y 6 formularios wizard con builders de payload. No es un prototipo a medias.

Tampoco es todavía algo que pueda ponerse en producción. Los fallos se agrupan en tres causas raíz:

1. **El pipeline de datos está cortado.** La migración está desactualizada y sin aplicar, y no hay forma de subir las fotos. Un formulario que no puede guardar sus evidencias no está terminado, esté o no hecho el resto.
2. **El backend confía ciegamente en el cliente.** No valida, no autoriza por objeto, no audita quién aprueba. `tipo_formulario` es texto libre y el serializer acepta cualquier combinación de secciones. La única barrera real es el frontend.
3. **No hay red de seguridad.** Cero tests de SMU y una CI que no ejecuta tests. Cualquier refactor se hace a ciegas.

Detrás hay deuda de mantenimiento seria (duplicación ×3 en CAPEX, componentes de 2 168 líneas), pero eso es lo segundo: arreglar el diseño sin antes tener el pipeline funcionando y tests es refactorizar sobre arena.

---

## 2. Mapa del área

### Backend — `backend/apps/smu/`

| Archivo | Líneas | Rol |
|---|---|---|
| `models/smu_actividades.py` | 894 | 20 modelos + `normalizar_smu_values()` (sin usos) |
| `serializers/smu_actividad_serializer.py` | 388 | 19 serializers de subtabla + `SmuActividadSerializer` raíz anidado |
| `services/smu_actividad_service.py` | 295 | `crear_actividad_smu` (26-141) y `actualizar_actividad_smu` (144-295), ambos `@transaction.atomic` |
| `views/smu_actividad_view.py` | 195 | `SmuActividadViewSet` (único) + acción `cambiar-estado` |
| `urls.py` | 10 | `DefaultRouter` → `actividades` |
| `admin.py` | 188 | 19 inlines + 4 `ModelAdmin` |
| `tests.py` | **1** | Contenido: `#` |
| `migrations/0001_initial.py` | 399 | 10 tablas base (2026-09-21) |
| `migrations/0002_...py` | 705 | Rediseño: ~83 `RemoveField`, ~30 `AddField`, 9 modelos nuevos (2026-09-25) |

No hay `filters.py`, `permissions.py`, `exceptions.py` ni `pagination.py`.

### Frontend — `frontend/src/modules/smu/`

| Archivo | Líneas | Rol |
|---|---|---|
| `components/SmuDashboard.tsx` | 103 | Orquestador, `switch(grupo)` en 43-71 |
| `components/preventivos/FormPreventivoPlantaSlider.tsx` | **2168** | Wizard planta, checklist de 105 ítems |
| `components/preventivos/FormPreventivoAASlider.tsx` | **1714** | Wizard aire acondicionado |
| `components/correctivos/FormCorrectivoEmergenciaSlider.tsx` | **1069** | Wizard correctivo/emergencia |
| `components/capex/FormCapexTipologia{1,3,5}Slider.tsx` | 507 / 417 / 500 | Wizards CAPEX |
| `components/capex/tipologia{1,3,5}/` | ~265 / ~470 / ~440 c/u | Pasos, `constants.ts`, `completion.ts`, `types.ts` |
| `components/common/` | — | `CatalogoFrecuenteDropdowns` (206) y 7 compartidos |
| `types/smu.types.ts` | 34 | `GrupoActividad`, `CategoriaActividad`, `TipoFormulario`, `SmuFormState` |

Servicio: `frontend/src/services/smu.service.ts` — **1050 líneas**, builders para los 6 formularios.
Store: `frontend/src/store/formCatalog.store.ts` (chips del Catálogo Frecuente, es global).

### Endpoints

Montaje: `backend/config/urls.py:37` → `path("smu/", include("apps.smu.urls"))`.

| Método | Ruta | Vista |
|---|---|---|
| GET | `/smu/actividades/` | `list` — view 112 |
| POST | `/smu/actividades/` | `create` → `crear_actividad_smu` — view 120 |
| GET | `/smu/actividades/{pk}/` | `retrieve` — view 134 |
| PUT/PATCH | `/smu/actividades/{pk}/` | `update` → `actualizar_actividad_smu` — view 142 |
| DELETE | `/smu/actividades/{pk}/` | `destroy` — view 158 |
| PATCH | `/smu/actividades/{pk}/cambiar-estado/` | `cambiar_estado` — view 177 |

**El frontend solo consume el `POST`.** Los otros 7 endpoints no tienen ningún llamador en `frontend/src`.

---

## 3. Cómo funciona el flujo

```
/smu → SmuDashboard → switch(grupo) → selector de categoría → slider (wizard)
   → build*Payload(formData)          [smu.service.ts]
   → useFormSubmit                    [POST /smu/actividades/]
   → crear_actividad_smu() @transaction.atomic
   → cabecera SmuActividad + hasta 15 colecciones
```

### `tipo_formulario`: la bifurcación vive solo en el frontend

| `tipo_formulario` | familia | `categoria` |
|---|---|---|
| `aire_acondicionado` | preventivos | `preventivos` |
| `planta` | preventivos | `preventivos` |
| `tipologia1` | CAPEX (Reforma SPT/Pararrayos) | `correctivos_capex` |
| `tipologia3` | CAPEX (Climatización) | `correctivos_capex` |
| `tipologia5` | CAPEX (Subestaciones/MT-BT) | `correctivos_capex` |
| `estandar` | correctivos y emergencias | `correctivos` \| `emergencias` |

En el backend, `tipo_formulario` es un `CharField` **sin `choices`** (`models:45-48`, solo `help_text`) y **no existe ni un solo `if tipo_formulario == ...`** en `backend/apps/smu/`. Aparece solo en: definición, índice compuesto, campo del serializer, filtro de listado y admin.

El serializer raíz declara las 15 secciones anidadas, **todas `required=False`** (`serializers:311-334`). Quien decide qué detalle se crea es el cliente, enviando o no esa sección. Nada impide enviar `detalle_capex` junto con `tipo_formulario="planta"`, o enviar dos detalles a la vez.

---

## 4. Fallos

Cada hallazgo fue verificado con grep o lectura directa del archivo indicado.

### 4.1 🔴 Bloque A — El pipeline está cortado

#### A1. La migración `0002` está desactualizada y sin aplicar

Le faltan **7 columnas** que el modelo ya define y que el frontend ya envía:

| Columna | Modelo | Frontend |
|---|---|---|
| `SmuActividad.categoria_criticidad` | `models:65-70` | `smu.service.ts:583` |
| `SmuActividadMaterial.origen_material` | `models:179-184` | `smu.service.ts:615` |
| `SmuActividadEvidencia.descripcion` | `models:247-251` | `smu.service.ts:189,406,557` |
| `SmuDetalleFallaIntervencion.detalles_plano` | `models:802-813` | `smu.service.ts:630` |
| `…reinstalacion / cambio / reparacion` | `models:804-813` | `smu.service.ts:632-636` |

**Verificación:** `grep -E "categoria_criticidad|origen_material|detalles_plano" backend/apps/smu/migrations/` → **0 coincidencias**.

Además, según `SESION_PENDIENTES_SMU.md:5`, la `0002` **no está aplicada en BD**. Consecuencias según el estado real:

- BD sin `0002` → no existen las 9 tablas nuevas ni las columnas añadidas: todo POST revienta.
- BD con `0002` aplicada → faltan las 7 columnas de arriba: los formularios `estandar` y los materiales correctivos revientan con `OperationalError`.

**Corrección documentada en el repo** (`SESION_PENDIENTES_SMU.md:69`): borrar `0002_...py` y correr `makemigrations smu --noinput`. ⚠️ **Único punto que toca la base de datos.**

#### A2. Las fotos nunca se suben

- `grep MEDIA_ROOT|MEDIA_URL backend/config/` → **0 coincidencias**. No hay `MEDIA_ROOT`, `MEDIA_URL` ni `DEFAULT_FILE_STORAGE`.
- El único `MultiPartParser` del backend está en `apps/empleados/views/empleado_view.py:14,29`.
- El propio código lo admite: `smu.service.ts:7-10`.

`ruta_archivo` termina guardando:

| Origen | Qué guarda | Dónde |
|---|---|---|
| Fallback | `"pendiente"` | `smu.service.ts:187` |
| Correctivos | el id interno como ruta | `smu.service.ts:557` (`evidencia("evidencias", e.id, e.id, …)`) |
| CAPEX | el blob temporal `blob:http://…` | `smu.service.ts:749-809, 886-921, 953-1003` |
| Placeholders | `"foto_certificado"`, `"foto_sitio"` | `smu.service.ts:294-298, 475-478` |

Un `blob:` URL muere al recargar la pestaña: **ninguna evidencia guardada es recuperable.**

#### A3. Timeout de 10 s contra payloads enormes

`frontend/src/lib/api.ts:12,21,30` → `timeout: 10000`.

Un preventivo de planta envía 105 ítems de checklist + hasta 10 plantas + hallazgos + firmas + certificados + evidencias. Si el front aborta antes, el backend sigue escribiendo (está en `@transaction.atomic`, `service:26`): **el usuario ve un error, pero el registro se creó** → duplicados al reintentar.

### 4.2 🔴 Bloque B — Seguridad e integridad

#### B1. Cualquiera crea una actividad ya "aprobada"

`estado` está en `fields` (`serializers:363`) y **no** está en `read_only_fields` (`serializers:388` → solo `id, created_at, updated_at`). El valor por defecto del modelo es `'enviado'` (`models:93`), pero el cliente puede enviar `estado="aprobado"` directamente.

El flujo de aprobación se salta por completo en el alta.

#### B2. `cambiar-estado` sin máquina de estados, sin auditoría, sin autorización

`view:177-195`. Única validación: que el valor pertenezca a `ESTADO_CHOICES` (182-189).

- Acepta `rechazado → aprobado` y cualquier salto.
- No registra **quién** aprobó ni **cuándo**: `SmuActividad` no tiene `created_by`/`approved_by` (`models:93-95`).
- **`grep request.user backend/apps/smu/` → 0 coincidencias.** El `request.user` no se usa en ningún punto del área.
- Devuelve `{'error': "…"}` con 400 (`view:184-189`) en vez de `rest_framework.exceptions.ValidationError`, por lo que no sigue el formato DRF y el frontend no puede mostrar errores por campo.

#### B3. El ViewSet no declara permisos

`view:11` — `SmuActividadViewSet` no tiene `permission_classes`. Aplica el global de `config/settings.py:155-157`.

Al no existir `has_object_permission`, cualquier usuario autenticado **o cualquier API Key** puede:

- `DELETE /smu/actividades/{pk}/` de cualquier actividad
- `PUT` / `PATCH` de cualquier actividad
- `PATCH .../cambiar-estado/` de cualquier actividad

#### B4. Cero validación de negocio

**`grep "def validate" backend/apps/smu/` → 0 coincidencias.** Concretamente:

- `tipo_formulario` sin `choices` → texto libre. No se valida coherencia `categoria` ↔ `tipo_formulario` (`preventivos` + `estandar` se guarda igual).
- No se valida `fecha_fin >= fecha_inicio` (`models:75-76`).
- `SmuDetallePreventivoAaChecklist.item_numero` documenta "Del 1 al 39" (`models:421`) sin validador de rango.
- Se aceptan dos detalles a la vez (ver §3).
- Las únicas unicidades reales son las de BD: `uk_aa_actividad_item` (`models:426-431`) y `uk_planta_actividad_sistema_comp` (`models:769-774`).

#### B5. HTTP 500 por duplicados

`create` (`view:120-127`) y `update` (`view:142-151`) no capturan `IntegrityError`. Un payload que choque contra los `unique` de BD provoca **500 en vez de 400**.

### 4.3 🟠 Bloque C — Rendimiento y API

#### C1. Sin paginación y con prefetch masivo

`config/settings.py:150-162` no define `DEFAULT_PAGINATION_CLASS`. `GET /smu/actividades/` devuelve **todas** las actividades, y el serializer raíz anida 15 colecciones que se pre-cargan siempre (`view:17-38`).

El prefetch está bien hecho (no es N+1), pero es 1 query gigante por colección × N filas + una respuesta enorme. El `prefetch_related` también se paga en `retrieve` y `cambiar-estado`, donde casi no se necesita.

#### C2. `actualizar_actividad_smu` borra y recrea todas las colecciones

`service:188-216, 226-249, 259-272, 290-293`. Estrategia *delete + recreate* para las colecciones, `update_or_create` para las OneToOne.

Cada PUT/PATCH destruye `id`, `created_at` e historial de cada hijo. Hoy es inutilizable además porque **no existe formulario de edición en el frontend**.

#### C3. 7 de 8 endpoints sin consumidor

`grep SMU_ACTIVIDADES_ENDPOINT frontend/src` → solo `method: "POST"` en 6 sitios. `GET`, `retrieve`, `PUT/PATCH`, `DELETE` y `cambiar-estado` son código pagado, documentado en OpenAPI y **sin una sola prueba**.

### 4.4 🟡 Bloque D — Sin red de seguridad

#### D1. Cero tests de SMU

- `backend/apps/smu/tests.py` → **1 línea: `#`**.
- `frontend/package.json:14` → `"test": "echo \"No tests configured yet\""`.
- `glob frontend/src/**/*.{test,spec}.*` → **0**.

Contraste con el resto del backend, que sí tiene cobertura: `empleados/tests.py` (~420 líneas), `operaciones/tests.py` (~290), `security/tests.py` (~320), `authentication/tests.py` (~155), `ia_dev/tests/` (~85 archivos). **SMU es la única app transaccional seria sin tests.**

Infra: runner estándar de Django (`manage.py test`), con variante `backend/config/settings_test.py` (SQLite en memoria) invocable con `--settings=config.settings_test`. **No hay pytest, conftest, tox ni coverage.**

#### D2. La CI no ejecuta nada

- `.github/workflows/check-branch.yml` (25 líneas) → **solo verifica que el PR venga de `develop`**.
- `ci-cd_example.yml` y `frontend-ci_example.yml` → plantillas de ejemplo (`*_example`).

No hay ninguna ejecución automática de tests ni de lint.

### 4.5 🟢 Bloque E — Deuda técnica

#### E1. Duplicación ×3 en CAPEX

| Qué | Dónde |
|---|---|
| `Paso1General.tsx` prácticamente idéntico | `tipologia1/`, `tipologia3/`, `tipologia5/` |
| `OPCIONES_UNIDAD_MEDIDA`, `OPCIONES_TIPO_TRANSPORTE`, `CATALOGO_SUMINISTROS_FRECUENTES`, `CATALOGO_ACTIVIDADES_FRECUENTES` | `constants.ts` de las 3 (T1: 17-209; T3: 14-415; T5: 16-381) |
| `completion.ts` con la misma estructura `STEP_CHECKS` | ×3 |
| Evidencias T3 (886-921) vs T5 (953-1038) y transportes T3 (931-939) vs T5 (1013-1029) | `smu.service.ts`, copias casi literales |
| Los 6 `handleSubmit` | el mismo bloque, 6 veces |

Mantenimiento de catálogos y reglas: **×3**.

#### E2. God-objects

`FormPreventivoPlantaSlider.tsx` (2168), `FormPreventivoAASlider.tsx` (1714), `FormCorrectivoEmergenciaSlider.tsx` (1069) concentran estado, handlers, catálogos y UI.

#### E3. Fuga de memoria de blob URLs

`URL.createObjectURL` en **18 sitios** del área; **`revokeObjectURL` → 0 coincidencias** en `frontend/src/modules/smu/`.

- `FormPreventivoPlantaSlider:672,727,737`
- `FormPreventivoAASlider:529,559`
- `FormCapexTipologia1Slider:145,222,301,344`
- `FormCapexTipologia3Slider:144,221,282`
- `FormCapexTipologia5Slider:97,162,239,300,347`
- `FormCorrectivoEmergenciaSlider:348`

(En el resto de `frontend/src` sí se usa: rrhh, agente-ia, operaciones, csv.)

#### E4. Código muerto

| Qué | Dónde |
|---|---|
| `normalizar_smu_values()` — exportado en `models/__init__.py:2,28`, **0 usos** | `models/smu_actividades.py:5-24` |
| `crearActividadSMU` — exportado, **0 importadores** (los formularios usan `useFormSubmit`) | `smu.service.ts:1047-1050` |
| Props `errors` **nunca pasadas** → la UI de error de esos radios es inalcanzable | `FormPreventivos.tsx:12`, `FormCorrectivosCapex.tsx:13`, `FormEmergenciaCorrectivos.tsx:13-15`, `SelectorTipoActividad.tsx:10` (frente a `SmuDashboard.tsx:47-66, 87-90`) |
| `SmuFormState.categoria/tipo_formulario` vive en `SmuDashboard`, pero cada builder re-hardcodea su `tipo_formulario` | `smu.service.ts:268,450,575,849,942,1032` |

#### E5. La validación de completitud es cosmética

`completion.ts` calcula `isTipologia1FormComplete`, pero su resultado **solo alimenta un `Alert`** (`FormCapexTipologia1Slider.tsx:387-399`). `handleSubmit` (352-383) envía igual.

Lo único que se valida de verdad antes del POST, en los 6 formularios, es `nombre_estacion` + cédula del responsable (p. ej. `FormCapexTipologia1Slider:355-365`). Y en el backend solo esos dos campos son no-null (`models:62, 77-80`).

#### E6. Strings de negocio duplicados

- `"OPERARIO (COMPRADO EN SITIO)"` en `smu.service.ts:620` **y** `FormCorrectivoEmergenciaSlider.tsx:67`. Si cambia uno, el flag `comprado_operario` deja de activarse.
- Claves de acciones AA duplicadas entre `smu.service.ts:198-210` y `help_text` de `models:558-564`.
- `ESTADO_PRUEBA_CHOICES` / `ESTADO_FILTRACION_CHOICES` (`models:585-596`) duplican las opciones del front (`smu.service.ts:424-445`).
- Catálogos SAP completos hardcodeados en `constants.ts` (no vienen de la API).
- `"TODOS"` / `"TODAS"` como valores sentinela (`FormPreventivoPlantaSlider.tsx:742,757`).

#### E7. Manejo de errores genérico

- Los 6 submits usan el mismo fallback `toast.error(err.message || "No se pudo guardar la actividad.")` — `FormPreventivoAASlider:595`, `FormPreventivoPlantaSlider:799`, `FormCorrectivoEmergenciaSlider:321`, `FormCapexTipologia1Slider:378`, `FormCapexTipologia3Slider:330`, `FormCapexTipologia5Slider:391`.
- Ninguno traduce los `field_errors` de DRF.
- `catch {}` vacío en los 6 (597 / 802 / 323 / 380 / 332 / 393).

#### E8. Sin documentación

`grep -i smu backend/README*.md backend/scripts/*.md` → **0 referencias** a la API SMU. Solo está en OpenAPI/Swagger. Además, el `@extend_schema` de `list` (`view:101-110`) omite los parámetros `search` y `ordering` que el endpoint sí soporta.

**No hay `console.log`, `print()`, `TODO`, `FIXME`, `XXX` ni `HACK` en toda el área** — eso está bien. La deuda está marcada con comentarios explícitos: `smu.service.ts:7-10` (Tarea B) y `smu.service.ts:637` (decisión pendiente sobre `tipo_intervencion`).

---

## 5. Hallazgos de dominio

### 5.1 Colisión "Actividad" / "Estado"

El glosario define **Actividad** como *"la unidad de trabajo registrada en operaciones"* y **Estado** con 6 valores (`CONTEXT.md:43-55`). Pero `SmuActividad` es otra entidad homónima con otra máquina de estados:

| | `actividad_model.py:30-40` (operaciones) | `smu_actividades.py:36-41, 93` (SMU) |
|---|---|---|
| valores | `pendiente`, `en_progreso`, `completada`, `cancelada`, `pausada`, `reprogramada` | `borrador`, `enviado`, `aprobado`, `rechazado` |
| defecto | `pendiente` | `enviado` |

Son dos semánticas distintas: una es **progreso del trabajo**, la otra es **aprobación de un reporte**. Un lector del glosario asumirá la equivocada.

**Acción tomada (2026-09-28):** `CONTEXT.md` ahora distingue **Actividad** / **Estado** (operaciones) de **Actividad SMU** / **Estado de aprobación**.

### 5.2 El glosario se incumple en el código

`CONTEXT.md:17` prohíbe *"módulo SMU, sistema SMU, servicio SMU"*, pero la docstring de la vista dice literalmente *"módulo SMU"* (`view:99` y `view:103`). Alcance: documentación, no runtime.

### 5.3 Decisiones sin resolver

Del `SESION_PENDIENTES_SMU.md:76-86`, siguen abiertas:

1. `tipo_intervencion` vs las 3 columnas nuevas `reinstalacion`/`cambio`/`reparacion` → ¿borrar la primera o dejarla como resumen? (`smu.service.ts:637`)
2. `mp_termostato` / `mp_termostato_post` → el front llena `temp_termostato_pos_ajuste`, se asumió `…_post` y `mp_termostato` queda huérfano. **Semántica sin confirmar.**
3. Reglas de completitud de los 3 `completion.ts` (¿fotos obligatorias?, ¿matrícula obligatoria?) → son de negocio.
4. Columnas huérfanas: `descripcion_generales`, `recomendaciones_aliado`.
5. Si eliminar `0002_...py` ya (es regenerable).

---

## 6. Corrección al archivo de pendientes

`SESION_PENDIENTES_SMU.md` está **desactualizado en la tarea E** (línea 70):

> *"Frontend: crear `frontend/src/services/smu.service.ts` … y conectar los `handleSubmit` (hoy solo hacen `console.log`). No existe ningún servicio SMU en el frontend."*

**Ya no es cierto:**

- `frontend/src/services/smu.service.ts` **existe con 1050 líneas**, con builders para los 6 formularios (`buildPreventivoAAPayload`, `buildPreventivoPlantaPayload`, `buildCorrectivoEmergenciaPayload`, `buildCapexTipologia{1,3,5}Payload`).
- Los 6 `handleSubmit` hacen `submit(build*Payload(...), { endpoint: SMU_ACTIVIDADES_ENDPOINT, method: "POST" })` de verdad — p. ej. `FormCapexTipologia1Slider.tsx:367-382`.

El archivo además está fechado *vie 25 sep 2026*; hoy es *lun 28 sep 2026*.

**Estado real de las tareas del §3:**

| Tarea | Estado real |
|---|---|
| **C** Cablear serializers + service | Verificar: los 9 modelos nuevos **sí** están en el serializer raíz (`serializers:326-334`). Falta confirmar `SmuActividadMaterialSerializer` (lista explícita) y el service. |
| **B** Endpoint de subida de fotos | ❌ Pendiente (A2 de este informe) |
| **D** Regenerar la migración | ❌ Pendiente (A1 de este informe) |
| **E** Frontend service + submits | ✅ **Hecha** |
| **F** Verificar dropdowns en navegador | ❌ Pendiente (no se ejecutó el navegador en este análisis) |
| **G** Catálogo MO a `CatalogoFrecuenteDropdowns` | ❌ Pendiente (E1 agrava: es ×3) |

---

## 7. Plan priorizado

### Oleada 1 — Que no se rompa

1. **A1** Regenerar la migración: borrar `0002_...py` → `makemigrations smu --noinput` → revisar el diff → `manage.py check`. ⚠️ Requiere decisión explícita sobre la BD.
2. **A2** `MEDIA_ROOT`/`MEDIA_URL` en `config/settings.py` + `POST /smu/evidencias/` multipart + reemplazar los `blob:`/`"pendiente"` del front por la URL devuelta.
3. **A3** Subir el timeout de `api.ts` (o hacerlo configurable por endpoint).

### Oleada 2 — Que no sea explotable

4. **B1** `estado` a `read_only_fields`.
5. **B3** `permission_classes` en el ViewSet + `has_object_permission`.
6. **B2** Máquina de transiciones válidas + `aprobado_por`/`aprobado_en` + `request.user` + error en formato DRF.
7. **B4** `choices` en `tipo_formulario`, coherencia `categoria`↔`tipo_formulario`, exclusividad de detalles, `fecha_fin >= fecha_inicio`.
8. **B5** Capturar `IntegrityError` → 400.

### Oleada 3 — Que aguante

9. **D1** Tests antes de refactorizar: `crear_actividad_smu` (los 6 formularios), `actualizar_actividad_smu`, el ViewSet (permisos, `cambiar-estado`), y `validate()` de B4.
10. **C1** Paginación.
11. **E1** Deduplicar CAPEX (catálogos y `Paso1General` primero: más valor, menos riesgo).
12. **E3** `revokeObjectURL` en los 18 sitios.
13. **E5** Que la completitud bloquee de verdad, no solo avise.

### Fuera de alcance de SMU (marcar para otro dueño)

- `backend/config/urls.py:28` monta el admin en `path('/', admin.site.urls)` en lugar de `path('admin/', …)`; la línea original está comentada en `:27`. Afecta al enrutado global.
- CI que no ejecuta tests (D2) es de repo, no del área.

---

## 8. Anexo — Errores preexistentes (no arreglar)

De `SESION_PENDIENTES_SMU.md:109-116`, confirmados como ajenos a este trabajo:

- `tsc`: `src/components/layout/AppSidebar.tsx(11,36): error TS7016` — `@tabler/icons-react` sin tipos.
- `python-dotenv could not parse statement starting at line 141..150`.
- `RequestsDependencyWarning: urllib3/chardet/charset_normalizer doesn't match`.
- `mysql.W002: MySQL Strict Mode is not set for database connection 'default'`.

## 9. Anexo — Estado de git

Rama `feat/smu_gestion_actividades`, **16 cambios sin commit**:

```
 M backend/config/db_router.py
 M backend/config/settings.py
 M backend/config/urls.py
 M backend/example.http
 M frontend/src/components/form/Select.tsx
 M frontend/src/components/layout/AppSidebar.tsx
?? CONTEXT.md
?? SESION_PENDIENTES_SMU.md
?? backend/apps/smu/
?? backend/py
?? frontend/src/app/(private)/smu/
?? frontend/src/modules/smu/
?? frontend/src/services/smu.service.ts
?? frontend/src/store/formCatalog.store.ts
?? package.json
```

`backend/py` y `package.json` (raíz) parecen artefactos accidentales: conviene revisar si van al commit o al `.gitignore`.

## 10. Anexo — Comandos de verificación

```powershell
# ── Backend (workdir: ...\app-cinco\backend) ──
#   ⚠️ NO usar `python` (3.14 sin Django) ni `py -3.11`.
#      El venv está en backend\.venv (oculto para los glob).
& ".\.venv\Scripts\python.exe" manage.py check
& ".\.venv\Scripts\python.exe" makemigrations smu --dry-run -v 2   # vería las 7 columnas
#   o el wrapper: .\scripts\dj.ps1 check

# ── Tests (SQLite en memoria, no toca la BD) ──
& ".\.venv\Scripts\python.exe" manage.py test apps.smu --settings=config.settings_test

# ── Frontend (workdir: ...\app-cinco\frontend) ──
#   ⚠️ usar npx.cmd, NO npx.ps1 (execution policy lo bloquea)
npx.cmd prettier --write <files>
npx.cmd tsc --noEmit
npx.cmd eslint <files>
```
