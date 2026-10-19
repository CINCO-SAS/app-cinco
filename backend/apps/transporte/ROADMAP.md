# Ruta pendiente — Módulo Transporte

> Documento vivo de seguimiento. Los `.md` de `MIGRACIONES/` son la
> **especificación**; éste solo registra **qué falta, en qué orden y qué lo
> desbloquea**. Actualizar la §6 al cerrar cada hito.
> Última actualización: 2026-10-15 · Rama: `feat/modulo_transporte` · Commits locales sin push.

---

## 0. Estado actual (snapshot)

| Fase | Contenido | Avance |
|---|---|---|
| F0 Diccionario y mapeo FKs | Mapeo aplicado en los modelos | ~90% (auditorías CR-3 pendientes → C2) |
| F1 Base Django y Festivos | 16 modelos + migración; **algoritmo de festivos portado + caché** (services/calendario.py); falta la tabla `common.Festivo` | ~70% (solo falta `common.Festivo` → G1; migrate real → C1) |
| F2 Flota y Conductores | CRUD + semáforo + documentos + CSV (CR-13) + QR (D-A8) | ~90% (falta T6 → C3) |
| F3 Kiosco y Fotos | Núcleo **CERRADO** (B2): alta de salidas S6, consulta B1, escaneo S1; **fotos B3 núcleo cerrado** (ventana/agenda/imágenes en servidor); **kiosco S3 (pre-chequeo) y S4 (consulta por placa) cerrados**; pendiente solo S2 (gated G4) y refinamientos B3 | ~70% |
| F4 Backoffice y Novedades | Backoffice **CERRADO** (B4): `aprobar-lote`, `aprobar`, `rechazar`, `validar`, `DELETE`, novedades (B6/B7), historial y `/validaciones/` (cierre por área) | ~60% (falta B11 centros de costos → G3) |
| F5 Liquidaciones e Informes | **F5-1…F5-7 CERRADOS** (cuenta de cobro, gráfico, informe mensual, export, WFM + worker, planillas, agregados de sábana) | ~95% |
| F6 ETL histórico | Esqueleto cerrado (A3); corrida real → C3 | ~40% |
| F7 Cutover | — | 0% |
| F8 Estabilización | — | 0% |

- 339 tests OK (`config.settings_test_transporte`, SQLite aislado de otros módulos).
- **Nada ejecutado contra MySQL real.**

---

## 1. Gates (bloqueadores externos)

| ID | Condición | Desbloquea | Estado / responsable |
|---|---|---|---|
| **G1** | Decisión de negocio: fuente y modelo del calendario de festivos (`common.Festivo`) | B1 (F3); **B2, B3 y B4 cerrados sin G1** con el algoritmo portado | Pospuesto por el negocio |
| **G2** | Conectividad: BD `azul` (`192.168.79.10`), BD negra Nokia y `default` | C1–C4, T6 teléfonos | Sin acceso desde esta máquina |
| **G3** | Modelo `common.Area` (viene de otro PHP) | FK de áreas en parámetros/backoffice | Pendiente de fuente |
| **G4** | Decisiones **D-A9** (asignar móvil vía outbox asíncrono) y **D-A10** (router BD negra) — §8 | S2 asignar móvil, T6 | Pendientes de decisión técnica |

---

## 2. Tramos

### Tramo A — sin bloqueos (ejecutable hoy)

- [x] **A1 · Parámetros (§5.8)** — ✅ **CERRADO** (`58889b8`, 87 tests).
      CRUD `FechaLimiteCierre` (cierres, unicidad (mes, anio)) y
      `JefeValidador` (áreas/carpetas como JSON → **no exige G3**).
      Endpoints canónicos `/parametros/cierres/` (absorbe B2) y
      `/parametros/jefes/` (D1) + `POST {id}/inactivar/`.
      > **Empleado (managed=False, cross-DB) resuelto:** resolución en dos
      > pasos (cédula→id, luego filtro local `empleado_id`; **cero JOINs**,
      > D-A10) + tabla de prueba creada con `schema_editor` únicamente en
      > tests de transporte. Escrituras con `DjangoModelPermissions`
      > (gate `$permi_editar`; permiso granular `editar_tras_cierre` → E3).
