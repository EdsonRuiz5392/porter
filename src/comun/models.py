"""
Modelos 

Define las estructuras de datos que representan un trabajo (Job) y los
estados por los que puede pasar durante su ciclo de vida. 

Contrato común -> Usar estas definiciones.

Responsable: Sin responsable único.
(Notificar cualquier cambio) -> (Responsable de producto: Angel)

Detalle en docs/technical-guide/contratos-interfaces.md, sección 4.

"""

from dataclasses import dataclass
from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "QUEUED"        # esperando su turno en la cola
    RUNNING = "RUNNING"      # corriendo ahora mismo como proceso real
    SUCCEEDED = "SUCCEEDED"  # terminó bien (código de salida 0)
    FAILED = "FAILED"        # terminó mal (código distinto de 0, o algo se rompió)
    CANCELED = "CANCELED"    # alguien pidió cancelarlo y se logró


@dataclass
class Job:
    """
    La "ficha" de un trabajo. Cada módulo la lee o la actualiza, pero nadie
    la inventa dos veces: todos usan esta misma forma.
    """
    id: str                               # UUID del trabajo
    command: str                          # comando a ejecutar, ej. "backup.sh"
    args: list[str]                       # argumentos, ej. ["--verbose"]
    status: JobStatus
    client_request_id: str | None = None  # para detectar solicitudes repetidas (ADR-005)
    pid: int | None = None                # PID real, una vez que el proceso arrancó
    submitted_at: str | None = None       # fecha/hora (ISO 8601 UTC) en que llegó
    started_at: str | None = None         # fecha/hora en que empezó a correr
    finished_at: str | None = None        # fecha/hora en que terminó
    exit_code: int | None = None          # código de salida del proceso
    stdout_path: str | None = None        # dónde quedó guardada su salida estándar
    stderr_path: str | None = None        # dónde quedó guardada su salida de error
