# Contratos de interfaz — JobRunner

Especificación de qué función expone cada módulo, qué recibe, qué regresa, y qué RF/ADR cubre. Es la referencia fija para implementar.

---

## 1. Propósito

Cada módulo del sistema es responsable de un archivo. Este documento define su interfaz pública (firmas de función) para que los demás módulos puedan usarlo sin conocer su implementación interna.

## 2. Formato de las firmas

Sintaxis Python con type hints. `async def` = corutina, se llama con `await`. `X | None` = el valor puede venir vacío. `self` no cuenta como parámetro real al llamar la función desde afuera.

## 3. Estados válidos

`QUEUED → RUNNING → (SUCCEEDED | FAILED | CANCELED)`, o directo `QUEUED → CANCELED` (cancelado antes de lanzarse) y `QUEUED → FAILED` (no se pudo lanzar). Los estados finales no cambian. El detalle está en [`arquitectura-y-estados.md`](arquitectura-y-estados.md).

---

## 4. `comun/models.py`

Sin dueño único — todos los módulos lo importan.

```python
class JobStatus(str, Enum):
    QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELED

@dataclass
class Job:
    id: str
    command: str
    args: list[str]
    status: JobStatus
    client_request_id: str | None = None
    pid: int | None = None
    submitted_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
```

---

## 5. `comun/protocolo.py`

- **Dueño**: Juan
- **RF**: 21
- **ADR**: ADR-004

Framing: 4 bytes de longitud (`struct`, `!I`) + JSON en UTF-8.

```python
async def read_message(reader: asyncio.StreamReader, max_len: int) -> dict
async def write_message(writer: asyncio.StreamWriter, message: dict) -> None
```

Excepciones: `ProtocolError` (base), `MessageTooLargeError`, `InvalidMessageError`.

Constantes: `ERROR_INVALID_REQUEST`, `ERROR_QUEUE_FULL`, `ERROR_NOT_FOUND`, `ERROR_VERSION_UNSUPPORTED`, `ERROR_SERVICE_CLOSING`, `ERROR_INTERNAL`, `ERROR_REQUEST_ID_CONFLICT`, `PROTOCOL_VERSION = 1`.

### Esquema de mensajes (`"version": 1` obligatorio en todos)

| type (request) | Campos | type (response) | Campos |
|---|---|---|---|
| `submit` | `command`, `args`, `client_request_id?` | `submit_response` | `ok`, `job_id`, `status` |
| `status` | `job_id` | `status_response` | `job` (objeto Job completo) |
| `list` | `status_filter?` | `list_response` | `jobs` (lista con `id`, `command`, `status`, `exit_code`) |
| `cancel` | `job_id` | `cancel_response` | `job_id`, `result` |
| `output` | `job_id`, `stream` (`"stdout"` \| `"stderr"`) | `output_response` | `job_id`, `stream`, `content` |
| `health` | — | `health_response` | `active`, `running`, `queued`, `recent_errors` |
| — | — | `error` | `code`, `message` |

`result` en `cancel_response`: `"CANCELING" | "ALREADY_FINISHED"`. Un trabajo inexistente responde `error` con `NOT_FOUND`.

Un mensaje demasiado grande o que no sea JSON válido recibe `error` con `INVALID_REQUEST` y se cierra la conexión; una versión incompatible recibe `VERSION_UNSUPPORTED` y la conexión sigue abierta.

---

## 6. `servicio/entrada.py`

- **Dueño**: Juan
- **RF**: 18, 19, 20, 21, 22, 28
- **ADR**: ADR-001, ADR-004

```python
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, job_manager, max_message_bytes: int) -> None
async def main(host: str, port: int, allowed_networks: list[str], job_manager, max_message_bytes: int) -> None
```
Traduce cada `type` de mensaje a una función de `control.py` (o de `operacion.py` para `health`), y traduce las excepciones de `control.py` (`InvalidRequestError`, `QueueFullError`, `ServiceClosingError`, etc.) a un mensaje `"error"` con su código correspondiente. Registra `PROTOCOL_ERROR` en la bitácora y tolera que el cliente se desconecte (ADR-007, ADR-011).

