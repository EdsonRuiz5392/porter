# Arquitectura y modelo de estados — Porter (Avance 02)

Describe cómo está construido el servicio en `main` y qué transiciones de estado son válidas. Las razones de cada decisión están en [`docs/decisions/`](../decisions/); las firmas de las funciones, en [`contratos-interfaces.md`](contratos-interfaces.md).

## 1. Vista general

```
   Cliente (cli.py)
        │  TCP en 127.0.0.1: 4 bytes de longitud + JSON
        ▼
   Entrada (entrada.py) ─────► Operación (configuración, salud, cierre)
        │  usa protocolo.py
        ▼
   Control (control.py)  ─────► Cola (cola.py, solo IDs, en memoria)
        │        │
        │        └───────────► Lanzador (launcher.py) ──► un grupo de procesos por trabajo
        ├────────────────────► Persistencia (SQLite en modo WAL)
        └────────────────────► Bitácora (jobrunner.log)
```

`main.py` arma las piezas, recupera el historial y atiende las señales de cierre.

## 2. Modelo de concurrencia

Un solo proceso y un solo hilo de `asyncio` atienden a los clientes y coordinan los trabajos (ADR-001). Las operaciones de SQLite se despachan a hilos con `run_in_executor` (ADR-003). Cada trabajo es un proceso aparte, en su propio grupo (ADR-008).

Como `asyncio` solo cambia de tarea en un `await`, el estado compartido se protege así:

| Riesgo | Mecanismo | Referencia |
|---|---|---|
| Dos envíos revisan la cola y encolan a la vez | `_submit_lock` cubre de revisar duplicados y capacidad hasta encolar | ADR-006 |
| Dos envíos con el mismo folio | El mismo candado, y `UNIQUE` en la base como respaldo | ADR-007 |
| Pasarse del límite de concurrencia | `_running_count + _reserved_count`: el lugar se reserva al sacar el trabajo de la cola | ADR-009 |
| Cancelar un trabajo que ya salió de la cola y aún no corre | `_en_curso` y `_cancel_requested`; `_run_job` los revisa antes y después de lanzar | ADR-008 |

## 3. Máquina de estados

```
                    ┌──────────► CANCELED   (cancelado en cola o en tránsito)
                    │
   (envío) ──► QUEUED ─────────► FAILED     (no se pudo lanzar: -1)
                    │
                    ▼
                 RUNNING ──────► SUCCEEDED  (código 0, sin cancelación pedida)
                    │ │
                    │ └────────► CANCELED   (alguien pidió cancelar, o el cierre)
                    └──────────► FAILED     (código ≠ 0, señal ajena, falla de captura o caída)
```

`SUCCEEDED`, `FAILED` y `CANCELED` son **terminales**: ninguna operación los cambia.

| De | A | Cuándo | Quién lo escribe | Evento en bitácora |
|---|---|---|---|---|
| — | QUEUED | Envío aceptado; se guarda y se encola | `submit` | `CREATED` |
| QUEUED | CANCELED | Se cancela y sigue en la cola | `request_cancel` | `CANCEL_REQUESTED`, `CANCELED` |
| QUEUED | CANCELED | Se cancela ya fuera de la cola, antes de lanzarlo | `_run_job` | `CANCEL_REQUESTED`, `CANCELED` |
| QUEUED | FAILED | `launcher.start` falla, por ejemplo si el programa no existe. Código -1 | `_run_job` | `FAILED`, `ERROR` |
| QUEUED | RUNNING | El proceso arrancó; se guarda el PID | `mark_running` | `STARTED` |
| RUNNING | SUCCEEDED | Código 0 y nadie pidió cancelar | `_run_job` | `SUCCEEDED` |
| RUNNING | FAILED | Código distinto de 0 | `_run_job` | `FAILED` |
| RUNNING | FAILED | Murió por una señal que nadie pidió. Código negativo | `_run_job` | `KILLED_BY_SIGNAL`, `FAILED` |
| RUNNING | FAILED | Falló la captura de salida; se termina el grupo. Código -1 | `_run_job` | `FAILED`, `ERROR` |
| RUNNING | FAILED | Al arrancar, el trabajo había quedado RUNNING tras una caída. Código -1 | `recover_on_startup` | `INTERRUPTED` |
| RUNNING | CANCELED | Se pidió cancelar, incluso si el programa salió con 0 | `_run_job` | `CANCEL_REQUESTED`, `CANCELED` |

**Regla de escritura:** el estado final de un trabajo que ya salió de la cola lo escribe solo `_run_job`. Por eso varias cancelaciones simultáneas producen un único estado final (RF-26).

**Estado "en tránsito":** entre `dequeue()` y `mark_running()`, el trabajo sigue `QUEUED` en la base, pero ya no está en la cola. Puede cancelarse (`_en_curso`). `health` no lo cuenta como en cola ni en ejecución; ver #59.

