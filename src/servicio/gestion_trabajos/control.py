"""
El "cerebro" de los trabajos: decide qué pasa con cada uno y en qué momento,
usando a cola.py, launcher.py y persistencia.py como sus herramientas.
Responsable: Dylan.
Ver docs/technical-guide/contratos-interfaces.md, sección 7.
Se apoya en: ADR-005 (saturación y duplicados), ADR-001 (modelo de concurrencia).
RF que cubre: 01, 02, 03, 05, 06, 07, 08, 09, 17, 25, 27.
"""

import asyncio
import os
import signal
import uuid
from datetime import datetime, timezone
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


class RequestIdConflictError(ControlError):
    """D3: el client_request_id ya pertenece a un trabajo con otro comando (RF-27)."""
    code = "REQUEST_ID_CONFLICT"


# Límites de tamaño de una solicitud (RF-02, RNF-14).
MAX_COMMAND_LEN = 4096
MAX_ARGS = 1000
MAX_ARGS_TOTAL_LEN = 65536
MAX_REQUEST_ID_LEN = 128


def _timestamp_utc() -> str:
    """Fecha/hora actual en UTC, formato ISO 8601 (ej. 2026-09-30T18:04:12.123456+00:00)."""
    return datetime.now(timezone.utc).isoformat()


def _proceso_es_nuestro(pid: int, started_at_iso: str) -> bool | None:
    """
    F5: antes de matar un PID guardado en la base, comprobar que sigue siendo
    el mismo proceso (Linux reutiliza los números de PID).
    True  = el proceso con ese PID arrancó a la hora que guardamos: es nuestro.
    False = existe, pero arrancó a otra hora: es de otro programa, no tocar.
    None  = ya no existe ningún proceso con ese PID.
    """
    try:
        with open(f"/proc/{pid}/stat") as f:
            campos = f.read().rsplit(")", 1)[1].split()
        ticks_desde_arranque = int(campos[19])  # campo 22 de /proc/<pid>/stat
        with open("/proc/stat") as f:
            btime = next(int(l.split()[1]) for l in f if l.startswith("btime"))
    except (FileNotFoundError, ProcessLookupError):
        return None
    inicio = btime + ticks_desde_arranque / os.sysconf("SC_CLK_TCK")
    guardado = datetime.fromisoformat(started_at_iso).timestamp()
    return abs(inicio - guardado) < 2.0


