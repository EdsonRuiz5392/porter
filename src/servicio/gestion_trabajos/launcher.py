"""
Quien realmente prende y apaga los procesos del sistema operativo.
Responsable: Marcos.
Ver docs/technical-guide/contratos-interfaces.md, sección 8.
Se apoya en: ADR-002 (IPC con subprocess), ADR-005 (escalamiento SIGTERM -> SIGKILL),
ADR-008 (grupos de procesos), ADR-016 (marca de entorno por trabajo).
RF que cubre: 04, 10, 26, 29, 30.
"""

import asyncio
import logging
import os
import signal
from typing import List, Optional

logger = logging.getLogger("servicio.gestion_trabajos.launcher")


# ADR-016: cada trabajo nace con esta variable de entorno. Sus hijos y nietos
# la heredan, aunque se salgan del grupo con setsid, así que permite encontrar
# TODOS los procesos de un trabajo leyendo /proc/<pid>/environ, incluso
# después de una caída del servicio en la que no alcanzó a guardarse el PID.
MARCA_ENTORNO = "JOBRUNNER_JOB_ID"


def _leer_stat(pid: str) -> tuple[str, int] | None:
    """(estado, grupo) de un proceso según /proc/<pid>/stat, o None si ya no existe."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            campos = f.read().rsplit(")", 1)[1].split()
        return campos[0], int(campos[2])            # campo 3: estado; campo 5: pgrp
    except (OSError, IndexError, ValueError):
        return None


def _grupo_vivo(pgid: int) -> bool:
    """
    True si todavía existe algún proceso VIVO en el grupo pgid.

    Avance 3 (defecto 9 del vol. 2): os.killpg(pgid, 0) también responde
    "existe" cuando en el grupo solo quedan zombis, y la cancelación esperaba
    la gracia completa sin necesidad. Ahora se revisa /proc ignorando a los
    zombis; si /proc no está disponible se usa la señal 0 como antes.
    """
    try:
        entradas = os.listdir("/proc")
    except OSError:
        try:
            os.killpg(pgid, 0)  # la señal 0 no hace nada: solo pregunta si existe
            return True
        except ProcessLookupError:
            return False
    for d in entradas:
        if d.isdigit():
            info = _leer_stat(d)
            if info and info[1] == pgid and info[0] != "Z":
                return True
    return False


def procesos_del_trabajo(job_id: str) -> list[int]:
    """
    PIDs vivos (no zombis) que llevan la marca de este trabajo. Solo se pueden
    leer los procesos del mismo usuario, que son justo los que el servicio lanzó.
    """
    marca = f"{MARCA_ENTORNO}={job_id}".encode()
    propio = os.getpid()
    pids = []
    try:
        entradas = os.listdir("/proc")
    except OSError:
        return pids
    for d in entradas:
        if not d.isdigit() or int(d) == propio:
            continue
        try:
            with open(f"/proc/{d}/environ", "rb") as f:
                variables = f.read().split(b"\0")
        except OSError:                                  # ya terminó, o es de otro usuario
            continue
        if marca in variables:
            info = _leer_stat(d)
            if info and info[0] != "Z":
                pids.append(int(d))
    return pids


def terminar_por_marca(job_id: str) -> int:
    """SIGKILL a todo proceso con la marca del trabajo. Regresa cuántos encontró."""
    pids = procesos_del_trabajo(job_id)
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    return len(pids)


class Launcher:
    """Encargado del ciclo de vida de procesos hijos de manera asíncrona."""

    async def start(
        self,
        command: str,
        args: List[str],
        job_id: str,
    ) -> asyncio.subprocess.Process:
        """
        Lanza el comando como un proceso hijo completamente separado del
        servicio (RF-04), capturando stdout y stderr por separado.

        F4/F5: start_new_session=True pone al trabajo en su propio grupo de
        procesos (su "familia"), cuyo ID es igual a su PID. Así se puede
        terminar a toda la familia (hijo y nietos) con os.killpg, y el Ctrl+C
        de la terminal del servicio ya no les llega.
        stdin=DEVNULL: el trabajo no hereda la entrada del servicio.
        """
        logger.info(f"[Trabajo {job_id}] Lanzando comando: {command} con args: {args}")

        # ADR-016: la marca nace con el proceso, en el mismo exec: no hay ventana.
        entorno = dict(os.environ)
        entorno[MARCA_ENTORNO] = job_id

        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
            env=entorno,
        )

        logger.info(f"[Trabajo {job_id}] Proceso iniciado con PID {proc.pid}")
        return proc

    async def cancel(
        self,
        proc: asyncio.subprocess.Process,
        grace_seconds: float,
        job_id: str | None = None,
    ) -> None:
        """
        Escalamiento SIGTERM -> SIGKILL (ADR-005), aplicado a todo el grupo
        del trabajo: pide amablemente que termine, espera hasta grace_seconds
        a que muera TODA la familia, y si queda alguien vivo la mata a la fuerza.

        ADR-016: con job_id, al final se buscan también los procesos con la
        marca del trabajo que se hayan salido del grupo (setsid), que antes
        sobrevivían y dejaban al trabajo RUNNING con los pipes abiertos.
        """
        if proc.returncode is not None and not _grupo_vivo(proc.pid):
            logger.info(f"El proceso PID {proc.pid} ya había finalizado con código {proc.returncode}")
            self._barrer_marca(job_id)
            return

        pgid = proc.pid
        try:
            logger.info(f"Enviando SIGTERM al grupo {pgid}. Esperando {grace_seconds}s...")
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            logger.warning(f"El grupo {pgid} ya no existía al intentar cancelarlo")
            self._barrer_marca(job_id)
            return

        loop = asyncio.get_running_loop()
        limite = loop.time() + grace_seconds
        while _grupo_vivo(pgid) and loop.time() < limite:
            await asyncio.sleep(0.1)

        if _grupo_vivo(pgid):
            logger.warning(f"Tiempo de gracia agotado para el grupo {pgid}. Escalando a SIGKILL...")
            try:
                os.killpg(pgid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            logger.info(f"Grupo {pgid} finalizado forzosamente mediante SIGKILL")
        else:
            logger.info(f"Grupo {pgid} finalizó de forma limpia tras SIGTERM")

        self._barrer_marca(job_id)
        await proc.wait()

    @staticmethod
    def _barrer_marca(job_id: str | None) -> None:
        if job_id:
            n = terminar_por_marca(job_id)
            if n:
                logger.warning(f"[Trabajo {job_id}] {n} proceso(s) fuera del grupo terminados por su marca")

    async def stream_output(
        self,
        proc: asyncio.subprocess.Process,
        stdout_path: str,
        stderr_path: str,
    ) -> int:
        """
        Lee stdout y stderr al mismo tiempo (con asyncio.gather, no uno tras
        otro) para no bloquear al proceso hijo si llena el buffer de uno
        mientras nadie lo vacía, y los guarda en archivos separados (RF-11).

        F6: lee por bloques de bytes (no por líneas), así una línea enorme no
        rompe la lectura; flush() hace visible la salida mientras corre.

        No crea carpetas: asume que stdout_path/stderr_path ya están en una
        carpeta que existe (la crea main.py al arrancar), para mantener la
        responsabilidad de este módulo enfocada solo en el proceso.
        """

        async def _escribir_stream(stream: Optional[asyncio.StreamReader], ruta: str):
            if not stream:
                return
            with open(ruta, "wb") as f:
                while True:
                    bloque = await stream.read(65536)
                    if not bloque:
                        break
                    f.write(bloque)
                    f.flush()

        await asyncio.gather(
            _escribir_stream(proc.stdout, stdout_path),
            _escribir_stream(proc.stderr, stderr_path),
        )

        returncode = await proc.wait()
        logger.info(f"Proceso PID {proc.pid} completó stream_output con retorno {returncode}")
        return returncode