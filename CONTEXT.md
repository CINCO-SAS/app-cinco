# app-cinco

Sistema interno que cubre operaciones de campo, recursos humanos, programación y
un área de inteligencia artificial. Sirve de registro y soporte para el trabajo
que la empresa ejecuta y documenta.

> **Uso de este archivo:** es un glosario, nada más. Se lee al empezar una sesión
> para alinear el vocabulario. No lleva decisiones de diseño ni detalles de
> implementación — esas van en ADRs.

## Language

### El sistema

**Módulo**:
Bloque funcional del sistema con sus pantallas, datos y reglas propios. Ejemplos
reales: Operaciones, RRHH, Programación. Es la unidad en la que se entrega trabajo
nuevo y la que reutiliza lo ya construido.
_Avoid_: pantalla, sección, app, componente

### Organización

**SMU**:
El área de la empresa a la que pertenece este trabajo. Es una unidad organizativa,
no un módulo ni una tecnología. Lo que esa área levanta en sitio se llama
Actividad SMU.
_Avoid_: módulo SMU, sistema SMU, servicio SMU

**Área**:
Unidad organizativa que agrupa personas y su trabajo. Ejemplos reales en el
sistema: Soporte Técnico.
_Avoid_: departamento, equipo, zona

**Responsable**:
La persona que queda a cargo de una actividad.
_Avoid_: asignado, encargado, owner

**Empresa aliada**:
Empresa externa contratista que ejecuta una actividad en lugar de personal propio.
_Avoid_: contratista, tercero, proveedor

**Técnico**:
Persona que ejecuta el trabajo en sitio y deja constancia de lo hecho.
_Avoid_: operario, gestor

### Trabajo operacional

**Actividad**:
La unidad de trabajo registrada en operaciones. Es el objeto central del módulo.
No confundir con Actividad SMU: son dos registros distintos con dos ciclos distintos.
_Avoid_: tarea, registro, caso, actividad SMU

**Actividad SMU**:
El registro que el área SMU levanta en sitio: su cabecera, su evidencia, sus
materiales y el detalle propio del formulario que le corresponde. Nace en borrador
y se somete a aprobación antes de cerrar.
_Avoid_: reporte, ficha, caso, formulario

**OT (Orden de Trabajo)**:
Identificador que agrupa y referencia una o más actividades. Formato observable:
`OT-2024-001`.
_Avoid_: orden, work order, orden de servicio

**INC (Número de Incidente)**:
Número que identifica el incidente que origina una actividad correctiva o de
emergencia.
_Avoid_: ticket, reporte

**Estado**:
Posición de una Actividad en su ciclo de vida. Valores: pendiente, en progreso,
completada, cancelada, pausada, reprogramada. Mide avance del trabajo, no aprobación.
_Avoid_: fase, etapa, status, estado de aprobación

**Estado de aprobación**:
Posición de una Actividad SMU en su ciclo de aprobación. Valores: borrador,
enviado, aprobado, rechazado. Mide si el reporte fue aceptado, no cuánto falta
por ejecutar.
_Avoid_: estado, fase, etapa, status

**Evidencia**:
Constancia material de que una actividad se ejecutó: fotografías, firmas y
certificados. Lo que se guarda como prueba.
_Avoid_: adjunto, anexo, archivo

**Catálogo Frecuente**:
Lista de ítems que se repiten y se reusan con autocompletar de un clic. Nace de lo
ya usado, para no digitar lo mismo cada vez.
_Avoid_: catálogo, plantilla, preset

### Mantenimiento y obras

**Preventivo**:
Mantenimiento programado que se hace antes de que falle el equipo.
_Avoid_: preventiva, mantenimiento preventivo

**Correctivo**:
Intervención reactiva ante una falla ya ocurrida. Cubre también las emergencias.
_Avoid_: correctiva, reparación

**CAPEX**:
Proyecto de inversión en bienes o mejoras, distinto del gasto operativo corriente.
_Avoid_: capex, inversión, proyecto

**Tipología (1, 3, 5)**:
Categorías de formulario CAPEX. Cada tipología tiene su propio flujo de pasos y su
propio conjunto de actividades.
_Avoid_: tipo, categoría, tipologia

**Planta**:
Equipo o instalación que recibe mantenimiento preventivo y hallazgos.
_Avoid_: equipo, instalación, sistema
