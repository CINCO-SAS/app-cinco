# Informe de avance — Migración del módulo Transporte (PHP legacy → Django)

> **Fecha:** 2026-10-15 · **Rama:** `feat/modulo_transporte` (commits locales, sin push)
> **Base documental:** `PLAN_BACKEND_DJANGO_CONSOLIDADO_MODULO_TRANSPORTE.md` (especificación)
> y `ROADMAP.md` (seguimiento vivo, §2 tramos / §6 registro).
> **Fuente de verdad de las reglas:** los PHP legacy de `MIGRACIONES/`
> leídos línea por línea; cualquier regla de este informe tiene su
> referencia de archivo/línea en el código o en el ROADMAP.

---

## 1. Resumen ejecutivo

- **Tramo A completo** (A1 parámetros · A2 liquidaciones · A3 ETL) y
  **B2, B4 y B3 (núcleo) cerrados** — el corazón transaccional (registro
  de salidas con CR-9, anticolisión y máquina de estados D-A11, el
  backoffice F4 y el reporte fotográfico F3).
- **F5-1…F5-7 cerrados**: cuenta de cobro, gráfico, informe mensual,
  export server-side, **WFM masivo (cola + lote + worker CLI)**,
  **planilla oficial de salida** (consecutivo atómico + QR) y
  **agregados de sábana** (día/área/matriz/nómina/liquidación).
- **428 tests OK** (416 transporte + 12 `apps.common`), `manage.py check` sin
  issues, `pyflakes` sin incidencias propias y **0 errores de OpenAPI** en el
  módulo; DoD cumplido en cada hito (tests verdes → check → commit local).
- **G2 ABIERTO desde el 20-oct**: `0001`–`0006` ya aplicados contra `default`
  = `db_cincosas` (17 tablas `transporte_*` + 79 permisos) y las auditorías
  C2 ejecutadas en modo **solo lectura** sobre `azul`. El backend **sigue sin
  escribir en la BD de producción**: la carga real (C3) la ejecuta el usuario.
  ⚠️ `sql_mode` vacío en `default` y `azul` → sin `STRICT_TRANS_TABLES` MySQL
  trunca en silencio: **habilitarlo antes de C3**.
- **PHP legacy intacto**: hasta el cutover único (D1) el sistema
  actual sigue vivo.
- **Insumos externos que faltan**: **G1** (solo la **tabla** `common.Festivo`;
  el calendario ya corre con algoritmo ∪ catálogo JSON editable), **G3** (el
  modelo `common.Area` — **la fuente ya está decidida** en D-A2/B11, solo
  falta escribirlo) y **G4** (D-A9 asignar móvil + D-A10 router de la BD
  negra). Del lado de la infraestructura falta el **alias `negra`** en
  `DATABASES` (hoy solo hay `default`, `azul`, `logistica_cinco`).

### Estado por fase

| Fase | Contenido | Avance |
|---|---|---|
| F0 Diccionario y mapeo FKs | Mapeo aplicado en los modelos | **~95%** (auditorías CR-3 → C2 ya ejecutadas) |
| F1 Base Django y Festivos | 16 modelos + migración; algoritmo de festivos portado + **catálogo JSON editable** (`apps/common/festivos/`); falta la tabla `common.Festivo` | ~85% (solo falta la tabla → G1) |
| F2 Flota y Conductores | CRUD + semáforo + documentos + CSV (CR-13) + QR (D-A8) + **ficha de contacto del conductor (A1)** + **licencias y cilindraje recuperados** | ~95% (falta T6 → C3; línea corporativa → G2) |
| F3 Kiosco y Fotos | **CERRADO**: núcleo B2 (alta S6, consulta B1, escaneo S1) + fotos B3 (ventana 10:00–16:00, agenda, 1–5 imágenes, match OT) + kiosco S3 (pre-chequeo) y S4 (consulta por placa). Pendiente **solo S2** (asignar móvil → G4) | ~80% |
| F4 Backoffice y Novedades | **CERRADO** (B4): aprobar-lote, rechazar, validar, eliminar, novedades, historial | ~85% (falta B11 → G3, ya con fuente decidida) |
| F5 Liquidaciones e Informes | **F5-1…F5-7 cerrados**, incluido el **formato físico F-104** (P1) | **100%** |
| F6 ETL histórico | 5 cargadores + 2 comandos de auditoría (solo lectura); corrida real → C3 | ~55% |
| F7 Cutover / F8 Estabilización | — | 0% |

