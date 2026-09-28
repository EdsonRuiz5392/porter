# Contratos de interfaz — JobRunner

Especificación de qué función expone cada módulo, qué recibe, qué regresa, y qué RF/ADR cubre. Es la referencia fija para implementar.

---

## 1. Propósito

Cada módulo del sistema es responsable de un archivo. Este documento define su interfaz pública (firmas de función) para que los demás módulos puedan usarlo sin conocer su implementación interna.

## 2. Formato de las firmas

Sintaxis Python con type hints. `async def` = corutina, se llama con `await`. `X | None` = el valor puede venir vacío. `self` no cuenta como parámetro real al llamar la función desde afuera.

## 3. Estados válidos

`QUEUED → RUNNING → (SUCCEEDED | FAILED | CANCELED)`, o `QUEUED → CANCELED` directo.

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

Constantes: `ERROR_INVALID_REQUEST`, `ERROR_QUEUE_FULL`, `ERROR_NOT_FOUND`, `ERROR_VERSION_UNSUPPORTED`, `ERROR_SERVICE_CLOSING`, `ERROR_INTERNAL`, `PROTOCOL_VERSION = 1`.

### Esquema de mensajes (`"version": 1` obligatorio en todos)

| type (request) | Campos | type (response) | Campos |
|---|---|---|---|
| `submit` | `command`, `args`, `client_request_id?` | `submit_response` | `ok`, `job_id`, `status` |
| `status` | `job_id` | `status_response` | `job` (objeto Job completo) |
| `list` | `status_filter?` | `list_response` | `jobs` (lista de Job) |
| `cancel` | `job_id` | `cancel_response` | `job_id`, `result` |
| `output` | `job_id`, `stream` (`"stdout"` \| `"stderr"`) | `output_response` | `job_id`, `stream`, `content` |
| `health` | — | `health_response` | `active`, `running`, `queued`, `recent_errors` |
| — | — | `error` | `code`, `message` |

`result` en `cancel_response`: `"CANCELING" | "ALREADY_FINISHED" | "NOT_FOUND"`.

---

## 6. `servicio/entrada.py`

- **Dueño**: Juan
- **RF**: 18, 19, 20, 21, 22, 28
- **ADR**: ADR-001, ADR-004

```python
async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, job_manager, max_message_bytes: int) -> None
async def main(host: str, port: int, allowed_networks: list[str], job_manager, max_message_bytes: int) -> None
```
Traduce cada `type` de mensaje a una función de `control.py` (o de `operacion.py` para `health`), y traduce las excepciones de `control.py` (`InvalidRequestError`, `QueueFullError`, `ServiceClosingError`, etc.) a un mensaje `"error"` con su código correspondiente.

---

## 7. `servicio/gestion_trabajos/cola.py` y `control.py`

- **Dueño**: Dylan
- **RF**: 01, 02, 03, 05, 06, 07, 08, 09, 17, 25, 27
- **ADR**: ADR-001, ADR-005

### `cola.py`
```python
def __init__(self, max_size: int)
def is_full(self) -> bool
def enqueue(self, job_id: str) -> None
def dequeue(self) -> str | None
def remove(self, job_id: str) -> bool
def size(self) -> int
```
Excepción: `QueueFullError`.

### `control.py`
```python
def __init__(self, cola, launcher, persistencia, bitacora, max_concurrency: int, grace_seconds: float)
async def submit(self, command: str, args: list[str], client_request_id: str | None) -> Job
async def get(self, job_id: str) -> Job | None
async def list(self, status_filter: JobStatus | None = None) -> list[Job]
async def request_cancel(self, job_id: str) -> str
async def get_output(self, job_id: str, stream: str) -> str | None
async def mark_running(self, job_id: str, pid: int) -> None
async def mark_finished(self, job_id: str, exit_code: int | None, status: JobStatus) -> None
async def recover_on_startup(self) -> None
def is_accepting(self) -> bool
def stop_accepting(self) -> None
def running_count(self) -> int
def queued_count(self) -> int
def recent_errors_count(self) -> int
```
Excepciones: `ControlError` (base), `InvalidRequestError`, `QueueFullError`, `ServiceClosingError`.

Internamente (no forman parte del contrato público, pero todos los usan): `_try_dispatch()` saca de la cola y arranca trabajos cuando hay lugar; `_run_job(job_id)` corre en segundo plano el ciclo completo de un trabajo.

