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
- **225 tests OK**, `manage.py check` sin issues, DoD
  cumplido en cada hito (tests verdes → check → commit local).
- **Cero ejecución contra MySQL real** (G2 sin conectividad); los tests
  corren en SQLite aislado (`config.settings_test_transporte`).
- **PHP legacy intacto**: hasta el cutover único (D1) el sistema
  actual sigue vivo; el backend nuevo aún no escribe en BD de producción.
- Únicos insumos externos que faltan del negocio/infra: **G1**
  (decisión del calendario `common.Festivo`) y **G2** (conectividad BD).

### Estado por fase

| Fase | Contenido | Avance |
|---|---|---|
| F0 Diccionario y mapeo FKs | Mapeo aplicado en los modelos | ~90% (auditorías CR-3 → C2) |
| F1 Base Django y Festivos | 16 modelos + migración; algoritmo de festivos portado; falta tabla `common.Festivo` | ~70% (→ G1 / C1) |
| F2 Flota y Conductores | CRUD + semáforo + documentos + CSV (CR-13) + QR (D-A8) | ~90% (falta T6 → C3) |
| F3 Kiosco y Fotos | Núcleo cerrado (B2): alta S6, consulta B1, escaneo S1; fotos y S2–S4 pendientes | ~35% |
| F4 Backoffice y Novedades | Modelos listos; servicio de estados listo (B2), faltan endpoints | 0% |
| F5 Liquidaciones e Informes | Núcleo cerrado (A2); planillas/informes pendientes | ~50% |
| F6 ETL histórico | Esqueleto cerrado (A3); corrida real → C3 | ~40% |
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
| **Calendario (B1 interino)** | `59c80dd` | Port de `festivosColombia.ts` → `services/calendario.py`: 18 festivos Ley 51/1983 (Emiliani + Pascua Butcher/Meeus), `sabado_habil` configurable (default hábil = frontend; CR-9 pasa `False` por paridad legacy), caché por año |
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
| CR-8 | Reemplazar cédulas hardcodeadas por permisos | ⬜ → E3/§5.9 (permisos ya referenciados en código) |
| CR-9 | Ventana −2 días hábiles + bypass por rol | ✅ `calendario` + `SalidaService.ventana_validacion` (con mensajes legacy literales) |
| CR-10 | Sábanas mensual/pronto-pago con estados exactos | ✅ A2 |
| CR-11 | Planillas con exclusión de motos y consecutivo | ⬜ → `PlanillaService` (tras B4) |
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
| §5.2 `LiquidacionService` | sábanas, consecutivos, cerrar_mes | ✅ núcleo (planillas/informes ⬜) |
| §5.3 `FlotaService` | ABM, semáforo, documentos, CSV, QR | ✅ |
| §5.4 `ConductorService` | ABM, licencia, edad derivada | ✅ |
| §5.5 `ReporteFotograficoService` | agenda + horario 10–16 | ⬜ → B3 |
| §5.6 `PlanillaService` (CR-11) | planillas con exclusión de motos | ⬜ |
| §5.7 `InformeService` | sábanas con filtros server-side + export | ⬜ (B1 filtros base ✅) |
| §5.8 `ParametrosService` | cierres + jefes | ✅ A1 |
| §5.9 `PermisoService` | grupos/permisos vs cédulas hardcodeadas | 🟡 referenciado (`has_perm`), declaración → E3 |

---

## 4. Matriz "nada se pierde" (§6 del plan) — estado

| Bloque | Entregado | Pendiente |
|---|---|---|
| **B (gestión)** | B1 filtros `?desde=&hasta=` ✅ · B2 ver cierres ✅ · B8 ficha+semáforo ✅ · B10 valor día/total ✅ (`total_a_pagar`) · B14 badge reportado ✅ · B5/B12/B13 🟡 servicio, falta HTTP (B4) | B3 ruta cierres `{mes}/{anio}/` · B4 export xlsx · B6/B7 novedades · B9 `buscar_movil` (G2/G4) · B11 centros de costos (G3) · B15 permisos por fila |
| **S (kiosco)** | S1 escanear ✅ · S6 grabar salida ✅ | S2 asignar móvil (G4/D-A9) · S3 validar · S4 consulta por placa · S5 planillas |
| **T (flota)** | T1 ficha · T2 fotos/docs · T3 bancarios · T4 CSV · T5 QR ✅ | T6 teléfonos (G2 + D-A9/D-A10) |
| **D (backoffice/tabla3)** | D1 jefes · D2 cierres · D3 liquidaciones · D4 pagos ✅ | — |
| **C/F** | C1 conductores ✅ | F1 reporte fotográfico → B3 |
| **E (reemplazos)** | — | E1 `catalogo-operativo` · E2 helpers JS · E3 `/permisos/estado/` |