---

## 2. Entregables por hito

| Hito | Commit | Qué quedó hecho |
|---|---|---|
| **F0/F1-base** | `313ec7a` | 16 modelos + `0001_initial` + choices + admin; registro en `settings`/`urls`/`db_router` (multi-BD, D-A10) |
| **F2 conductores** | `ca7f522` | `ConductorService`/viewset: ABM, unicidad de cédula, edad derivada (nunca persistida) |
| **F2 flota** | `8eaa38a` | `FlotaService`: ABM con placa única, **semáforo SOAT/CDA en servidor**, ficha documental, documentos |
| Fix MEDIA_ROOT | `f88221c` | Tests con MEDIA_ROOT temporal (sin artefactos en el repo) |
| **CR-13 CSV bancarios** | `5fd3583` | Upsert por placa, separador autodetectado (`;`/`,`), sanitización regex, reporte de rechazadas |
| **D-A8 QR** | `c97b9bb` | QR de verificación **en memoria** bajo demanda (placa); elimina `codigo_qr` persistido |
| **A1 parámetros** | `58889b8` | `FechaLimiteCierre` (unicidad mes/año) + `JefeValidador` con regla `isUserLeaderOfSalida`; **áreas/carpetas JSON ⇒ no exige G3** |
| **A2 liquidaciones** | `7a4d89c` | Sábanas **CR-10** (mensual APROBADO+REPORTADO+VALIDADO vs pronto pago solo APROBADO, retroceso de 6 meses), consecutivos atómicos (`select_for_update`, arranque 1000), gate `editar_tras_cierre`, upsert de pagos; `services/periodos.py` |
| **A3 ETL** | `3c8a457` | `apps/transporte/etl/` (normalizadores D-A4/D-A6, convertidores puros, carga con FKs por cédula/placa + lotes 2.000) + `manage.py migrate_transporte_legacy` (`--fuente/--lote/--dry-run`) + muestras locales; conciliación estricta (exit 1 si descuadra) |
| **Calendario (B1 interino)** | `59c80dd` | Port de `festivosColombia.ts` → 18 festivos Ley 51/1983 (Emiliani + Pascua Butcher/Meeus), `sabado_habil` configurable (default hábil = frontend; CR-9 pasa `False` por paridad legacy), caché por año |
| **Calendario reutilizable (G1 parcial)** | *(commit `6f3e837`)* | Movido a **`apps/common/festivos/`** (cualquier módulo lo importa) + **catálogo `festivos_colombia.json`** (2022–2030) como fuente editable: `es_festivo` = **algoritmo ∪ catálogo**, `festivos_del_anio()`, `recargar_catalogo()`. Se corrigió el JSON de origen (San Pedro y San Pablo 2027 estaba en el lunes anterior → 2027-07-05) |
| **Formato físico F-104 (P1)** | *(este commit)* | Verificado `planilla_salida.php` → `POST /planillas/formato/`: HTML autocontenido (LETTER horizontal, hoja por vehículo, QR en base64, casillas en blanco para firmas). Mejoras: fecha real, conductor/teléfono/valor día reales (el legacy los dejaba vacío), consecutivo impreso y sin código de barras (D-A8) |
| **B2 salidas (F3)** | `cffd8f8` | `SalidaService`: ventana CR-9, CR-1/CR-2, snapshots, exigencia de personal, máquina D-A11 con `SalidaHistorial` + `AuditoriaLog`, `aprobar_masivo` atómico, `eliminar` lógico; endpoints `GET/POST /salidas/`, `GET /salidas/{id}/`, `POST /kiosco/escanear/` |

---

## 3. Cobertura de reglas de negocio verificadas

Leyenda: ✅ implementada y testeada · 🟡 servicio listo, falta endpoint/Dato · ⬜ pendiente de gate.

### Reglas CR (contrato de migración)