---

## 7. `servicio/gestion_trabajos/cola.py` y `control.py`

- **Dueño**: Dylan
- **RF**: 01, 02, 03, 05, 06, 07, 08, 09, 17, 25, 27
- **ADR**: ADR-001, ADR-005, ADR-006, ADR-007, ADR-010

### `cola.py`
```python
def __init__(self, max_size: int)
def is_full(self) -> bool
def enqueue(self, job_id: str) -> None
def restore(self, job_id: str) -> None   # solo en la recuperación; no aplica el límite (ADR-010)
def dequeue(self) -> str | None
def remove(self, job_id: str) -> bool
def size(self) -> int
```
Excepción: `QueueFullError`.

### `control.py`
```python
def __init__(self, cola, launcher, persistencia, bitacora, max_concurrency: int, grace_seconds: float, data_dir: str)
async def submit(self, command: str, args: list[str], client_request_id: str | None) -> Job
async def get(self, job_id: str) -> Job | None
async def list(self, status_filter: JobStatus | None = None) -> list[Job]
async def request_cancel(self, job_id: str) -> str
async def get_output(self, job_id: str, stream: str) -> str | None
async def mark_running(self, job_id: str, pid: int) -> None
async def mark_finished(self, job_id: str, exit_code: int | None, status: JobStatus) -> None
async def recover_on_startup(self) -> None
async def cancel_all_running(self, motivo: str) -> int
def in_progress_count(self) -> int
def is_accepting(self) -> bool
def stop_accepting(self) -> None
def running_count(self) -> int
def queued_count(self) -> int
def recent_errors_count(self) -> int
```
Excepciones: `ControlError` (base), `InvalidRequestError`, `QueueFullError`, `ServiceClosingError`, `RequestIdConflictError`.

Internamente (no forman parte del contrato público, pero todos los usan): `_try_dispatch()` saca de la cola y arranca trabajos cuando hay lugar; `_run_job(job_id)` corre en segundo plano el ciclo completo de un trabajo.

Nota de responsabilidad: `get_output` apoya RF-11 (Ángel), `request_cancel` apoya RF-10 (Marcos), y `recover_on_startup`/`is_accepting`/`stop_accepting`/`running_count`/`queued_count`/`recent_errors_count` apoyan RF-13/15/23/24 (Ángel). Viven en `control.py` porque necesitan su estado interno, pero la responsabilidad de esos RF sigue siendo de quien los tiene asignados en la tabla del equipo.

---

## 8. `servicio/gestion_trabajos/launcher.py`

- **Dueño**: Marcos
- **RF**: 04, 10, 26, 29, 30
- **ADR**: ADR-002, ADR-008, ADR-009

```python
async def start(self, command: str, args: list[str], job_id: str) -> asyncio.subprocess.Process
async def cancel(self, proc: asyncio.subprocess.Process, grace_seconds: float) -> None
async def stream_output(self, proc, stdout_path: str, stderr_path: str) -> int
```
`start` lanza el trabajo en su propio grupo de procesos (`start_new_session=True`) y con `stdin=DEVNULL`. `cancel` señala a todo el grupo con `os.killpg`: SIGTERM, espera `grace_seconds` y, si queda alguien, SIGKILL.

`stream_output` lee stdout y stderr al mismo tiempo y por bloques de bytes, para no bloquear al proceso hijo si llena el buffer de uno mientras nadie lo vacía y para no tener límite de largo de línea.

---

## 9. `servicio/persistencia.py`, `bitacora.py`, `operacion.py`

- **Dueño**: Ángel
- **RF**: 11, 12, 13, 14, 15, 16, 23, 24
- **ADR**: ADR-001, ADR-003, ADR-007, ADR-010, ADR-011, ADR-012

### `persistencia.py`
```python
def __init__(self, db_path: str)
async def save_job(self, job: Job) -> None
async def load_job(self, job_id: str) -> Job | None
async def load_all(self) -> list[Job]
async def find_by_client_request_id(self, client_request_id: str) -> Job | None
```
`save_job` usa `INSERT … ON CONFLICT(id) DO UPDATE`, nunca `INSERT OR REPLACE`, para no borrar filas.