- [x] **A2 · Núcleo de liquidaciones F5 con fixtures** — ✅ **CERRADO**
      (`7a4d89c`, 105 tests). `LiquidacionService`: sábanas CR-10
      (pago mensual APROBADO+REPORTADO+VALIDADO vs pronto pago **solo
      APROBADO**) con retroceso de 6 meses solo si el pedido es el mes en
      curso (legacy 331–348/411–428), `proximo_consecutivo` atómico
      (`select_for_update` + unique, arranque 1000 = MAX global como el
      legacy), `puede_editar_periodo` (gate `editar_tras_cierre`) y upsert
      de `PagoVehiculoMensual` con `total_liquidado` autocalculado (§5.1).
      Endpoints: `GET /liquidaciones/?mes=&anio=` (D3; la ruta compuesta
      `/{anio}/{mes}/` queda como query param — DefaultRouter reserva
      `/{pk}/`), `GET .../pago-mensual|pronto-pago/` (D4),
      `POST .../consecutivo|pago/`. Matemática de períodos extraída a
      `services/periodos.py` (fuente única con cierres). *Pendiente de A2:
      ruta compuesta B3 `/cierres/{mes}/{anio}/`; planilla/informes van
      tras B2.*
- [x] **A3 · Esqueleto del comando ETL con fixtures locales** — CERRADO.
      `apps/transporte/etl/` (normalizadores D-A4/D-A6, convertidores puros
      §7.2, carga con FKs por cédula/placa + lotes + conciliación) y
      `manage.py migrate_transporte_legacy` (`--fuente/--lote/--dry-run`);
      muestras en `etl/muestras/`. La validación real recién en C3 (G2).
      *Hallazgo: la conciliación usa `convertidas` (no creadas): una fila
      que convierte pero falla al cargar descuadra y el comando sale con
      estado 1 — intencional, el cutover no avanza con datos perdidos.*

> T6 (teléfonos/`buscar_movil`) **no** es Tramo A: encadena tres BD (G2) y arrastra D-A9/D-A10 (G4).

### Tramo B — requiere G1 (festivos)

- [ ] **B1 · F1-resto: festivos** — modelo/precarga del calendario + caché en memoria
      + tests de la regla de −2 días hábiles (CR-9). *Tamaño M · Es gate de todo el tramo.*
      **Avance (14-oct):** el ALGORITMO ya está portado al backend en
      `services/calendario.py` (18 festivos estatutarios Ley 51/1983 +
      Pascua Butcher/Meeus, port de `frontend/src/utils/festivos/festivosColombia.ts`,
      sábado configurable con default hábil como el original). G1 ahora solo
      gatea la TABLA `common.Festivo` (festivos decretados art. 71 + fuente
      compartida de otras áreas): al llegar, `es_festivo` = algoritmo ∪ BD.
      **Paridad verificada:** el legacy CR-9 excluía sábados
      (`base_salida_transporte.php` 77–96) → la ventana usará
      `sabado_habil=False` explícito.
