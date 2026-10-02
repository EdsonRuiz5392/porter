"""
La memoria del sistema: guarda los trabajos en SQLite para que sobrevivan a
un reinicio del servicio.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
Se apoya en: ADR-003 (SQLite/WAL), ADR-001 (despachar llamadas bloqueantes fuera del loop).
RF que cubre: 12, 13.
"""

import sqlite3
import json
import asyncio
from src.comun.models import Job, JobStatus


class DuplicateClientRequestError(Exception):
    """
    Se lanza cuando se intenta guardar un Job cuyo client_request_id ya le
    pertenece a otro (restricción UNIQUE).
    """
    pass


class Persistencia:
    def __init__(self, db_path: str):
        """
        Abre (o crea) la base de datos SQLite en db_path, activa
        el modo WAL, y crea la tabla "jobs" si no existe.
        """
        self.db_path = db_path
        self._init_db_sync()

    def _init_db_sync(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                command TEXT NOT NULL,
                args TEXT,
                status TEXT NOT NULL,
                exit_code INTEGER,
                pid INTEGER,
                client_request_id TEXT UNIQUE,
                submitted_at TEXT,
                started_at TEXT,
                finished_at TEXT,
                stdout_path TEXT,
                stderr_path TEXT
            )
        """)
        conn.commit()
        conn.close()

    def _execute_sync(self, func, *args):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            res = func(conn, *args)
            conn.commit()
            return res
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    async def save_job(self, job: Job) -> None:
        def _save(conn):
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO jobs 
                    (id, command, args, status, exit_code, pid, client_request_id, submitted_at, started_at, finished_at, stdout_path, stderr_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    job.id,
                    job.command,
                    json.dumps(job.args),
                    job.status.value if hasattr(job.status, 'value') else str(job.status),
                    job.exit_code,
                    job.pid,
                    job.client_request_id,
                    job.submitted_at,
                    job.started_at,
                    job.finished_at,
                    job.stdout_path,
                    job.stderr_path
                ))
            except sqlite3.IntegrityError as e:
                if "UNIQUE constraint failed" in str(e):
                    raise DuplicateClientRequestError("El client_request_id ya está registrado en otro trabajo.")
                raise

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._execute_sync, _save)

    async def load_job(self, job_id: str) -> Job | None:
        def _load(conn):
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            return self._row_to_job(row)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._execute_sync, _load)

    async def load_all(self) -> list[Job]:
        def _load_all(conn):
            rows = conn.execute("SELECT * FROM jobs ORDER BY submitted_at ASC").fetchall()
            return [self._row_to_job(row) for row in rows]

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._execute_sync, _load_all)

    async def find_by_client_request_id(self, client_request_id: str) -> Job | None:
        def _find(conn):
            row = conn.execute("SELECT * FROM jobs WHERE client_request_id = ?", (client_request_id,)).fetchone()
            if not row:
                return None
            return self._row_to_job(row)

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._execute_sync, _find)

    def _row_to_job(self, row) -> Job:
        status_val = row["status"]
        try:
            status = JobStatus(status_val)
        except ValueError:
            status = JobStatus.QUEUED

        return Job(
            id=row["id"],
            command=row["command"],
            args=json.loads(row["args"]) if row["args"] else [],
            status=status,
            exit_code=row["exit_code"],
            pid=row["pid"],
            client_request_id=row["client_request_id"],
            submitted_at=row["submitted_at"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            stdout_path=row["stdout_path"],
            stderr_path=row["stderr_path"]
        )