Nota de responsabilidad: `get_output` apoya RF-11 (Ángel), `request_cancel` apoya RF-10 (Marcos), y `recover_on_startup`/`is_accepting`/`stop_accepting`/`running_count`/`queued_count`/`recent_errors_count` apoyan RF-13/15/23/24 (Ángel). Viven en `control.py` porque necesitan su estado interno, pero la responsabilidad de esos RF sigue siendo de quien los tiene asignados en la tabla del equipo.

---

## 8. `servicio/gestion_trabajos/launcher.py`

- **Dueño**: Marcos
- **RF**: 04, 10, 26, 29, 30
- **ADR**: ADR-002, ADR-005

```python
async def start(self, command: str, args: list[str], job_id: str) -> asyncio.subprocess.Process
async def cancel(self, proc: asyncio.subprocess.Process, grace_seconds: float) -> None
async def stream_output(self, proc, stdout_path: str, stderr_path: str) -> int
```
`stream_output` debe leer stdout y stderr al mismo tiempo (no uno tras otro), para no bloquear al proceso hijo si llena el buffer de uno mientras nadie lo vacía.

---

## 9. `servicio/persistencia.py`, `bitacora.py`, `operacion.py`

- **Dueño**: Ángel
- **RF**: 11, 12, 13, 14, 15, 16, 23, 24
- **ADR**: ADR-003, ADR-001

### `persistencia.py`
```python
def __init__(self, db_path: str)
async def save_job(self, job: Job) -> None
async def load_job(self, job_id: str) -> Job | None
async def load_all(self) -> list[Job]
async def find_by_client_request_id(self, client_request_id: str) -> Job | None
```
Excepción: `DuplicateClientRequestError` (la tabla debe tener una restricción UNIQUE sobre `client_request_id`, como red de seguridad ante dos solicitudes casi simultáneas con el mismo ID).

### `bitacora.py`
```python
def __init__(self, log_path: str)
def log_event(self, job_id: str | None, event: str, detail: str = "") -> None
```

### `operacion.py`
```python
def load_config() -> dict
async def shutdown(job_manager) -> None
async def health_summary(job_manager) -> dict
def check_rate_limit(current_count: int, max_allowed: int) -> bool
```
`health_summary` y `shutdown` usan los métodos de `control.py`: `is_accepting()`, `running_count()`, `queued_count()`, `recent_errors_count()`, `stop_accepting()`.

---

## 10. `cliente/cli.py`

- **Dueño**: Dylan
- **RF**: 17

```python
def _leer_configuracion_conexion() -> tuple[str, int, int]
async def _enviar_solicitud(host: str, port: int, mensaje: dict, max_len: int) -> dict
def main() -> int
```
`main()` es una función normal (no `async`); usa `asyncio.run(_enviar_solicitud(...))` internamente para poder llamar a las funciones `async` de `protocolo.py`. `_leer_configuracion_conexion()` lee sus propias variables de entorno (no importa `servicio.operacion`, para mantener al cliente independiente del paquete del servicio).

---

## 11. `servicio/main.py`

- **Ya viene resuelto** — no hay nada que implementar aquí, es la referencia de cómo se conectan todas las piezas.

```python
async def arrancar() -> None
```
Arma `persistencia`, `bitacora`, `cola`, `launcher` y `control` con la configuración de `operacion.load_config()`, llama a `control.recover_on_startup()` (RF-13) antes de aceptar conexiones, arranca `entrada.main(...)`, y espera una señal de apagado para llamar a `operacion.shutdown(control)` (RF-15).

---

## 12. Flujo de referencia: enviar un trabajo

`cli.py` → `protocolo.write_message()` → `entrada.handle_client()` → `protocolo.read_message()` → `control.submit()` → `cola` / `persistencia.save_job()` / `bitacora.log_event()` → `control._try_dispatch()` → `launcher.start()` → respuesta de vuelta por el mismo camino.

---

## 13. Configuración

| Variable | Tipo |
|---|---|
| `JOBRUNNER_HOST` | str |
| `JOBRUNNER_PORT` | int |
| `JOBRUNNER_MAX_CONCURRENCY` | int |
| `JOBRUNNER_MAX_QUEUE` | int |
| `JOBRUNNER_GRACE_SECONDS` | float |
| `JOBRUNNER_DATA_DIR` | str |
| `JOBRUNNER_ALLOWED_NETWORKS` | list[str] |
| `JOBRUNNER_MAX_MESSAGE_BYTES` | int |

---

## 14. Cambios al contrato

Cualquier cambio de firma se coordina con (Equipo, Producto: Angel) y se actualizará aquí antes de implementarse.
