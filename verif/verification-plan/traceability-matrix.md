# Matriz de Trazabilidad — Porter (JobRunner)

**Responsable:** Edson Ruiz (líder de verificación) · **Aprueba excepciones:** Ángel Vences (responsable de producto)
**Estado:** en construcción · **Última actualización:** 2026-09-29 · **Commit de referencia:** `2cedea0`
**Referencias:** RF (doc 02), RNF (doc 03), casos y columnas obligatorias (doc 05), hitos (doc 06), dueños según `project-management/roles-matrix.md`.
**Plan asociado:** [plan-verificacion.md](plan-verificacion.md) · **Evidencia:** `verif/results/<run-id>/`

## Reglas de esta matriz

- Cadena obligatoria (doc 05): **Requisito → Método → Caso → Resultado esperado → Evidencia → PASS/FAIL**.
- Un requisito pasa a **PASS** solo con una corrida registrada en `verif/results/<run-id>/` (commit, entorno, comando, salida). Sin corrida, queda **Pendiente** aunque "parezca" cumplirse (doc 02, reglas de aceptación).
- Todo **FAIL** o defecto detectado por inspección abre un issue, y su número va en la columna Defecto/Excepción (doc 05, gestión de defectos).
- **Dueño:** quien responde por el requisito en la revisión, según `roles-matrix.md`. Que una función viva en otro módulo no cambia al dueño (ver `trazabilidad-funciones.md`).
- **Métodos** (doc 05): Prueba, Análisis, Inspección, Demostración.
- **Hito** (doc 06): H1 = Avance 01 y RT-1 (6 de octubre); H2 = concurrencia y persistencia; H3 = red privada; H4 = candidato de entrega.
- Los casos TC-001 a TC-024 y su mapeo son los del doc 05. TC-025 a TC-027 los **propone el equipo** para requisitos sin caso asignado; los aprueba producto.

## Requisitos funcionales (RF-01 a RF-30)

