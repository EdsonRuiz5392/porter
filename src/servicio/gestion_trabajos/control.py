"""
El "cerebro" de los trabajos: decide qué pasa con cada uno y en qué momento,
usando a cola.py, launcher.py y persistencia.py como sus herramientas.
Responsable: Dylan.
Ver docs/technical-guide/contratos-interfaces.md, sección 7.
Se apoya en: ADR-005 (saturación y duplicados), ADR-001 (modelo de concurrencia).
RF que cubre: 01, 02, 03, 05, 06, 07, 08, 09, 17, 25, 27.
"""

import asyncio
import uuid
from datetime import datetime
from src.comun.models import Job, JobStatus


class ControlError(Exception):
    """Clase base para errores de negocio."""
    code = "INTERNAL_ERROR"


class InvalidRequestError(ControlError):
    """La solicitud no tiene sentido, ej. un comando vacío (RF-02)."""
    code = "INVALID_REQUEST"


class QueueFullError(ControlError):
    """La cola ya está llena y no se puede aceptar un trabajo más (RF-25)."""
    code = "QUEUE_FULL"


class ServiceClosingError(ControlError):
    """El servicio está en proceso de apagarse y ya no acepta nada (RF-15)."""
    code = "SERVICE_CLOSING"


class Control:
    def __init__(
        self,
        cola,
        launcher,
        persistencia,
        bitacora,
        max_concurrency: int,
        grace_seconds: float,
    ):
        self.cola = cola
        self.launcher = launcher
        self.persistencia = persistencia
        self.bitacora = bitacora
        self.max_concurrency = max_concurrency
        self.grace_seconds = grace_seconds

        self._running_count = 0
        self._reserved_count = 0
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._accepting = True
        self._recent_errors_count = 0
        self._cancel_requested: set[str] = set()

    async def submit(
        self, command: str, args: list[str], client_request_id: str | None
    ) -> Job:
        if not self._accepting:
            raise ServiceClosingError("El servicio está cerrando y no acepta nuevos trabajos.")

        if not command or not command.strip():
            raise InvalidRequestError("El comando no puede estar vacío.")

        # Verificar duplicados por client_request_id (RF-27)
        if client_request_id:
            existing = await self.persistencia.find_by_client_request_id(client_request_id)
            if existing and existing.status in [JobStatus.QUEUED, JobStatus.RUNNING]:
                return existing

        if self.cola.is_full():
            raise QueueFullError("La cola de trabajos está llena.")

        job_id = str(uuid.uuid4())[:8]
        submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        job = Job(
            id=job_id,
            command=command,
            args=args,
            status=JobStatus.QUEUED,
            client_request_id=client_request_id,
            submitted_at=submitted_at,
            stdout_path=f"data/stdout_{job_id}.log",
            stderr_path=f"data/stderr_{job_id}.log"
        )

        try:
            await self.persistencia.save_job(job)
        except Exception:
            # Manejo de concurrencia en duplicados de base de datos
            if client_request_id:
                existing = await self.persistencia.find_by_client_request_id(client_request_id)
                if existing:
                    return existing
            raise

        self.bitacora.log_event(job_id, "CREATED", f"Comando: {command}")
        self.cola.enqueue(job_id)
        
        # Intentar despacho inmediato
        asyncio.create_task(self._try_dispatch())
        return job

    async def get(self, job_id: str) -> Job | None:
        return await self.persistencia.load_job(job_id)

    async def list(self, status_filter: JobStatus | None = None) -> list[Job]:
        all_jobs = await self.persistencia.load_all()
        if status_filter:
            return [j for j in all_jobs if j.status == status_filter]
        return all_jobs

    async def request_cancel(self, job_id: str) -> str:
        job = await self.persistencia.load_job(job_id)
        if not job:
            return "NOT_FOUND"

        if job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED]:
            return "ALREADY_FINISHED"

        if job.status == JobStatus.QUEUED:
            removed = self.cola.remove(job_id)
            if removed:
                finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                job.status = JobStatus.CANCELED
                job.finished_at = finished_at
                await self.persistencia.save_job(job)
                self.bitacora.log_event(job_id, "CANCELED", "Cancelado desde la cola")
                return "CANCELING"

        if job.status == JobStatus.RUNNING:
            if job_id not in self._cancel_requested:
                self._cancel_requested.add(job_id)
                proc = self._active_processes.get(job_id)
                if proc:
                    asyncio.create_task(self.launcher.cancel(proc, self.grace_seconds))
            return "CANCELING"

        return "ALREADY_FINISHED"

    async def get_output(self, job_id: str, stream: str) -> str | None:
        job = await self.persistencia.load_job(job_id)
        if not job:
            return None

        path = job.stdout_path if stream == "stdout" else job.stderr_path
        if not path:
            return ""

        def _read_file():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return f.read()
            except FileNotFoundError:
                return ""

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _read_file)

    async def mark_running(self, job_id: str, pid: int) -> None:
        job = await self.persistencia.load_job(job_id)
        if job:
            job.status = JobStatus.RUNNING
            job.pid = pid
            job.started_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.persistencia.save_job(job)
            self._reserved_count = max(0, self._reserved_count - 1)
            self._running_count += 1
            self.bitacora.log_event(job_id, "STARTED", f"PID: {pid}")

    async def mark_finished(
        self, job_id: str, exit_code: int | None, status: JobStatus
    ) -> None:
        job = await self.persistencia.load_job(job_id)
        if job:
            job.status = status
            job.exit_code = exit_code
            job.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            await self.persistencia.save_job(job)

            if job_id in self._active_processes:
                del self._active_processes[job_id]
            if job_id in self._cancel_requested:
                self._cancel_requested.remove(job_id)

            if job.status == JobStatus.RUNNING or status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED]:
                # Si llegó a correr, restamos del contador de ejecución activa
                if job.started_at:
                    self._running_count = max(0, self._running_count - 1)

            if status == JobStatus.FAILED:
                self._recent_errors_count += 1

            self.bitacora.log_event(job_id, str(status), f"Exit code: {exit_code}")
            asyncio.create_task(self._try_dispatch())

    async def _try_dispatch(self) -> None:
        while self._accepting:
            available_slots = self.max_concurrency - (self._running_count + self._reserved_count)
            if available_slots <= 0:
                break
            
            # Llamada síncrona a dequeue sin await
            job_id = self.cola.dequeue()
            if not job_id:
                break

            self._reserved_count += 1
            asyncio.create_task(self._run_job(job_id))

    async def _run_job(self, job_id: str) -> None:
        job = await self.persistencia.load_job(job_id)
        if not job:
            self._reserved_count = max(0, self._reserved_count - 1)
            return

        try:
            proc = await self.launcher.start(job.command, job.args, job.id)
            self._active_processes[job_id] = proc
            await self.mark_running(job.id, proc.pid)

            exit_code = await self.launcher.stream_output(proc, job.stdout_path, job.stderr_path)

            if job_id in self._cancel_requested or exit_code == -15 or exit_code == -9:
                final_status = JobStatus.CANCELED
            elif exit_code == 0:
                final_status = JobStatus.SUCCEEDED
            else:
                final_status = JobStatus.FAILED

            await self.mark_finished(job.id, exit_code, final_status)
        except Exception as e:
            self._reserved_count = max(0, self._reserved_count - 1)
            await self.mark_finished(job_id, -1, JobStatus.FAILED)
            self.bitacora.log_event(job_id, "ERROR", str(e))

    async def recover_on_startup(self) -> None:
        all_jobs = await self.persistencia.load_all()
        for job in all_jobs:
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.FAILED
                job.finished_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                job.exit_code = -1
                await self.persistencia.save_job(job)
                self.bitacora.log_event(job.id, "INTERRUPTED", "Interrumpido por reinicio del servicio")
            elif job.status == JobStatus.QUEUED:
                self.cola.enqueue(job.id)
        
        asyncio.create_task(self._try_dispatch())

    def is_accepting(self) -> bool:
        return self._accepting

    def stop_accepting(self) -> None:
        self._accepting = False

    def running_count(self) -> int:
        return self._running_count

    def queued_count(self) -> int:
        return self.cola.size() if hasattr(self.cola, "size") else 0

    def recent_errors_count(self) -> int:
        return self._recent_errors_count