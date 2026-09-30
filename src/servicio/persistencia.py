"""
La memoria del sistema: guarda los trabajos en SQLite para que sobrevivan a
un reinicio del servicio.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
Se apoya en: ADR-003 (SQLite/WAL), ADR-001 (despachar llamadas bloqueantes fuera del loop).
RF que cubre: 12, 13.

Nota propia: sqlite3 es una librería que bloquea mientras trabaja. Cada
función de aquí abajo debe ejecutar la parte que toca disco con
loop.run_in_executor(None, funcion_sincrona, ...) (o asyncio.to_thread()), para
no congelar el resto del servicio mientras escribe o lee.
"""

from src.comun.models import Job


class DuplicateClientRequestError(Exception):
    """
    Se lanza cuando se intenta guardar un Job cuyo client_request_id ya le
    pertenece a otro. Existe como red de seguridad: aunque control.py ya
    revisa duplicados antes de crear un Job, dos solicitudes casi
    simultáneas con el mismo client_request_id podrían pasar esa revisión
    al mismo tiempo. Por eso la tabla debe tener una restricción UNIQUE
    sobre esa columna (ignorando los que vienen en None), para que sea la
    base de datos —no el código— quien finalmente lo impida.
    """


class Persistencia:
    def __init__(self, db_path: str):
        """
        Abre (o crea, si no existe) la base de datos SQLite en db_path, activa
        el modo WAL (PRAGMA journal_mode=WAL), y crea la tabla "jobs" si no
        existe, incluyendo la restricción UNIQUE sobre client_request_id
        que se explica en DuplicateClientRequestError.
        """
        raise NotImplementedError

    async def save_job(self, job: Job) -> None:
        """
        Guarda un Job completo: si ya existía uno con ese id, actualiza sus
        campos; si no, lo crea. Si el client_request_id que trae ya le
        pertenece a otro Job distinto, debe traducir el error de SQLite en
        DuplicateClientRequestError, para que control.py sepa qué pasó.
        """
        raise NotImplementedError

    async def load_job(self, job_id: str) -> Job | None:
        """Busca por id y regresa el Job reconstruido, o None si no existe."""
        raise NotImplementedError

    async def load_all(self) -> list[Job]:
        """
        Regresa todos los trabajos guardados, en el orden en que se crearon
        (por ejemplo, ordenados por submitted_at). Se usa una sola vez, al
        arrancar el servicio, para recuperar el historial (RF-13) — el orden
        importa porque los que sigan QUEUED se vuelven a formar en ese mismo
        orden.
        """
        raise NotImplementedError

    async def find_by_client_request_id(self, client_request_id: str) -> Job | None:
        """
        Busca si ya existe un trabajo creado con ese mismo client_request_id.
        Es lo que usa control.py para detectar solicitudes duplicadas o
        reenviadas (RF-27).
        """
        raise NotImplementedError