class Control:
    def __init__(
        self,
        cola,
        launcher,
        persistencia,
        bitacora,
        max_concurrency: int,
        grace_seconds: float,
        data_dir: str,
    ):
        self.cola = cola
        self.launcher = launcher
        self.persistencia = persistencia
        self.bitacora = bitacora
        self.max_concurrency = max_concurrency
        self.grace_seconds = grace_seconds
        self.data_dir = data_dir

        self._running_count = 0
        self._reserved_count = 0
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._accepting = True
        self._recent_errors_count = 0
        self._cancel_requested: set[str] = set()
        # F1/F7: un solo submit a la vez entre "revisar" y "encolar".
        self._submit_lock = asyncio.Lock()
        # F3: trabajos que ya salieron de la cola y cuyo _run_job sigue vivo
        # (arrancando o corriendo).
        self._en_curso: set[str] = set()

    def _rutas_salida(self, job_id: str) -> tuple[str, str]:
        """
        Arma las rutas de stdout/stderr dentro de data_dir/output/. Esa
        carpeta ya existe para cuando esto se usa (la crea main.py una sola
        vez al arrancar) — aquí solo se arma el texto de la ruta.
        """
        return (
            f"{self.data_dir}/output/{job_id}.stdout.log",
            f"{self.data_dir}/output/{job_id}.stderr.log",
        )

    @staticmethod
    def _validar_envio(command, args, client_request_id) -> list[str]:
        """
        RF-02 / RNF-14: revisa tipos y tamaños antes de tocar nada.
        Regresa args normalizado (None -> lista vacía).
        """
        if not isinstance(command, str) or not command.strip():
            raise InvalidRequestError(
                "El comando no puede estar vacío y debe ser texto. Ejemplo: submit sleep 5"
            )
        if len(command) > MAX_COMMAND_LEN:
            raise InvalidRequestError(f"El comando excede {MAX_COMMAND_LEN} caracteres.")
        if args is None:
            args = []
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise InvalidRequestError("'args' debe ser una lista de textos, ej. [\"-l\", \"/tmp\"].")
        if len(args) > MAX_ARGS or sum(len(a) for a in args) > MAX_ARGS_TOTAL_LEN:
            raise InvalidRequestError(
                f"Demasiados argumentos (máximo {MAX_ARGS} y {MAX_ARGS_TOTAL_LEN} caracteres en total)."
            )
        if client_request_id is not None:
            if not isinstance(client_request_id, str) or not client_request_id.strip():
                raise InvalidRequestError("'client_request_id' debe ser texto no vacío.")
            if len(client_request_id) > MAX_REQUEST_ID_LEN:
                raise InvalidRequestError(f"'client_request_id' excede {MAX_REQUEST_ID_LEN} caracteres.")
        return args

    @staticmethod
    def _validar_job_id(job_id) -> None:
        if not isinstance(job_id, str) or not job_id.strip():
            raise InvalidRequestError("'job_id' debe ser texto no vacío.")

    def _resolver_duplicado(self, existing: Job, command: str, args: list[str],
                            client_request_id: str) -> Job:
        """
        D3 (RF-27): mismo client_request_id y MISMO comando+argumentos = es un
        reintento -> se devuelve el trabajo original (en cualquier estado).
        Mismo client_request_id con OTRO comando = error explícito.
        """
        if existing.command != command or existing.args != args:
            self.bitacora.log_event(
                existing.id, "REQUEST_ID_CONFLICT",
                f"client_request_id={client_request_id} reusado con otro comando: {command}",
            )
            raise RequestIdConflictError(
                f"El client_request_id '{client_request_id}' ya se usó con otro comando "
                f"(trabajo {existing.id}: '{existing.command}'). Usa un client_request_id distinto."
            )
        self.bitacora.log_event(existing.id, "DUPLICATE", f"client_request_id={client_request_id}")
        return existing

    async def submit(
        self, command: str, args: list[str], client_request_id: str | None
    ) -> Job:
        if not self._accepting:
            self.bitacora.log_event(None, "REJECTED", "SERVICE_CLOSING: el servicio está cerrando")
            raise ServiceClosingError("El servicio está cerrando y no acepta nuevos trabajos.")

        args = self._validar_envio(command, args, client_request_id)

        # F1/F7: desde aquí hasta encolar, un submit a la vez.
        async with self._submit_lock:
            # F8/RF-27 (D3): ver _resolver_duplicado.
            if client_request_id:
                existing = await self.persistencia.find_by_client_request_id(client_request_id)
                if existing:
                    return self._resolver_duplicado(existing, command, args, client_request_id)

            if self.cola.is_full():
                self.bitacora.log_event(None, "REJECTED", f"QUEUE_FULL: cola llena ({self.cola.size()}/{self.cola.max_size})")
                raise QueueFullError("La cola de trabajos está llena.")

            job_id = str(uuid.uuid4())
            stdout_path, stderr_path = self._rutas_salida(job_id)

            job = Job(
                id=job_id,
                command=command,
                args=args,
                status=JobStatus.QUEUED,
                client_request_id=client_request_id,
                submitted_at=_timestamp_utc(),
                stdout_path=stdout_path,
                stderr_path=stderr_path,
            )

            try:
                await self.persistencia.save_job(job)
            except Exception:
                # Red de seguridad: la restricción UNIQUE de la base (F8).
                if client_request_id:
                    existing = await self.persistencia.find_by_client_request_id(client_request_id)
                    if existing:
                        return self._resolver_duplicado(existing, command, args, client_request_id)
                raise

            # Encolar justo después de guardar; la bitácora al final.
            self.cola.enqueue(job_id)
            self.bitacora.log_event(job_id, "CREATED", f"Comando: {command}")

        asyncio.create_task(self._try_dispatch())
        return job

    async def get(self, job_id: str) -> Job | None:
        self._validar_job_id(job_id)
        return await self.persistencia.load_job(job_id)

    async def list(self, status_filter: JobStatus | None = None) -> list[Job]:
        if status_filter is not None:
            try:
                status_filter = JobStatus(status_filter)
            except ValueError:
                validos = ", ".join(s.value for s in JobStatus)
                raise InvalidRequestError(f"Estado desconocido: {status_filter!r}. Usa uno de: {validos}.")
        all_jobs = await self.persistencia.load_all()
        if status_filter:
            return [j for j in all_jobs if j.status == status_filter]
        return all_jobs

    async def request_cancel(self, job_id: str) -> str:
        self._validar_job_id(job_id)
        job = await self.persistencia.load_job(job_id)
        if not job:
            return "NOT_FOUND"

        if job.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED):
            return "ALREADY_FINISHED"

        self.bitacora.log_event(job_id, "CANCEL_REQUESTED", f"estado al pedirlo: {job.status.value}")

        # Caso 1: sigue esperando en la cola -> se cancela ahí mismo.
        if self.cola.remove(job_id):
            job.status = JobStatus.CANCELED
            job.finished_at = _timestamp_utc()
            await self.persistencia.save_job(job)
            self.bitacora.log_event(job_id, "CANCELED", "Cancelado desde la cola")
            return "CANCELING"

        # Caso 2 (F3): ya salió de la cola (arrancando o corriendo).
        if job_id in self._en_curso:
            if job_id not in self._cancel_requested:
                self._cancel_requested.add(job_id)
                proc = self._active_processes.get(job_id)
                if proc:
                    asyncio.create_task(self.launcher.cancel(proc, self.grace_seconds))
                # Si aún no hay proceso, _run_job revisa _cancel_requested.
            return "CANCELING"

        return "ALREADY_FINISHED"

    async def get_output(self, job_id: str, stream: str) -> str | None:
        self._validar_job_id(job_id)
        if stream not in ("stdout", "stderr"):
            raise InvalidRequestError("'stream' debe ser \"stdout\" o \"stderr\".")
        job = await self.persistencia.load_job(job_id)
        if not job:
            return None

        path = job.stdout_path if stream == "stdout" else job.stderr_path
        if not path:
            return ""

        def _read_file():
            try:
                # F6: la salida se guarda como bytes; bytes inválidos -> "�".
                with open(path, "r", encoding="utf-8", errors="replace") as f:
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
            job.started_at = _timestamp_utc()
            await self.persistencia.save_job(job)
            self._reserved_count = max(0, self._reserved_count - 1)
            self._running_count += 1
            self.bitacora.log_event(job_id, "STARTED", f"PID: {pid}")

    async def mark_finished(
        self, job_id: str, exit_code: int | None, status: JobStatus
    ) -> None:
        job = await self.persistencia.load_job(job_id)
        if job:
            ya_habia_arrancado = job.started_at is not None

            job.status = status
            job.exit_code = exit_code
            job.finished_at = _timestamp_utc()
            await self.persistencia.save_job(job)

            self._active_processes.pop(job_id, None)
            self._cancel_requested.discard(job_id)
            self._en_curso.discard(job_id)

            if ya_habia_arrancado:
                self._running_count = max(0, self._running_count - 1)

            if status == JobStatus.FAILED:
                self._recent_errors_count += 1

            self.bitacora.log_event(job_id, status.value, f"Exit code: {exit_code}")
            asyncio.create_task(self._try_dispatch())

    async def _try_dispatch(self) -> None:
        while self._accepting:
            available_slots = self.max_concurrency - (self._running_count + self._reserved_count)
            if available_slots <= 0:
                break

            job_id = self.cola.dequeue()
            if not job_id:
                break

            self._reserved_count += 1
            self._en_curso.add(job_id)
            asyncio.create_task(self._run_job(job_id))

    async def _run_job(self, job_id: str) -> None:
        job = await self.persistencia.load_job(job_id)
        if not job:
            self._reserved_count = max(0, self._reserved_count - 1)
            self._en_curso.discard(job_id)
            return

        # F3, revisión 1: si lo cancelaron mientras salía de la cola, no se lanza.
        if job_id in self._cancel_requested:
            self._reserved_count = max(0, self._reserved_count - 1)
            await self.mark_finished(job_id, None, JobStatus.CANCELED)
            return

        proc = None
        arrancado = False  # F6: la reserva se libera una sola vez
        try:
            proc = await self.launcher.start(job.command, job.args, job.id)
            await self.mark_running(job.id, proc.pid)
            arrancado = True
            # Registrar el proceso y revisar la cancelación sin await de por medio.
            self._active_processes[job_id] = proc
            # F3, revisión 2: la cancelación llegó mientras arrancaba.
            if job_id in self._cancel_requested:
                asyncio.create_task(self.launcher.cancel(proc, self.grace_seconds))

            exit_code = await self.launcher.stream_output(proc, job.stdout_path, job.stderr_path)

            # Decisión: CANCELED solo si alguien lo pidió (RF-29).
            if job_id in self._cancel_requested:
                final_status = JobStatus.CANCELED
            elif exit_code == 0:
                final_status = JobStatus.SUCCEEDED
            else:
                final_status = JobStatus.FAILED
                if exit_code is not None and exit_code < 0:
                    self.bitacora.log_event(
                        job_id, "KILLED_BY_SIGNAL",
                        f"Terminado por la señal {-exit_code} sin que nadie lo cancelara",
                    )

            await self.mark_finished(job.id, exit_code, final_status)
        except Exception as e:
            # F6: si algo falla, no dejar el proceso vivo y sin control.
            if proc is not None and proc.returncode is None:
                try:
                    await self.launcher.cancel(proc, 0)
                except Exception:
                    pass
            if not arrancado:
                self._reserved_count = max(0, self._reserved_count - 1)
            await self.mark_finished(job_id, -1, JobStatus.FAILED)
            self.bitacora.log_event(job_id, "ERROR", str(e))

    def _terminar_grupo_huerfano(self, job: Job) -> None:
        """F5: termina el grupo de procesos de un trabajo que quedó vivo tras una caída."""
        if not job.pid or not job.started_at:
            return
        nuestro = _proceso_es_nuestro(job.pid, job.started_at)
        if nuestro is False:
            self.bitacora.log_event(job.id, "ORPHAN_SKIPPED",
                                    f"PID {job.pid} ahora pertenece a otro proceso; no se toca")
            return
        try:
            # nuestro=True: el líder vive y es nuestro.
            # nuestro=None: el líder murió; si el grupo existe es porque quedan
            # descendientes nuestros (POSIX no reutiliza el ID de un grupo vivo).
            os.killpg(job.pid, signal.SIGKILL)
            self.bitacora.log_event(job.id, "ORPHAN_KILLED", f"Grupo {job.pid} terminado al recuperar")
        except ProcessLookupError:
            pass
        except PermissionError as e:
            self.bitacora.log_event(job.id, "ORPHAN_ERROR", str(e))

    async def recover_on_startup(self) -> None:
        all_jobs = await self.persistencia.load_all()
        for job in all_jobs:
            if job.status == JobStatus.RUNNING:
                self._terminar_grupo_huerfano(job)
                job.status = JobStatus.FAILED
                job.finished_at = _timestamp_utc()
                job.exit_code = -1
                await self.persistencia.save_job(job)
                self.bitacora.log_event(job.id, "INTERRUPTED", "Interrumpido por reinicio del servicio")
            elif job.status == JobStatus.QUEUED:
                # F2: los trabajos ya aceptados vuelven todos, aunque no quepan.
                self.cola.restore(job.id)

        if self.cola.size() > self.cola.max_size:
            self.bitacora.log_event(
                None, "RECOVERY_OVER_CAPACITY",
                f"{self.cola.size()} pendientes recuperados, capacidad {self.cola.max_size}; "
                "no se aceptan nuevos hasta que baje",
            )

        asyncio.create_task(self._try_dispatch())

    async def cancel_all_running(self, motivo: str) -> int:
        """
        D6 (RF-15): usada por el cierre cuando se agota JOBRUNNER_SHUTDOWN_TIMEOUT.
        Cancela con el escalamiento normal (SIGTERM -> grace -> SIGKILL) todo lo
        que siga arrancando o corriendo, y espera a que las señales terminen.
        Los trabajos quedan CANCELED (los terminó el servicio a propósito).
        """
        ids = list(self._en_curso)
        tareas = []
        for job_id in ids:
            self._cancel_requested.add(job_id)
            self.bitacora.log_event(job_id, "CANCEL_REQUESTED", motivo)
            proc = self._active_processes.get(job_id)
            if proc:
                tareas.append(self.launcher.cancel(proc, self.grace_seconds))
            # Si aún no tiene proceso, _run_job ve la cancelación y no lo lanza.
        if tareas:
            await asyncio.gather(*tareas, return_exceptions=True)
        return len(ids)

    def in_progress_count(self) -> int:
        """Trabajos fuera de la cola que siguen vivos (arrancando o corriendo)."""
        return len(self._en_curso)

    def is_accepting(self) -> bool:
        return self._accepting

    def stop_accepting(self) -> None:
        self._accepting = False

    def running_count(self) -> int:
        return self._running_count

    def queued_count(self) -> int:
        return self.cola.size()

    def recent_errors_count(self) -> int:
        return self._recent_errors_count