- [x] **B2 · F3 núcleo: registro de salidas** — ✅ **CERRADO** (`cffd8f8`, 162 tests).
      `SalidaService`: ventana CR-9 con `calendario` (−2 días hábiles,
      sábados NO hábiles; bypass programación/admin y jefe del área,
      mensajes legacy literales), anticolisión CR-1 `(vehículo, fecha)` y
      CR-2 `(conductor, fecha)` excluyendo `ELIMINADO` (liberados por
      borrado lógico), snapshots `area/carpeta/sede/valor_dia`,
      exigencia estricta de personal / área manual en "disponible",
      máquina de estados `REPORTADO → APROBADO/RECHAZADO/ELIMINADO` y
      `APROBADO → VALIDADO` (D-A11; `RECHAZADO` terminal) con
      `SalidaHistorial` por fila + `AuditoriaLog`. Endpoints:
      `GET/POST /salidas/`, `GET /salidas/{id}/` (S6/B1) y
      `POST /kiosco/escanear/` (S1: QR D-A8 → placa + salida del día).
      Las transiciones vía HTTP (aprobar-lote/rechazar/validar/DELETE) y
      las novedades quedan para B4 — el servicio ya lo soporta.
- [x] **B3 · F3 reporte fotográfico (núcleo)** — ✅ ventana 10:00–16:00 y gate de
      agenda (`operaciones_agenda`, **solo lectura de módulo ajeno**) validados
      EN SERVIDOR; exención de área (`transporteOmiteValidacionOt`); 1–5 imágenes
      con compresión Pillow; dedup `(vehículo, fecha, técnico)`; identidad desde
      `request.user` (no del cliente). Endpoints: `POST /reportes-fotograficos/`,
      `POST .../validar-agenda/`, `GET .../vehiculo-placa/`. **Núcleo CERRADO**
      (214 tests). *Pendiente (diferido):* match OT-específica `validar_agenda_ot`
      (→ con WFM/OT, F5) y ventana de días anteriores con excepción en
      `programacion_parametros` (→ decisión ETL).
- [x] **B4 · F4 backoffice** — aprobación masiva, rechazo con motivo, eliminación
      lógica, novedades, historial (`SalidaHistorial`) y validación de jefes
      (`ValidacionSalida`, con datos de A1). *Tamaño M.* **CERRADO** (182 tests).

### Tramo C — requiere G2 (conectividad)

- [ ] **C1 · Migrate real** — `0001_initial` en `default` (`db_cincosas`), verificar `utf8mb4`.
- [ ] **C2 · Auditorías §7.1** — CR-3 (placas duplicadas), CR-1/CR-2 (duplicados previos)
      → columna virtual `STORED` + constraints únicos parciales de `Salida`.
- [ ] **C3 · F6 ETL** — `manage.py migrate_transporte_legacy`: lotes de 2.000,
      desempaquetado del JSON `datos`, resolución de FKs (`ID Foreign Keys`),
      **jefes** (`programacion_parametros`), **fechas límite**, **festivos** (si su
      fuente es PHP) y **T6 teléfonos** (cascada azul→negra).
      *DoD: 201.000 registros con conciliación = 0.*
- [ ] **C4 · Validación contra datos reales** — semáforos SOAT/CDA, upserts de
      bancarios y QR sobre datos de producción (solo lectura).

### Tramo D — cierre

- [ ] **D1 · F7 cutover único** — dry-run en pruebas, ventana de congelación de
      escrituras legacy, sincronización final, pase de puntero `ConfigMenu`
      (rollback < 2 min) y E2E completo. *PHP intacto como respaldo.*
- [ ] **D2 · F8 estabilización** — índices/monitoreo en MySQL, archivo del PHP
      legacy, informe final del proyecto.

### F5 — desglose en curso (Tab 2 informes + planillas)

Núcleo de liquidaciones **CERRADO** en A2 (D3/D4, CR-10, consecutivos). El
resto de F5, troceado de menor a mayor (1 hito = 1 commit). WFM y cuenta de
cobro no tienen fila propia en la matriz §6: viven dentro de la sábana (I1).