| Req ID | Descripción breve | Dueño | Prioridad | Método | Caso(s) | Evidencia | Resultado | Defecto/Excepción | Hito |
|---|---|---|---|---|---|---|---|---|---|
| RF-01 | Enviar comando con argumentos y recibir un ID único | Dylan | Alta | Prueba | TC-001 | Salida del cliente + bitácora | Pendiente | — | H1 |
| RF-02 | Rechazar entradas vacías, mal formadas o no autorizadas con mensaje útil | Dylan | Alta | Prueba | TC-001 | Respuesta `error` + código de salida del cliente | Pendiente | — | H1 |
| RF-03 | Mantener cola cuando no hay capacidad inmediata | Dylan | Alta | Prueba | TC-002 | Línea de tiempo de estados | Pendiente | — | H1 (cola inicial) |
| RF-04 | Ejecutar en procesos separados sin bloquear nuevas solicitudes | Marcos | Alta | Prueba | TC-002 | `ps` con PID/PPID + tiempos de respuesta | Pendiente | #15 (bloqueante): `launcher` sin `start` | H1 |
| RF-05 | Configurar y respetar el máximo de trabajos simultáneos | Dylan | Alta | Prueba | TC-002 | Línea de tiempo + bitácora | Pendiente | — | H2 |
| RF-06 | Estados QUEUED, RUNNING, SUCCEEDED, FAILED y CANCELED | Dylan | Alta | Prueba / Inspección | TC-003 | Secuencia de estados + `models.JobStatus` | Pendiente | — | H1 |
| RF-07 | Tiempos de recepción, inicio y fin, y código de salida | Dylan | Alta | Prueba | TC-003, TC-006 | Campos del `Job` en `status` | Pendiente | — | H1 |
| RF-08 | Consultar estado y metadatos por ID | Dylan | Alta | Prueba | TC-004 | Salida de `status` | Pendiente | — | H1 |
| RF-09 | Listar trabajos con filtro por estado | Dylan | Media | Prueba | TC-004 | Salida de `list` con y sin filtro | Pendiente | — | H1 |
| RF-10 | Cancelar en cola o en ejecución y reflejar el resultado | Marcos | Alta | Prueba | TC-005 | Estados + señal enviada + `ps` | Pendiente | #15 (bloqueante): `launcher` sin `cancel` | H1 |
| RF-11 | Capturar stdout y stderr sin mezclarlos y consultarlos | Ángel | Alta | Prueba | TC-006 | Archivos `stdout_path` / `stderr_path` | Pendiente | — | H1 |
| RF-12 | Conservar metadatos y resultados tras reiniciar el servicio | Ángel | Crítica | Prueba | TC-007 | Estado antes y después del reinicio | Pendiente | — | H2 |
| RF-13 | Recuperar historial y marcar trabajos interrumpidos al arrancar | Ángel | Crítica | Prueba | TC-007 | Estados tras el reinicio + bitácora | Pendiente | — | H2 |
| RF-14 | Bitácora de eventos y errores con marca temporal e ID de trabajo | Ángel | Alta | Prueba / Inspección | TC-025 | Extracto de `jobrunner.log` | Pendiente | TC-025 propuesto | H2 |
| RF-15 | Inicio y detención controlados, sin aceptar trabajos durante el cierre | Ángel | Alta | Prueba | TC-009 | Bitácora del cierre + rechazo durante el cierre | Pendiente | — | H2 |
| RF-16 | Configurar directorio de datos, concurrencia, interfaz y puerto | Ángel | Media | Prueba / Inspección | TC-013 | Variables `JOBRUNNER_*` + comportamiento | Pendiente | — | H2 |
| RF-17 | Ayuda de uso y códigos de salida adecuados en el cliente | Dylan | Media | Prueba | TC-015 | Salida de `--help` + códigos de salida | Pendiente | — | H1 |
| RF-18 | Cliente remoto: enviar, consultar, listar y cancelar | Juan | Alta | Prueba / Demostración | TC-010 | Registros del cliente y del servicio | Pendiente | — | H3 |
| RF-19 | Misma semántica en operación local y remota | Juan | Alta | Prueba | TC-010 | Comparación local frente a remoto | Pendiente | — | H3 |
| RF-20 | Restringir el acceso remoto a redes o direcciones permitidas | Juan | Crítica | Prueba / Análisis | TC-011 | `JOBRUNNER_ALLOWED_NETWORKS` + intento rechazado | Pendiente | — | H3 |
| RF-21 | Delimitar mensajes, identificar errores y tolerar lecturas parciales | Juan | Alta | Prueba | TC-012 | Registro de mensajes fragmentados | Pendiente | — | H3 |
| RF-22 | Manejar desconexiones del cliente sin afectar el servicio | Juan | Alta | Prueba | TC-012, TC-019 | Servicio vivo + estados coherentes | Pendiente | — | H3 |
| RF-23 | Rechazar y registrar solicitudes que exceden límites | Ángel | Media | Prueba | TC-016, TC-026 | Respuesta de rechazo + bitácora | Pendiente | TC-026 propuesto | H2 |
| RF-24 | Resumen de salud del servicio | Ángel | Media | Prueba | TC-013 | Respuesta `health_response` | Pendiente | — | H3 |
| RF-25 | Rechazo explícito con la cola llena, sin perder trabajos aceptados | Dylan | Alta | Prueba | TC-016 | Respuesta `QUEUE_FULL` + estados | Pendiente | — | H2 |
| RF-26 | Dos cancelaciones concurrentes dan un estado final coherente | Marcos | Alta | Prueba | TC-017 | Respuestas de ambos clientes + estado final | Pendiente | — | H2 |
| RF-27 | Solicitudes duplicadas sin estados contradictorios | Dylan | Media | Prueba | TC-018a, TC-018b | Estados + semántica del ADR-006 | Pendiente | Dos caminos: con y sin `client_request_id` | H2 |
| RF-28 | Estado coherente si el cliente se desconecta durante una solicitud | Juan | Alta | Prueba | TC-019 | Estado final + bitácora | Pendiente | — | H3 |
| RF-29 | Detectar la terminación inesperada de un hijo y liberar sus recursos | Marcos | Crítica | Prueba | TC-020 | Estado terminal + `ps` sin zombis | Pendiente | #15 (bloqueante): `launcher` sin `stream_output` | H2 (recomendado en H1) |
| RF-30 | Escalamiento documentado si el trabajo no termina al cancelarse | Marcos | Alta | Prueba | TC-021 | Bitácora con SIGTERM y SIGKILL | Pendiente | #15 (bloqueante) | H2 (recomendado en H1) |

## Requisitos no funcionales (RNF-01 a RNF-34)