Excepción: `DuplicateClientRequestError` (la tabla tiene una restricción UNIQUE sobre `client_request_id`, como red de seguridad ante dos solicitudes casi simultáneas con el mismo ID).

### `bitacora.py`
```python
def __init__(self, log_path: str)
def log_event(self, job_id: str | None, event: str, detail: str = "") -> None
```

### `operacion.py`
```python
def load_config() -> dict
async def shutdown(job_manager, timeout: float) -> None
async def health_summary(job_manager) -> dict
def check_rate_limit(current_count: int, max_allowed: int) -> bool
```
`health_summary` y `shutdown` usan los métodos de `control.py`: `is_accepting()`, `running_count()`, `queued_count()`, `recent_errors_count()`, `stop_accepting()`, `in_progress_count()`, `cancel_all_running()`. `load_config` termina el proceso con un mensaje claro si una variable es inválida.

---

## 10. `cliente/cli.py`

- **Dueño**: Dylan
- **RF**: 17 (además expone RF-09, 11, 24 y 27)

```python
def _leer_configuracion_conexion() -> tuple[str, int, int]
async def _enviar_solicitud(host: str, port: int, mensaje: dict, max_len: int) -> dict
def main() -> int
```
`main()` es una función normal (no `async`); usa `asyncio.run(_enviar_solicitud(...))` internamente para poder llamar a las funciones `async` de `protocolo.py`. `_leer_configuracion_conexion()` lee sus propias variables de entorno (no importa `servicio.operacion`, para mantener al cliente independiente del paquete del servicio).

Comandos: `submit [--request-id FOLIO] <comando> [args...]`, `status <id>`, `list [--status ESTADO]`, `cancel <id>`, `output <id> [stdout|stderr]` y `health`. Termina con código 0 si hubo éxito y 1 si hubo un error.

---

## 11. `servicio/main.py`

- **Dueño**: Ángel
- **ADR**: ADR-011

```python
async def arrancar() -> None
```
Valida la configuración con `operacion.load_config()`, verifica que el puerto esté libre, arma `persistencia`, `bitacora`, `cola`, `launcher` y `control`, llama a `control.recover_on_startup()` (RF-13) antes de aceptar conexiones, arranca `entrada.main(...)` y espera SIGINT o SIGTERM para llamar a `operacion.shutdown(control, shutdown_timeout)` (RF-15). Si el servidor se detiene solo, registra `SERVICE_ERROR`, cierra y termina con código 1.

---

## 12. Flujo de referencia: enviar un trabajo

`cli.py` → `protocolo.write_message()` → `entrada.handle_client()` → `protocolo.read_message()` → `control.submit()` (con `_submit_lock`: revisar duplicados y capacidad → `persistencia.save_job()` → `cola.enqueue()` → `bitacora.log_event()`) → `control._try_dispatch()` → `launcher.start()` → respuesta de vuelta por el mismo camino.

---

## 13. Configuración

| Variable | Tipo | Por defecto | Válido |
|---|---|---|---|
| `JOBRUNNER_HOST` | str | `127.0.0.1` | — |
| `JOBRUNNER_PORT` | int | `9000` | 1 a 65535 |
| `JOBRUNNER_MAX_CONCURRENCY` | int | `3` | Al menos 1 |
| `JOBRUNNER_MAX_QUEUE` | int | `100` | Al menos 1 |
| `JOBRUNNER_GRACE_SECONDS` | float | `5` | 0 o más |
| `JOBRUNNER_SHUTDOWN_TIMEOUT` | float | `30` | 0 o más |
| `JOBRUNNER_DATA_DIR` | str | `./data` | — |
| `JOBRUNNER_ALLOWED_NETWORKS` | list[str] | `127.0.0.1` | Se lee; se aplica en el Hito 3 |
| `JOBRUNNER_MAX_MESSAGE_BYTES` | int | `1048576` | Al menos 1024 |

---

## 14. Cambios al contrato

Cualquier cambio de firma se coordina con (Equipo, Producto: Angel) y se actualizará aquí antes de implementarse.
