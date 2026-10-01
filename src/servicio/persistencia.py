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

import asyncio
import json
import sqlite3

from src.comun.models import Job, JobStatus


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
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                args TEXT NOT NULL,
                status TEXT NOT NULL,
                client_request_id TEXT UNIQUE,
                pid INTEGER,
                submitted_at TEXT,
                started_at TEXT,
                finished_at TEXT,
                exit_code INTEGER,
                stdout_path TEXT,
                stderr_path TEXT
            )
            """
        )
        self._conn.commit()

    async def save_job(self, job: Job) -> None:
        """
        Guarda un Job completo: si ya existía uno con ese id, actualiza sus
        campos; si no, lo crea. Si el client_request_id que trae ya le
        pertenece a otro Job distinto, debe traducir el error de SQLite en
        DuplicateClientRequestError, para que control.py sepa qué pasó.
        """
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._save_job_sync, job)

    def _save_job_sync(self, job: Job) -> None:
        """Parte bloqueante de save_job(); corre en un hilo aparte."""
        try:
            self._conn.execute(
                """
                INSERT INTO jobs (
                    id, command, args, status, client_request_id, pid,
                    submitted_at, started_at, finished_at, exit_code,
                    stdout_path, stderr_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    command=excluded.command,
                    args=excluded.args,
                    status=excluded.status,
                    client_request_id=excluded.client_request_id,
                    pid=excluded.pid,
                    submitted_at=excluded.submitted_at,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    exit_code=excluded.exit_code,
                    stdout_path=excluded.stdout_path,
                    stderr_path=excluded.stderr_path
                """,
                (
                    job.id,
                    job.command,
                    json.dumps(job.args),
                    job.status.value,
                    job.client_request_id,
                    job.pid,
                    job.submitted_at,
                    job.started_at,
                    job.finished_at,
                    job.exit_code,
                    job.stdout_path,
                    job.stderr_path,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise DuplicateClientRequestError(
                f"client_request_id {job.client_request_id!r} ya existe"
            ) from exc

    async def load_job(self, job_id: str) -> Job | None:
        """Busca por id y regresa el Job reconstruido, o None si no existe."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._load_job_sync, job_id)

    def _load_job_sync(self, job_id: str) -> Job | None:
        """Parte bloqueante de load_job(); corre en un hilo aparte."""
        row = self._conn.execute(
            "SELECT * FROM jobs WHERE id = ?", (job_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_job(row)

    def _row_to_job(self, row: sqlite3.Row) -> Job:
        """Convierte una fila de la tabla de vuelta a un objeto Job."""
        return Job(
            id=row["id"],
            command=row["command"],
            args=json.loads(row["args"]),
            status=JobStatus(row["status"]),
            client_request_id=row["client_request_id"],
            pid=row["pid"],
            submitted_at=row["submitted_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            exit_code=row["exit_code"],
            stdout_path=row["stdout_path"],
            stderr_path=row["stderr_path"],
        )

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