| Req ID | Descripción breve | Dueño | Prioridad | Método | Caso(s) | Evidencia | Resultado | Defecto/Excepción | Hito |
|---|---|---|---|---|---|---|---|---|---|
| RNF-01 | Ejecutar en la distribución Linux declarada | Edson | Crítica | Prueba / Inspección | TC-014 | Registro del entorno en cada corrida | Pendiente | Distribución de referencia: Ubuntu 24.04 LTS (por confirmar con producto) | H1 |
| RNF-02 | Construcción reproducible desde un clon limpio | Edson | Alta | Prueba / Inspección | TC-014 | Bitácora de instalación desde clon limpio | Pendiente | El README aún no documenta instalación ni ejecución | H1 |
| RNF-03 | Operar sin privilegios de root | Marcos | Alta | Prueba / Análisis | TC-014 | `id -u` durante la corrida | Pendiente | — | H1 |
| RNF-04 | Mantener 3 trabajos simultáneos con límite 3 | Dylan | Alta | Prueba | TC-002 | Línea de tiempo + `ps` | Pendiente | — | H2 |
| RNF-05 | Consulta de estado en 1 s o menos con 100 trabajos | Dylan | Media | Prueba | TC-004 | Medición de tiempos | Pendiente | — | H2 |
| RNF-06 | Soportar al menos 500 registros sin pérdida de metadatos | Ángel | Media | Prueba | TC-027 | Conteo antes y después | Pendiente | TC-027 propuesto | H2 |
| RNF-07 | Nunca más procesos que el límite de concurrencia | Dylan | Alta | Prueba | TC-002 | Máximo de procesos observado | Pendiente | — | H2 |
| RNF-08 | Una solicitud inválida o una desconexión no termina el servicio | Juan | Crítica | Prueba | TC-008 | Servicio vivo tras entradas inválidas | Pendiente | — | H1 |
| RNF-09 | El fallo de un trabajo no afecta a otros | Marcos | Crítica | Prueba | TC-008 | Bitácora + estados de los demás trabajos | Pendiente | — | H1 |
| RNF-10 | Tras un reinicio, no reportar RUNNING un proceso no controlado | Ángel | Crítica | Prueba | TC-007 | Estados tras el reinicio | Pendiente | — | H2 |
| RNF-11 | Escritura persistente sin estados parciales | Ángel | Crítica | Prueba / Análisis | TC-007 | Integridad de `jobs.db` tras interrupción | Pendiente | — | H2 |
| RNF-12 | No escuchar en interfaces públicas por defecto | Juan | Crítica | Inspección / Prueba | TC-011 | `ss -ltnp` + `JOBRUNNER_HOST` por defecto | Pendiente | — | H3 |
| RNF-13 | Acceso remoto solo desde localhost, subred privada o VPN | Juan | Crítica | Prueba | TC-011 | Intento permitido y rechazado | Pendiente | — | H3 |
| RNF-14 | Validar longitud y formato de los mensajes de red | Juan | Alta | Prueba | TC-012 | Respuestas a mensajes inválidos o demasiado grandes | Pendiente | — | H3 |
| RNF-15 | Las bitácoras no exponen secretos ni configuración sensible | Ángel | Media | Inspección | TC-025 | Revisión de `jobrunner.log` | Pendiente | — | H4 |
| RNF-16 | Mínimo privilegio y modelo de amenazas documentado | Ángel | Media | Inspección / Análisis | TC-014 | Documento de amenazas + corrida sin root | Pendiente | — | H3 |
| RNF-17 | Código en módulos con responsabilidades identificables | Edson | Media | Inspección | Prueba de contratos | `src/` por módulo y dueño + `verif/results/20260929-1508-2cedea0/` | PASS | — | H1 |
| RNF-18 | Interfaces públicas y decisiones relevantes documentadas | Edson | Media | Inspección | Prueba de contratos | `contratos-interfaces.md`, ADR-001 a ADR-006 + corrida `20260929-1508-2cedea0` | PASS | ADR-005 y ADR-006 siguen en estado Propuesto | Todos |
| RNF-19 | Sin advertencias nuevas bajo las opciones acordadas | Edson | Media | Análisis | — | Salida del analizador estático | Pendiente | Herramienta por acordar (propuesta: `ruff`) | H1 |
| RNF-20 | Pruebas automatizadas ejecutables con un solo comando | Edson | Alta | Prueba | Prueba de contratos | `python -m pytest verif/scripts/test_contratos.py -v` → `verif/results/20260929-1508-2cedea0/` | PASS | — | H1 |
| RNF-21 | Errores que indican operación, causa y acción sugerida | Dylan | Media | Prueba | TC-015 | Mensajes de error capturados | Pendiente | — | H1 |
| RNF-22 | La bitácora correlaciona una solicitud con su trabajo | Ángel | Media | Prueba / Inspección | TC-025 | Extracto de la bitácora | Pendiente | — | H2 |
| RNF-23 | La guía de usuario permite usar el sistema sin ayuda | Dylan | Media | Demostración | TC-015 | Escenarios A, B y E del doc 05 | Pendiente | — | H4 |
| RNF-24 | Protocolo tolera mensajes fragmentados y solicitudes seguidas | Juan | Alta | Prueba | TC-012 | Registro de mensajes fragmentados | Pendiente | — | H3 |
| RNF-25 | Liberar sockets y procesos hijos al cerrar | Ángel | Alta | Prueba | TC-009 | `ss` y `ps` después del cierre | Pendiente | — | H2 |
| RNF-26 | Demostración remota solo en red privada o VPN | Juan | Crítica | Inspección / Demostración | TC-010, TC-011 | Configuración de bind + reglas | Pendiente | — | H3 |
| RNF-27 | Transiciones de estado consistentes bajo concurrencia | Dylan | Alta | Prueba | TC-017 | Secuencias de estado sin regresiones | Pendiente | — | H2 |
| RNF-28 | Actualizaciones persistentes atómicas o recuperables | Ángel | Crítica | Prueba | TC-022 | Integridad tras la interrupción | Pendiente | — | H2 |
| RNF-29 | Backpressure o rechazo al llegar a los límites | Dylan | Alta | Prueba | TC-016 | Respuesta de rechazo | Pendiente | — | H2 |
| RNF-30 | Sin procesos huérfanos tras un cierre o una falla | Marcos | Crítica | Prueba | TC-020 | `ps` después del cierre | Pendiente | — | H2 |
| RNF-31 | La recuperación distingue pendientes, terminados e interrumpidos | Ángel | Alta | Prueba | TC-022 | Estados tras la recuperación | Pendiente | — | H2 |
| RNF-32 | Versionado del protocolo y rechazo de mensajes incompatibles | Juan | Media | Prueba | TC-023 | Respuesta `VERSION_UNSUPPORTED` | Pendiente | — | H3 |
| RNF-33 | Liberar memoria, procesos, archivos y sockets bajo estrés | Marcos | Alta | Prueba | TC-024 | Mediciones antes y después de la carga | Pendiente | — | H4 |
| RNF-34 | Decisiones de seguridad, consistencia o recuperación con análisis de riesgo y prueba | Ángel | Media | Inspección | — | Revisión de `docs/decisions/` | Pendiente | — | Todos |

