# Ruta pendiente — Módulo Transporte

> Documento vivo de seguimiento. Los `.md` de `MIGRACIONES/` son la
> **especificación**; éste solo registra **qué falta, en qué orden y qué lo
> desbloquea**. Actualizar la §6 al cerrar cada hito.
> Última actualización: 2026-10-14 · Rama: `feat/modulo_transporte` · Commits locales sin push.

---

## 0. Estado actual (snapshot)

| Fase | Contenido | Avance |
|---|---|---|
| F0 Diccionario y mapeo FKs | Mapeo aplicado en los modelos | ~90% (auditorías CR-3 pendientes → C2) |
| F1 Base Django y Festivos | 16 modelos + migración generada; **festivos no** | ~50% (festivos → B1; migrate real → C1) |
| F2 Flota y Conductores | CRUD + semáforo + documentos + CSV (CR-13) + QR (D-A8) | ~90% (falta T6 → C3) |
| F3 Kiosco y Fotos | — | 0% |
| F4 Backoffice y Novedades | Modelos listos | 0% |
| F5 Liquidaciones e Informes | Modelos listos | 0% (núcleo → A2) |
| F6 ETL histórico | — | 0% |
| F7 Cutover | — | 0% |
| F8 Estabilización | — | 0% |

- 50 tests OK (`config.settings_test_transporte`, SQLite aislado de otros módulos).
- **Nada ejecutado contra MySQL real.**

---

## 1. Gates (bloqueadores externos)

| ID | Condición | Desbloquea | Estado / responsable |
|---|---|---|---|
| **G1** | Decisión de negocio: fuente y modelo del calendario de festivos (`common.Festivo`) | B1 → B2 → B3 → B4 (F3 y F4 completas) | Pospuesto por el negocio |
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
- [ ] **B2 · F3 núcleo: registro de salidas** — `SalidaService`:
      ventana CR-9, anticolisión CR-1 `(vehículo, fecha)` y CR-2 `(conductor, fecha)`
      excluyendo `ELIMINADO`, snapshots de datos en la salida, máquina de estados
      `REPORTADO → APROBADO/RECHAZADO/ELIMINADO` y `APROBADO → VALIDADO` (D-A11),
      endpoints `/salidas/` + `POST /kiosco/escanear/` (S1). *Tamaño L · El corazón transaccional.*
- [ ] **B3 · F3 reporte fotográfico** — validación de agenda (`operaciones_agenda`,
      **solo lectura de módulo ajeno**) y ventana 10:00–16:00. *Tamaño M.*
- [ ] **B4 · F4 backoffice** — aprobación masiva, rechazo con motivo, eliminación
      lógica, novedades, historial (`SalidaHistorial`) y validación de jefes
      (`ValidacionSalida`, con datos de A1). *Tamaño M.*

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

1. Tests en verde: `python backend/manage.py test apps.transporte --settings=config.settings_test_transporte`
2. `python backend/manage.py check` sin issues
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