- [x] **F5-1 · Cuenta de cobro** — ✅ `GET /informes/cuenta-cobro/?placa=&mes=&anio=`
      devuelve HTML imprimible (legacy `cuenta_cobro_plantilla.php`).
      **Mejora de integridad:** el legacy imprimía `pagar`/`banco`/`cuenta`/
      `nombre` desde campos ocultos del formulario (importe alterable desde
      el navegador); aquí el importe se calcula en SERVIDOR
      (`valor_base = Σ total_a_pagar`; retefuente 1 %; `pagar = base − rete`)
      y el pagador se lee de `DatosBancariosVehiculo` (fallback: propietario).
      Consecutivo tomado de `ConsecutivoMensual` si existe. *Tamaño S.*
- [x] **F5-2 · Gráfico mensual por área** — ✅ `GET /informes/series-chart/?anio=`
      devuelve `{"series": ...}` para el gráfico "Pagos por Mes, por Área"
      (suma de `total_a_pagar` por (área, mes); I&M al eje secundario a2 con
      su estilo). **Corrección del bug legacy:** el PHP recibía `mes`/`yyyy`
      y hacía `execute([2024])` — fijaba 2024 a mano e ignoraba ambos; el año
      ahora es un filtro opcional **respetado** (sin año: histórico completo).
      Estados como el legacy post-01/08/2024 (VALIDADO + APROBADO).
      *Tamaño S.*
- [x] **F5-3 · Informe mensual + filtros** — ✅ `GET /informes/mensual/?mes=&anio=&estado=&sede=&area=&carpeta=&search=`
      (§5.7 `InformeService.mensual`): salidas **no eliminadas** del mes,
      filtros server-side, orden **día a día** (ascendente), paginado, con
      `SalidaSerializer` (placa, área, valor día, novedad, `total_a_pagar`,
      `puede_gestionar` B15). + `GET /informes/areas/?mes=&anio=` (áreas del
      periodo → `arr_areas` de la sábana). Rango de mes **semiabierto**
      `[desde, hasta)` como `LiquidacionService` (no `__range`, que incluye
      el día 1 del mes siguiente). *Tamaño M.*
      **Hallazgo (corregido):** no existía `DEFAULT_PAGINATION_CLASS` en el
      proyecto, así que `get_paginated_response` daba **HTTP 500** en
      `GET /salidas/` (B1/B4) — latente porque los tests iban a nivel
      servicio. Creado `views/paginacion.py` (`PaginacionTransporte`) y
      aplicado a `SalidaViewSet` e `InformeViewSet`.
- [x] **F5-4 · Export server-side CERRADO** — fila B4: `GET /salidas/export/?formato=xlsx|csv`
      (migrado de client-side DataTables a server-side). Reutiliza
      `SalidaService.listar` (mismos filtros B1) + `InformeService.exportar`
      (13 columnas de la sábana, números reales en XLSX; CSV `;` + BOM
      utf-8 para Excel español). `openpyxl==3.1.5` declarado en
      `requirements.txt`.
      ⚠️ El parámetro se llama `formato`, **no** `format`: DRF reserva
      `format` para su content negotiation (`?format=`) y lo convertía en
      **404**.
- [x] **F5-5 · WFM** — ✅ **CERRADO** (330 tests). `WfmService` (§5.10): ventana
      de 2 días hábiles, elegibilidad WFM primaria + agenda como respaldo
      (hallazgo: los mapas "completado"/"any" del legacy eran idénticos),
      lote síncrono con `select_for_update` (el UPDATE a ciegas del
      legacy permitía carreras) y cola de jobs idempotente por chunk
      (`chunkDays=1`). Transición `REPORTADO → VALIDADO` incorporada a
      `TRANSICIONES` (D-A11 extendido con evidencia legacy 426–445).
      Endpoints: `POST /wfm/validar/`, `/wfm/crear-job/`, `/wfm/estado-job/`
      (con respaldo síncrono). **Worker**: `manage.py wfm_worker`
      (port de `transporte_validacion_wfm_worker.php`: `reclamar_siguiente`
      con precedencia PROCESANDO-huérfano, 1 chunk por defecto,
      `--hasta-completar` / `--job <uuid>`; cron sugerido cada 5 min).