## Decisiones de arquitectura (ADR) y los requisitos que cubren

Tomado del encabezado "Requisitos relacionados" de cada ADR. Sirve para la parte de la RT-1 en que hay que **defender una decisión**.

| ADR | Decisión | Estado | Requisitos | Módulos |
|---|---|---|---|---|
| ADR-001 | Python 3 como lenguaje | Aceptado | Transversal | Todos |
| ADR-002 | Concurrencia del servicio con `asyncio` | Aceptado | RF-04, 05, 18, 19, 22; RNF-04, 07, 24, 27 | `entrada`, `control` |
| ADR-003 | IPC con procesos hijos vía `asyncio.create_subprocess_exec` | Aceptado | RF-04, 07, 11, 29; RNF-09, 25, 30 | `launcher` |
| ADR-004 | Persistencia en SQLite (modo WAL) | Aceptado | RF-12, 13; RNF-06, 10, 11, 28, 31 | `persistencia` |
| ADR-005 | Protocolo con prefijo de longitud y JSON | Propuesto | RF-18, 21, 22; RNF-14, 24, 32 | `protocolo`, `entrada`, `cli` |
| ADR-006 | Saturación (rechazo inmediato), duplicados (`client_request_id` opcional) y cancelación (SIGTERM → gracia → SIGKILL) | Propuesto | RF-25, 27, 30; RNF-29 | `control`, `cola`, `launcher` |

## Casos de prueba

Mapeo oficial del doc 05. Cada caso tendrá su archivo en `verif/test-cases/TC-XXX.md` con el formato del doc 05.