| CR | Regla | Estado |
|---|---|---|
| CR-1 | Unicidad salida (vehículo, día) contra vivas | ✅ servicio (constraints reales → **C2**) |
| CR-2 | Unicidad salida (móvil, día) contra vivas | ✅ servicio (misma nota C4/C2) |
| CR-3 | Placa única (la BD legacy no la tenía) | 🟡 servicio (auditoría de duplicados → C2) |
| CR-4 | Modelo completo (faltaban ~9 tablas) | ✅ en modelos (16) |
| CR-5 | `area` nullable por carga histórica | ✅ (snapshot + TODO FK `common.Area` → G3) |
| CR-6 | Conductor externo ≠ Empleado nómina (D-A2) | ✅ modelos + ETL |
| CR-7 | Absorber las 3 pestañas + kiosco + flota + fotos + planilla | 🟡 matriz §6: ver §4 |
| CR-8 | Reemplazar cédulas hardcodeadas por permisos | ✅ `PermisoService` + `GET /permisos/estado/` (E3, migración 0006) |
| CR-9 | Ventana −2 días hábiles + bypass por rol | ✅ `calendario` + `SalidaService.ventana_validacion` (con mensajes legacy literales) |
| CR-10 | Sábanas mensual/pronto-pago con estados exactos | ✅ A2 |
| CR-11 | Planillas con exclusión de motos y consecutivo | ✅ F5-6 (**filtro duro `tipo != 'MOTO'` explícito**, no solo choices) |
| CR-12 | Esquemas SQL quemados → portabilidad | ✅ `DatabaseRouter` (D-A10) |
| CR-13 | Import CSV bancarios con upsert | ✅ F2 |

### Decisiones arquitectónicas (D-A)

| D-A | Decisión | Estado |
|---|---|---|
| D-A1 | Empleado sin JOINs cross-DB (2 pasos cédula→id) | ✅ patrón usado en A1/B2 |
| D-A3 | ViewSet → Service → Serializer | ✅ sin lógica en vistas/serializers |
| D-A4/D-A6 | `USE_TZ` America/Bogota; mayúsculas saneadas | ✅ ETL + servicios |
| D-A8 | QR regenerado bajo demanda, sin persistir | ✅ |
| D-A9 | Asignar móvil vía outbox (S2) | ⬜ → G4 |
| D-A10 | Router multi-BD (`azul`/`negra`/`default`) | ✅ parcial (BD negra → G4) |
| D-A11 | Máquina de estados (RECHAZADO terminal, APROBADO→VALIDADO) | ✅ B2 |
| D-A12 | Unicidad por columna virtual `STORED` | ⬜ → C2 (junto con CR-1/CR-2) |
| D-A13 | Motos fuera del catálogo | ✅ por choices |

### Servicios §5 del plan

| §5 | Servicio | Estado |
|---|---|---|
| §5.1 `SalidaService` | ventana · registrar · listar · aprobar/masivo · rechazar · eliminar · validar | ✅ 7/9 métodos (novedades → B4; `buscar_movil` → T6/G4) |
| §5.2 `LiquidacionService` | sábanas, consecutivos, cerrar_mes | ✅ núcleo cerrado (planillas → F5-6 en `PlanillaService`; informes → F5-7 en `InformeService`) |
| §5.3 `FlotaService` | ABM, semáforo, documentos, CSV, QR | ✅ |
| §5.4 `ConductorService` | ABM, licencia, edad derivada | ✅ |
| §5.5 `ReporteFotograficoService` | agenda + horario 10–16 | ⬜ → B3 |
| §5.6 `PlanillaService` (CR-11) | planillas con exclusión de motos | ✅ F5-6 (alcances PLACA/PROPIO/EXTERNO/RENTING/TODAS, consecutivo atómico, QR) |
| §5.7 `InformeService` | sábanas con filtros server-side + export | ✅ **F5-1…F5-7 cerrados**: cuenta de cobro · series_chart · informe mensual · export (`GET /salidas/export/?formato=xlsx|csv`) · **agregados** (`/informes/dia/`, `/area/`, `/areas-mes/`, `/nomina/`, `/liquidacion/`) |
| §5.8 `ParametrosService` | cierres + jefes | ✅ A1 |
| §5.9 `PermisoService` | grupos/permisos vs cédulas hardcodeadas | ✅ `services/permiso_service.py` + migración 0006 (permisos `puede_programar`/`permiso_especial`/`editar_tras_cierre`) |
| §5.10 `WfmService` | validación WFM masiva (lote + cola + worker) | ✅ F5-5 (`manage.py wfm_worker`) |