## 4. Persistencia y consistencia

- **Formato:** tabla `jobs` en SQLite, modo WAL, con `client_request_id UNIQUE` (ADR-003, ADR-007).
- **Escritura:** `save_job` usa `INSERT … ON CONFLICT(id) DO UPDATE` y cada escritura es una transacción (RNF-11, RNF-28).
- **Conexiones:** cada operación abre y cierra su propia conexión, en un hilo.
- **Orden al aceptar:** primero se guarda y después se encola, así un trabajo aceptado nunca existe solo en memoria.
- **La cola vive en memoria** y se reconstruye al arrancar con los trabajos `QUEUED` de la base.

## 5. Recuperación tras reinicio (ADR-010)

`recover_on_startup` corre antes de aceptar conexiones.

| Estado guardado | Acción |
|---|---|
| SUCCEEDED, FAILED, CANCELED | No se toca |
| QUEUED | `cola.restore()`: vuelve a la cola, aunque se exceda `MAX_QUEUE` |
| RUNNING | Se termina su grupo si sigue vivo y es nuestro, y queda FAILED (-1) con `INTERRUPTED` |

Para no matar un proceso ajeno por un PID reutilizado, `_proceso_es_nuestro` compara la hora de arranque real (`/proc/<pid>/stat`) con `started_at`, con tolerancia de ±2 s:

| Se encuentra | Acción | Evento |
|---|---|---|
| Existe y la hora coincide | `killpg` con SIGKILL | `ORPHAN_KILLED` |
| Existe y la hora no coincide | No se toca | `ORPHAN_SKIPPED` |
| Ya no existe el líder | `killpg` de todos modos: si el grupo existe, solo quedan descendientes nuestros | `ORPHAN_KILLED` si había algo |
| Sin permiso | No se toca | `ORPHAN_ERROR` |

## 6. Cancelación y escalamiento (ADR-008)

`launcher.cancel`: SIGTERM al grupo → hasta `grace_seconds` esperando a que desaparezca todo el grupo → SIGKILL si queda alguien → `proc.wait()` para no dejar zombis.

Cada trabajo se lanza con `start_new_session=True`, por eso su PID es también el ID de su grupo y el Ctrl+C de la terminal del servicio no le llega.

## 7. Captura de salida (ADR-009)

`stream_output` lee stdout y stderr al mismo tiempo, por bloques de 64 KiB, y los guarda como bytes con `flush()` en cada bloque. La salida se puede consultar mientras el trabajo corre. Los trabajos reciben `stdin=DEVNULL`.

## 8. Arranque y cierre (ADR-011)

**Arranque:** validar configuración → crear carpetas → verificar que el puerto esté libre → abrir base y bitácora → `SERVICE_STARTED` → recuperar → escuchar.

**Cierre (SIGINT o SIGTERM):** `SHUTDOWN_STARTED` → dejar de aceptar → esperar hasta `SHUTDOWN_TIMEOUT` → cancelar lo que siga → esperar hasta 5 s a que se registre → `SERVICE_STOPPED`.

## 9. Eventos de la bitácora

Formato: `fecha UTC | job=<ID o -> | EVENTO | detalle`.

| Grupo | Eventos |
|---|---|
| Ciclo de un trabajo | `CREATED`, `STARTED`, `SUCCEEDED`, `FAILED`, `CANCELED` |
| Cancelación y fallas | `CANCEL_REQUESTED`, `KILLED_BY_SIGNAL`, `ERROR` |
| Solicitudes | `REJECTED`, `DUPLICATE`, `REQUEST_ID_CONFLICT`, `PROTOCOL_ERROR` |
| Recuperación | `INTERRUPTED`, `ORPHAN_KILLED`, `ORPHAN_SKIPPED`, `ORPHAN_ERROR`, `RECOVERY_OVER_CAPACITY` |
| Servicio | `SERVICE_STARTED`, `SHUTDOWN_STARTED`, `SERVICE_STOPPED`, `SERVICE_ERROR` |

El escalamiento a SIGKILL se registra en la salida del servicio mediante `logging`, no en `jobrunner.log`.

## 10. Límites y defectos conocidos

| Tema | Situación | Referencia |
|---|---|---|
| Acceso remoto | `allowed_networks` se recibe pero no se aplica | Hito 3 |
| Proceso que sale de su grupo (`setsid`) | Queda fuera de control | ADR-008 |
| Salidas de varios MB en `output` | Pueden exceder `MAX_MESSAGE_BYTES` | ADR-009 |
| Crecimiento del disco | No hay borrado automático | ADR-012 |
| `database is locked` bajo carga | Un trabajo válido puede terminar FAILED (-1) | #58 |
| `health` no cuenta trabajos en tránsito | Puede reportar 0 y 0 con un trabajo por arrancar | #59 |