- [x] **F5-6 · Planillas** — ✅ **CERRADO** (330 tests). `POST /planillas/generar/`
      (S5, CR-11): alcances PLACA/PROPIO/EXTERNO/RENTING/TODAS,
      **filtro duro `tipo != 'MOTO'` explícito en todos los alcances**
      (legacy `transporte_salida.php` 597/608/663; los choices no bastan
      contra datos legacy de la ETL), consecutivo atómico por vehículo y
      QR en disco. Permisos: exige `add_consecutivomensual` (generar
      planilla ESCRIBE consecutivos). *Pendiente menor (P1): el formato
      físico definitivo requiere `planilla_salida.php` verificado.*
- [x] **F5-7 · Agregados de sábana** — ✅ **CERRADO** (351 tests). Agregaciones
      server-side del JS de la sábana (`transporte_salida_informes.php`):
      `GET /informes/dia/?fecha=` (día → área → carpetas con `arr_estado`),
      `GET /informes/area/?mes=&anio=&solo_aprobados=` (totales del mes,
      interruptor "solo aprobados" = APROBADO/VALIDADO),
      `GET /informes/areas-mes/?anio=` (matriz área × meses),
      `GET /informes/nomina/?mes=&anio=` ((carpeta, placa), rete 1 %,
      pagador en servidor CR-13; **`centro_costo` vacío hasta G3/B11** —
      el legacy lo tomaba de `map_carpetas` en JS) y
      `GET /informes/liquidacion/?mes=&anio=` (por placa, rete 1 %,
      consecutivo). Fidelidad: `pendiente` = REPORTADO, EXTERNO es el
      único "externo" (PROPIO/RENTING son propios), importes en pesos
      enteros (`parseInt`), REPORTADO/ELIMINADO excluidos en nómina y
      liquidación. *El "pronto pago" ya existía en A2 (`/liquidaciones/pronto-pago/`).*

---

## 3. Orden recomendado

```
   HOY (sin gates)              G1 (festivos)                G2 (BD)                 CIERRE
 ┌─────────────────┐         ┌────────────────────┐      ┌──────────────────┐    ┌──────────┐
 │ A1 Parámetros   │         │ B1 festivos (gate) │      │ C1 migrate real  │    │ D1 F7    │
 │ A2 núcleo F5    │ ──────► │ B2 salidas (corazón)│ ───►│ C2 auditorías    │ ─► │ D2 F8    │
 │ A3 esqueleto ETL│         │ B3 fotos  B4 backof.│      │ C3 ETL  C4 real  │    └──────────┘
 └─────────────────┘         └────────────────────┘      └──────────────────┘
                                    ▲
        C1/C2 pueden adelantarse en cuanto se resuelva G2 (paralelo al Tramo A/B).
```

**Recomendación:** atacar A1 → A2 ahora; preparar G1 (decisión de festivos) como
siguiente hito de negocio, porque de él cuelga el 40% del sistema (F3+F4).

---

## 4. Riesgos

| ID | Riesgo | Mitigación |
|---|---|---|
| R1 | Lógica escrita sin datos reales (G2 cerrado) | Fixtures desde specs + ejecución temprana de C1 apenas haya conectividad |
| R2 | A2 (F5) adelantado a B2 (F3) → posible rework | Specs CR-10/D-A11 cerradas; mover A2 tras B2 si se prefiere orden estricto |
| R3 | Dependencia de módulos ajenos (`operaciones_agenda`, `cinco_base_de_personal`, Nokia) | **Solo lectura**; nunca editar otros módulos (regla del proyecto) |
| R4 | Regresión en otros módulos | Tests aislados (`settings_test_transporte`) + `manage.py check` en cada hito |
| R5 | Divergencia con el PHP legacy | Legacy intocado; cualquier cambio de regla es decisión de negocio documentada |

---

## 5. DoD estándar de cada hito