---

## 4. Matriz "nada se pierde" (§6 del plan) — estado

| Bloque | Entregado | Pendiente |
|---|---|---|
| **B (gestión)** | B1 filtros `?desde=&hasta=` ✅ · B2 ver cierres ✅ · B8 ficha+semáforo ✅ · B10 valor día/total ✅ (`total_a_pagar`) · B14 badge reportado ✅ · **B4 export xlsx ✅ (F5-4)** · B6/B7 novedades ✅ · B5/B12/B13 🟡 servicio, falta HTTP | B3 ruta cierres `{mes}/{anio}/` · B9 `buscar_movil` (G2/G4) · B11 centros de costos (G3) · B15 permisos por fila |
| **S (kiosco)** | S1 escanear ✅ · S6 grabar salida ✅ · S3 pre-chequeo ✅ · S4 consulta por placa ✅ · **S5 planillas ✅ (F5-6)** | S2 asignar móvil (G4/D-A9) |
| **T (flota)** | T1 ficha · T2 fotos/docs · T3 bancarios · T4 CSV · T5 QR ✅ | T6 teléfonos (G2 + D-A9/D-A10) |
| **D (backoffice/tabla3)** | D1 jefes · D2 cierres · D3 liquidaciones · D4 pagos ✅ | — |
| **C/F** | C1 conductores ✅ | F1 reporte fotográfico → B3 |
| **E (reemplazos)** | E1 `catalogo-operativo` ✅ · E3 `/permisos/estado/` ✅ | E2 helpers JS (frontend) |

---

## 5. Métricas

| Métrica | Valor |
|---|---|
| Tests | **405 OK** (393 transporte + 12 `apps.common`; evolución 87 → 105 → 126 → 134 → 162 → 182 → 214 → 225 → 238 → 246 → 255 → 260 → 330 → 339 → 351 → 353 → 355 → 365 → 377 → 389 → 405) |
| Modelos Django | 16 (+ `0001_initial`–`0005`, choices, admin) |
| Endpoints activos | 13 recursos router (`/conductores/`, `/vehiculos/`, `/parametros/cierres/`, `/parametros/jefes/`, `/liquidaciones/`, `/planillas/`, `/informes/`, `/salidas/`, `/kiosco/`, `/reportes-fotograficos/`, `/validaciones/`, `/wfm/`, `/permisos/`) + acciones (`catalogo-operativo`, `permisos/estado`, `resumen`, `documentos`, `importar-bancarios`, `qr.png`, `inactivar`×2, `pago-mensual`, `pronto-pago`, `sabana`, `consecutivo`, `pago`, `escanear`, `identificar`, `vehiculo/{placa}`, `validar`×3, `aprobar-lote`, `aprobar`, `rechazar`, `novedad`, `historial`, `export`, `cuenta-cobro`, `series-chart`, `mensual`, `areas`, `dia`, `area`, `areas-mes`, `nomina`, `liquidacion`, `generar`, `formato`, `validar-agenda`, `vehiculo-placa`, `wfm/validar`, `wfm/crear-job`, `wfm/estado-job`) |
| Comandos CLI | `migrate_transporte_legacy` (ETL) · **`wfm_worker` (cola WFM)** |
| Archivos PHP legacy modificados | **0** |
| Ejecuciones contra BD real | **0** |

---

## 6. Método y calidad

1. **DoD por hito** (ROADMAP §5): tests verdes → `manage.py check` →
   commit local → registro en §6 + fecha.
2. **Verificación de reglas**: cada validación nueva se escribió leyendo
   el PHP correspondiente (mensaje de error legacy citado al pie de la
   letra en los `ValueError`).
3. **Aislamiento**: tests en SQLite propio; módulos ajenos
   (`operaciones`, `smu`, `ia_dev`) solo se leen cuando el spec lo
   exige (p. ej. `operaciones_agenda` en B3) — nunca se editan.
4. **Arquitectura**: ViewSet → Service → Serializer (D-A3); las vistas
   solo enrutan y traducen `ValueError` a HTTP.
5. **Transaccionalidad**: altas y transiciones de estado en
   `transaction.atomic` con historial por fila + log de auditoría.

---