| Caso | Título | Requisitos | Hito |
|---|---|---|---|
| TC-001 | Enviar trabajo válido | RF-01, RF-02 | H1 |
| TC-002 | Cola y límite de concurrencia | RF-03, RF-04*, RF-05, RNF-04, RNF-07 | H1 (parcial) · H2 |
| TC-003 | Estados y tiempos | RF-06, RF-07 | H1 |
| TC-004 | Consultar y listar | RF-08, RF-09, RNF-05 | H1 · H2 (RNF-05) |
| TC-005 | Cancelar en cola y en ejecución | RF-10 | H1 |
| TC-006 | Capturar stdout, stderr y código de salida | RF-11, RF-07 | H1 |
| TC-007 | Reinicio y recuperación | RF-12, RF-13, RNF-10, RNF-11 | H2 |
| TC-008 | Aislamiento de fallo | RNF-08, RNF-09 | H1 |
| TC-009 | Cierre controlado | RF-15, RNF-25 | H2 |
| TC-010 | Flujo remoto completo en LAN/VPN | RF-18, RF-19, RNF-26 | H3 |
| TC-011 | Restricción de red | RF-20, RNF-12, RNF-13 | H3 |
| TC-012 | Fragmentación y desconexión | RF-21, RF-22, RNF-14, RNF-24 | H3 |
| TC-013 | Configuración y salud | RF-16, RF-24 | H2 · H3 |
| TC-014 | Construcción desde clon limpio | RNF-01, RNF-02, RNF-03, RNF-16* | H1 |
| TC-015 | Usabilidad documental | RF-17, RNF-21, RNF-23 | H1 · H4 |
| TC-016 | Saturación de cola y rechazo explícito | RF-25, RNF-29, RF-23* | H2 |
| TC-017 | Cancelaciones concurrentes | RF-26, RNF-27 | H2 |
| TC-018a / TC-018b | Solicitud duplicada, con y sin `client_request_id` (ADR-006) | RF-27 | H2 |
| TC-019 | Desconexión durante una solicitud | RF-28, RF-22 | H3 |
| TC-020 | Terminación inesperada del proceso hijo | RF-29, RNF-30 | H2 (recomendado en H1) |
| TC-021 | Escalamiento de la cancelación | RF-30 | H2 (recomendado en H1) |
| TC-022 | Interrupción durante la persistencia | RNF-28, RNF-31 | H2 |
| TC-023 | Compatibilidad de protocolo | RNF-32 | H3 |
| TC-024 | Liberación de recursos bajo carga | RNF-33 | H4 |
| TC-025 | Bitácora de eventos correlacionable (**propuesto**) | RF-14, RNF-15, RNF-22 | H2 |
| TC-026 | Solicitud que excede los límites configurados (**propuesto**) | RF-23 | H2 |
| TC-027 | Carga de 500 registros sin pérdida (**propuesto**) | RNF-06 | H2 |
| Prueba de contratos | `verif/scripts/test_contratos.py`: cada módulo expone las funciones del contrato | RNF-17, RNF-18, RNF-20 | H1 (ya ejecutada) |

\* Requisito que el equipo agregó al caso, además del mapeo oficial del doc 05.

## Corridas registradas

| run-id | Qué se corrió | Commit | Resultado | Defectos abiertos |
|---|---|---|---|---|
| `20260929-1508-2cedea0` | Prueba de contratos (56 comprobaciones) | `2cedea0` | 53 PASS, 3 FAIL | #15: `launcher` sin `start`, `cancel`, `stream_output` |

## Cobertura

| Grupo | Total | Con caso o método asignado | Con dueño | PASS | FAIL / bloqueado | Pendiente |
|---|---|---|---|---|---|---|
| RF-01 a RF-30 | 30 | 30 | 30 | 0 | 4 bloqueados por #15 | 26 |
| RNF-01 a RNF-34 | 34 | 34 | 34 | 3 | 0 | 31 |

## Pendientes de decisión (producto: Ángel)

1. Confirmar Ubuntu 24.04 LTS como distribución de referencia (RNF-01).
2. Aceptar los casos TC-025, TC-026 y TC-027.
3. Elegir el analizador estático para RNF-19.
4. Resolver la contradicción del alcance: `control.list` y `recover_on_startup` usan `persistencia.load_all`, marcada "sin tocar" para este avance.

## Historial de cambios

| Fecha | Cambio | Autor |
|---|---|---|
| 2026-09-20 | Versión inicial con 17 requisitos | Dylan |
| 2026-09-29 | Matriz completa (RF-01 a RF-30, RNF-01 a RNF-34) con columna de dueño según `roles-matrix.md`, ADR remapeados a los seis archivos actuales, casos TC-025 a TC-027 propuestos y sección de corridas. RNF-01 y RNF-03 regresan de PASS a Pendiente por no existir corrida registrada (doc 02). RNF-17, RNF-18 y RNF-20 pasan a PASS con la corrida `20260929-1508-2cedea0`. Defecto #15 anotado en RF-04, RF-10, RF-29 y RF-30 | Edson |
