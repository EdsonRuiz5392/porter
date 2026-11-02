"""
Quien realmente prende y apaga los procesos del sistema operativo.
Responsable: Marcos.
Ver docs/technical-guide/contratos-interfaces.md, sección 8.
Se apoya en: ADR-002 (IPC con subprocess), ADR-005 (escalamiento SIGTERM -> SIGKILL).
RF que cubre: 04, 10, 26, 29, 30.
"""

import asyncio
import logging
import os
import signal
from typing import List, Optional

logger = logging.getLogger("servicio.gestion_trabajos.launcher")


def _grupo_vivo(pgid: int) -> bool:
    """True si todavía existe algún proceso en el grupo pgid."""
    try:
        os.killpg(pgid, 0)  # la señal 0 no hace nada: solo pregunta si existe
        return True
    except ProcessLookupError:
        return False


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

        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )

        logger.info(f"[Trabajo {job_id}] Proceso iniciado con PID {proc.pid}")
        return proc

    async def cancel(
        self,
        proc: asyncio.subprocess.Process,
        grace_seconds: float,
    ) -> None:
        """
        Escalamiento SIGTERM -> SIGKILL (ADR-005), aplicado a todo el grupo
        del trabajo: pide amablemente que termine, espera hasta grace_seconds
        a que muera TODA la familia, y si queda alguien vivo la mata a la fuerza.
        """
        if proc.returncode is not None and not _grupo_vivo(proc.pid):
            logger.info(f"El proceso PID {proc.pid} ya había finalizado con código {proc.returncode}")
            return

        pgid = proc.pid
        try:
            logger.info(f"Enviando SIGTERM al grupo {pgid}. Esperando {grace_seconds}s...")
            os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:
            logger.warning(f"El grupo {pgid} ya no existía al intentar cancelarlo")
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

        await proc.wait()

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