## 7. Bloqueadores, riesgos y pendientes abiertos

| ID | Tema | Impacto / estado |
|---|---|---|
| **G1** | Calendario `common.Festivo` (decisión de negocio, compañera) | **Resuelto a nivel de comportamiento**: `es_festivo` ya es algoritmo ∪ catálogo JSON editable (`apps/common/festivos/`), incluido el feriado decretado 2026-07-13. Solo queda pendiente la **tabla** BD (opcional) para decretar en caliente sin redeploy |
| **G2** | Conectividad BD (`192.168.79.10`, negra Nokia, `default`) | Bloquea C1–C4 y T6; R1 principal (lógica sin datos reales) |
| **G3** | Modelo `common.Area` | Centros de costos (B11) y FK de áreas (CR-5) |
| **G4** | D-A9 (outbox móvil) y D-A10 (BD negra) | S2 asignar móvil y T6 |
| **R2** | A2 adelantado a B2 | Cubierto: specs CR-10/D-A11 cerradas; sin rework detectado |
| **R5** | Divergencia con legacy | Mitigado con mensajes/reglas citados; legacy intocado |
| **Hallazgo C4** | La query CR-2 legacy comparaba columna `movil_sale` contra cédula pudiendo contener nombres (comentario del propio PHP) | El backend aplica CR-2 sobre la FK `conductor` resuelta; verificar comportamiento con datos reales en C4 |
| **Hallazgo F5-3** | No existía `DEFAULT_PAGINATION_CLASS` en `settings.py`, así que `get_paginated_response` revienta con `AssertionError` → **HTTP 500** en los endpoints que paginan (`GET /salidas/` B1/B4 e `/informes/mensual/`). Latente: los tests de B1 iban a nivel servicio, no por HTTP | **Corregido** en F5-3: `views/paginacion.py` (`PaginacionTransporte`, page_size 50 / `?page_size=` / máx 1000) aplicado a `SalidaViewSet` e `InformeViewSet` |
| **Pendientes de negocio** | Decisiones abiertas del consolidado **§8 (P1–P5)**, no del `PLAN_TECNICO` (que es spec cerrada) | **P1** **CERRADO (19-oct)**: `planilla_salida.php` verificado y formato F-104 implementado en `POST /planillas/formato/`; siguen sin adjuntarse `controller_cinco.php` y `transporte_salida_datos(_fix).php`, hoy solo útiles como contraste en C3 (no gatean F5 ni F3); **P2/D-A1** motor MySQL vs PG (adoptado MySQL, falta cierre formal); **P3/D-A9** fuente de verdad de `asignar_movil` (bloquea S2); **P4** ventana de novedades tras cierre mensual y `fecha_egreso` al inactivar (P4a toca B4); **P5** auditoría de duplicados (bloquea F6). Detalle en consolidado §8 |
| **F0 · `ValidacionSalida.datos`** | JSON cuya forma definitiva pospuse a F0 (documentado en `validacion_service.py`) | Se persiste **tal cual** hasta F0; no bloquea B4 |

---

## 8. Próximos pasos (orden del ROADMAP §3)

> **E1 y E3 ya cerrados y el calendario compartido (`apps/common/festivos/`)
> quedó reutilizable.** Ya no queda código de backend sin gates: lo
> único que falta está bloqueado por decisión de negocio (G3), acceso
> a BD (G2) o decisión técnica (G4).

1. **B1 (resto) · tabla `common.Festivo`** — *opcional y de confort*: hoy el
   calendario resuelve con algoritmo ∪ catálogo JSON, que se edita y se
   commitea sin tocar Python. La tabla BD solo aporta decretar un festivo
   en caliente sin redeploy → `es_festivo = algoritmo ∪ catálogo ∪ BD`.
   *(B2, B3 y B4 ya cerrados; B1 de facto operativo.)*
2. **Refinamiento B3 #2 (diferido)**: ventana de días anteriores con
   excepción en `programacion_parametros` (el legacy guarda
   `{cedula, fecha_permitida}`; hoy el backend rechaza toda fecha pasada).
   Requiere **decisión de diseño**: storage propio + CRUD con permiso
   `puede_programar` + ETL de las excepciones existentes.
   *El #1 (match OT-específica `validar_agenda_ot`) CERRÓ el 20-oct.*