1. Tests en verde: `backend\.venv\Scripts\python.exe backend\manage.py test apps.transporte --settings=config.settings_test_transporte`
   *(el venv canónico es `backend/.venv` — `backend/README.md`; el `.venv` de la raíz se eliminó el 19-oct por estar roto: apuntaba a un Python 3.14 inexistente)*
2. `backend\.venv\Scripts\python.exe backend\manage.py check` sin issues
3. Commit local (**sin push**)
4. Marcar el hito en la §6 y actualizar la fecha de este documento

---

## 6. Registro de avance

| Fecha | Hito | Commit |
|---|---|---|
| 2026-10-14 | F0/F1-base: modelos, config, migración inicial | `313ec7a` |
| 2026-10-14 | F2 conductores completo | `ca7f522` |
| 2026-10-14 | F2 flota completo (semáforo, documentos) | `8eaa38a` |
| 2026-10-14 | Fix tests MEDIA_ROOT temporal | `f88221c` |
| 2026-10-14 | Import CSV bancarios (CR-13) | `5fd3583` |
| 2026-10-14 | QR bajo demanda (D-A8) + dependencias | `c97b9bb` |
| 2026-10-14 | ROADMAP: tramos, gates y orden pendiente | `35f2186` |
| 2026-10-14 | A1 parámetros completo: cierres + jefes (87 tests) | `58889b8` |
| 2026-10-14 | A2 núcleo liquidaciones: CR-10, consecutivos, gate (105 tests) | `7a4d89c` |
| 2026-10-14 | A3 esqueleto ETL: comando + muestras + conciliación (126 tests) — **Tramo A completo** | `3c8a457` |
| 2026-10-15 | Calendario de festivos portado del frontend (18 festivos, CR-9 desbloqueada) | `59c80dd` |
| 2026-10-15 | B2 núcleo de salidas: CR-9/CR-1/CR-2, D-A11, /salidas/ + /kiosco (162 tests) | `cffd8f8` |
| 2026-10-15 | B4 backoffice F4: novedades, historial, perfil gestión, /validaciones/ (182 tests) | `a652fc0` |
| 2026-10-15 | B3 reporte fotográfico (núcleo): ventana/agenda en servidor, imágenes Pillow, /reportes-fotograficos/ (214 tests) | `d510271` |
| 2026-10-15 | Kiosco S3/S4: pre-chequeo /kiosco/validar/ (CR-9/CR-1/CR-2) y consulta /kiosco/vehiculo/{placa}/ (225 tests) | `bac53fe` |
| 2026-10-15 | F5-1 cuenta de cobro: /informes/cuenta-cobro/ HTML imprimible, importe y pagador en servidor (238 tests) | `ec9b2db` |
| 2026-10-15 | F5-2 gráfico por área: /informes/series-chart/ corrige el hardcode 2024 del legacy; año como filtro (246 tests) | `eb2656f` |
| 2026-10-15 | F5-3 informe mensual: /informes/mensual/ + /areas/ con filtros server-side; fix paginación (500 latente en /salidas/) (255 tests) | `7f0f362` |
| 2026-10-15 | F5-4 export server-side: /salidas/export/?formato=xlsx|csv, 13 columnas, mismos filtros B1 (260 tests) | `3013df2` |
| 2026-10-19 | F5-5 WFM + F5-6 planillas: cola+lote WFM con worker y planilla oficial con consecutivo y QR (330 tests) | `6c2e10c` |
| 2026-10-19 | Hallazgos de calidad: permisos de modelo en /planillas/, tecnico_cedula real, filtro duro MOTO (CR-11), worker `wfm_worker`, .venv raíz roto eliminado (339 tests) | `33e8d7e` |
| 2026-10-19 | F5-7 agregados de sábana: /informes/dia, /area, /areas-mes, /nomina y /liquidacion server-side (351 tests) | *(este commit)* |