---

## 5. Métricas

| Métrica | Valor |
|---|---|
| Tests | **162 OK** (18 clases; evolución 87 → 105 → 126 → 134 → 162) |
| Código Python del módulo | 46 archivos · ~6.700 LOC (1.617 líneas de tests) |
| Cambio acumulado en rama | 56 archivos · +8.057 líneas (incluye config y docs) |
| Modelos Django | 16 (+ `0001_initial`, choices, admin) |
| Endpoints activos | 7 recursos router (`/conductores/`, `/vehiculos/`, `/parametros/cierres/`, `/parametros/jefes/`, `/liquidaciones/`, `/salidas/`, `/kiosco/`) + 11 acciones (`resumen`, `documentos`, `importar-bancarios`, `qr.png`, `inactivar`×2, `pago-mensual`, `pronto-pago`, `consecutivo`, `pago`, `escanear`) |
| Commits del módulo | 18 + este informe (locales, sin push) |
| Ejecuciones contra BD real | **0** |
| Archivos PHP legacy modificados | **0** |

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
| **G1** | Calendario `common.Festivo` (decisión de negocio, compañera) | Solo gatea la **tabla** de festivos decretados (art. 71); el algoritmo ya corre → B2 avanzó sin G1 |
| **G2** | Conectividad BD (`192.168.79.10`, negra Nokia, `default`) | Bloquea C1–C4 y T6; R1 principal (lógica sin datos reales) |
| **G3** | Modelo `common.Area` | Centros de costos (B11) y FK de áreas (CR-5) |
| **G4** | D-A9 (outbox móvil) y D-A10 (BD negra) | S2 asignar móvil y T6 |
| **R2** | A2 adelantado a B2 | Cubierto: specs CR-10/D-A11 cerradas; sin rework detectado |
| **R5** | Divergencia con legacy | Mitigado con mensajes/reglas citados; legacy intocado |
| **Hallazgo C4** | La query CR-2 legacy comparaba columna `movil_sale` contra cédula pudiendo contener nombres (comentario del propio PHP) | El backend aplica CR-2 sobre la FK `conductor` resuelta; verificar comportamiento con datos reales en C4 |
| **Pendientes de negocio** | Decisiones abiertas del consolidado **§8 (P1–P5)**, no del `PLAN_TECNICO` (que es spec cerrada) | **P1** archivos legacy verificados (B3 desbloqueado y cerrado); aún faltan `controller_cinco.php`, `transporte_salida_datos(_fix).php` y `planilla_salida.php` para F5/C3; **P2/D-A1** motor MySQL vs PG (adoptado MySQL, falta cierre formal); **P3/D-A9** fuente de verdad de `asignar_movil` (bloquea S2); **P4** ventana de novedades tras cierre mensual y `fecha_egreso` al inactivar (P4a toca B4); **P5** auditoría de duplicados (bloquea F6). Detalle en consolidado §8 |
| **F0 · `ValidacionSalida.datos`** | JSON cuya forma definitiva pospuse a F0 (documentado en `validacion_service.py`) | Se persiste **tal cual** hasta F0; no bloquea B4 |

---

## 8. Próximos pasos (orden del ROADMAP §3)

1. **B1 (resto) · tabla `common.Festivo`** en cuanto G1 decida fuente y
   modelo → `es_festivo = algoritmo ∪ BD`. *(B2, B3 y B4 ya cerrados sin G1.)*
2. **Refinamientos B3 (diferidos)**: match OT-específica `validar_agenda_ot`
   (→ junto al subsistema WFM/OT, F5) y ventana de días anteriores con
   excepción en `programacion_parametros` (→ decisión ETL de esa tabla).
3. **G2 → Tramo C**: C1 migrate real · C2 auditorías y constraints
   (CR-3/CR-1/CR-2/D-A12) · C3 ETL con conciliación = 0 (DoD 201.000) ·
   C4 validación con datos reales.
4. **Tramo D**: cutover único D1 (rollback < 2 min, PHP como respaldo)
   → D2 estabilización e informe final.

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
| 2026-10-15 | Kiosco S3/S4: pre-chequeo /kiosco/validar/ y consulta /kiosco/vehiculo/{placa}/ (225 tests) | *(este commit)* |