3. **G2 → Tramo C**: C1 migrate real (incluye migración 0006 de permisos) ·
   C2 auditorías y constraints (CR-3/CR-1/CR-2/D-A12) · C3 ETL con
   conciliación = 0 (DoD 201.000) · C4 validación con datos reales.
4. **Tramo D**: cutover único D1 (rollback < 2 min, PHP como respaldo)
   → D2 estabilización e informe final.

*(G3 → B11 centros de costos; G4 → S2 asignar móvil y T6 teléfonos.)*

---

## Anexo A — Registro de avance (§6 del ROADMAP)

| Fecha | Hito | Commit |
|---|---|---|
| 2026-10-14 | F0/F1-base: modelos, config, migración inicial | `313ec7a` |
| 2026-10-14 | F2 conductores completo | `ca7f522` |
| 2026-10-14 | F2 flota completo (semáforo, documentos) | `8eaa38a` |
| 2026-10-14 | Fix tests MEDIA_ROOT temporal | `f88221c` |
| 2026-10-14 | Import CSV bancarios (CR-13) | `5fd3583` |
| 2026-10-14 | QR bajo demanda (D-A8) | `c97b9bb` |
| 2026-10-14 | ROADMAP: tramos, gates y orden pendiente | `35f2186` |
| 2026-10-14 | A1 parámetros completo: cierres + jefes (87 tests) | `58889b8` |
| 2026-10-14 | A2 núcleo liquidaciones: CR-10, consecutivos, gate (105 tests) | `7a4d89c` |
| 2026-10-14 | A3 esqueleto ETL (126 tests) — **Tramo A completo** | `3c8a457` |
| 2026-10-15 | Calendario de festivos portado del frontend (CR-9 desbloqueada) | `59c80dd` |
| 2026-10-15 | B2 núcleo de salidas: CR-9/CR-1/CR-2, D-A11, /salidas/ + /kiosco (162 tests) | `cffd8f8` |
| 2026-10-15 | B4 backoffice F4: novedades, historial, perfil gestión, /validaciones/ (182 tests) | `a652fc0` |
| 2026-10-15 | B3 reporte fotográfico (núcleo): ventana/agenda en servidor, imágenes Pillow, /reportes-fotograficos/ (214 tests) | `d510271` |
| 2026-10-15 | Kiosco S3/S4: pre-chequeo /kiosco/validar/ y consulta /kiosco/vehiculo/{placa}/ (225 tests) | `bac53fe` |
| 2026-10-15 | F5-1 cuenta de cobro: /informes/cuenta-cobro/ HTML imprimible con importe/pagador en servidor (238 tests) | `ec9b2db` |
| 2026-10-15 | F5-2 gráfico por área: /informes/series-chart/ con año como filtro (corrige hardcode 2024) (246 tests) | `eb2656f` |
| 2026-10-15 | F5-3 informe mensual: /informes/mensual/ + /areas/ con filtros server-side; fix paginación (500 latente en GET /salidas/) (255 tests) | `7f0f362` |
| 2026-10-15 | F5-4 export server-side: /salidas/export/?formato=xlsx|csv, 13 columnas, mismos filtros B1 (260 tests) | `3013df2` |
| 2026-10-19 | F5-5 WFM + F5-6 planillas: cola+lote WFM con worker y planilla oficial con consecutivo y QR (330 tests) | `6c2e10c` |
| 2026-10-19 | Hallazgos de calidad: permisos de modelo en /planillas/, tecnico_cedula real, filtro duro MOTO, worker `wfm_worker`, `.venv` raíz eliminado (339 tests) | `33e8d7e` |
| 2026-10-19 | F5-7 agregados de sábana: /informes/dia, /area, /areas-mes, /nomina y /liquidacion server-side (351 tests) | `c39ee9a` |
| 2026-10-19 | Revisión de cambios subidos: registro real de `/validaciones/` (desde B4 devolvía 404), `serializer_class` en cierres/jefes (500 latente), fix clave duplicada `tipo_vinculacion` en ETL, paginación canónica en 6 listados, inline bancarios en admin (353 tests) | `91615d4` |
| 2026-10-19 | Refactor F5-7 (mejora sobre el legacy): claves de estado reales (`reportado`/`total`), RENTING separado de PROPIO, importes en `Decimal` (355 tests) | `76c140f` |
| 2026-10-19 | E1 catálogo operativo + E3 PermisoService (cierra CR-8): `/vehiculos/catalogo-operativo/` (solo activos, semáforo en servidor) y `/permisos/estado/` (grupos/permisos en vez de cédulas, migración 0006) (365 tests) | `65c2709` |
| 2026-10-19 | Calendario reutilizable (G1 parcial): `apps/common/festivos/` con el algoritmo + catálogo editable `festivos_colombia.json` (2022–2030); `es_festivo` = algoritmo ∪ catálogo (agregar festivo = editar JSON, sin código ni migración); shim en transporte (sin cambio de comportamiento); corrección del JSON de origen: San Pedro y San Pablo 2027 del lunes anterior al correcto 2027-07-05; +10 tests en `apps.common` (377 tests) | `6f3e837` |
| 2026-10-19 | **P1 CERRADO**: formato físico F-104 en `POST /planillas/formato/`, verificado contra `planilla_salida.php` (LETTER horizontal, una hoja por vehículo, QR embebido en base64, casillas en blanco para firmas de salida/retorno). Mejoras sobre el legacy: fecha real (imprimía "16/02/2022" fijo), CONDUCTOR/TELÉFONO/VALOR DÍA reales (la consulta del legacy estaba comentada y salían vacíos), CONSECUTIVO impreso (§3.6) y sin código de barras (D-A8 lo eliminó); F5 al 100 %. +12 tests (389 tests) | `7e00e26` |
| 2026-10-20 | **Refinamiento B3 #1 CERRADO**: match OT-específica `validar_agenda_ot` (port de `validarOtActividadTransporte` + `validarOtActividadAgendaTransporte`, controlador_fix 319–360/175–244): la OT declarada debe coincidir exactamente (mayúsculas + espacios colapsados) con `actividad.ot`, `tipo_trabajo`, `descripcion` u `observacion` de una agenda no borrada del día; se aplica en `guardar()` y en el pre-chequeo `validar-agenda/`; áreas exentas y WFM/IM intactas y sin OT declarada no se endurece el gate ya cerrado. Queda el #2 (ventana de días anteriores con excepción). +16 tests (405 tests) | *(este commit)* |
| 2026-10-21 | **A1 ficha de contacto del conductor CERRADA** (última acción de `base_transportadores.php` que faltaba): `GET /vehiculos/{id}/contacto/` + `ContactoService`, que cruza las 3 fuentes del legacy — línea corporativa (Nokia, BD negra), celular de `transporte_base_conductores` y los 3 teléfonos de `cinco_base_de_personal`. Cross-BD sin JOIN (D-A10) y con degradación explícita de la fuente Nokia (`nokia_disponible=false`) mientras no haya gate G2: la ficha se entrega igual con las 2 fuentes de `azul`, en vez de un 500. Mejora sobre el legacy: `linea_corporativa` es lista, no la cadena `300111,300222` del `group_concat`. +10 tests |
| 2026-10-21 | **Huecos del legacy recuperados en flota** (al auditar `base_transportadores.php` contra `DICCIONARIO_DATOS.md`): `cilindraje` (varchar 11, "numérico como texto") vuelve al `Vehiculo`; `licencia` (SI/NO/NO APLICA → `posee_licencia`), `estado_licencia` (ACTIVA/INACTIVA → `situacion_licencia`), `categoria` (A1..C3) y `fecha_licencia` vuelven al `Conductor` (de quien son) — era un hueco real: el docstring decía "pertenecen al conductor" pero nunca se habían añadido. **Fix de pérdida de datos:** `CategoriaLicencia` solo tenía 4 de las 8 categorías del legacy, por lo que la ETL convertía a NULL las licencias A1/A2/B2/B3 → catálogo ampliado a 8. La ETL enriquece al conductor con la copia del vehículo **solo en campos vacíos** (resultado independiente del orden de carga). El semáforo `estado_licencia` (VIGENTE/POR_VENCER/VENCIDA) NO se toca: el flag manual del legacy va en `situacion_licencia` para que no choquen. Migración 0007 (3 AddField nullable + AlterField de choices), sin migración de datos; `migrate` contra la BD real **no ejecutado**. +13 tests (428 tests, 0 rojos). |
