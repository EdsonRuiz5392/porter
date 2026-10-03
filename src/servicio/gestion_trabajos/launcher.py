"""
Quien realmente prende y apaga los procesos del sistema operativo.
Responsable: Marcos.
Ver docs/technical-guide/contratos-interfaces.md, sección 8.
Se apoya en: ADR-002 (IPC con subprocess), ADR-005 (escalamiento SIGTERM -> SIGKILL).
RF que cubre: 04, 10, 26, 29, 30.

Módulo Launcher - Servicio de Gestión de Trabajos 02-10-2026
Responsable de lanzar, cancelar y transmitir la salida de procesos independientes
utilizando concurrencia asíncrona con asyncio.
"""

import asyncio
import logging
import os
from typing import List, Optional

logger = logging.getLogger("servicio.gestion_trabajos.launcher")


class Launcher:
    """
    Clase encargada de la gestión del ciclo de vida de procesos hijos de manera asíncrona.
    Conforme a contratos-interfaces.md, ADR-003 (IPC con asyncio) y ADR-006 (SIGTERM -> SIGKILL).
    """

    def __init__(self, directorio_trabajo: Optional[str] = None):
        self.directorio_trabajo = directorio_trabajo or os.getcwd()

    async def start(
        self,
        command: str,
        args: List[str],
        job_id: str
    ) -> asyncio.subprocess.Process:
        """
        Lanza la ejecución asíncrona de un trabajo mediante un proceso hijo.

        Args:
            command (str): Comando ejecutable principal.
            args (List[str]): Lista de argumentos adicionales para el comando.
            job_id (str): Identificador único del trabajo.

        Returns:
            asyncio.subprocess.Process: Instancia del proceso hijo asíncrono.
        """
        logger.info(f"[Trabajo {job_id}] Lanzando comando: {command} con args: {args}")

        # Se inicia el proceso asíncrono canalizando stdout y stderr
        proc = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.directorio_trabajo
        )

        logger.info(f"[Trabajo {job_id}] Proceso iniciado exitosamente con PID {proc.pid}")
        return proc

    async def cancel(
        self,
        proc: asyncio.subprocess.Process,
        grace_seconds: int = 5
    ) -> bool:
        """
        Cancela de manera segura un proceso en ejecución aplicando escalamiento SIGTERM -> SIGKILL
        según lo estipulado en la ADR-006.

        Args:
            proc (asyncio.subprocess.Process): Instancia del proceso a cancelar.
            grace_seconds (int): Segundos de gracia antes de forzar el cierre con SIGKILL.

        Returns:
            bool: True si el proceso finalizó correctamente durante la cancelación.
        """
        if proc.returncode is not None:
            logger.info(f"El proceso PID {proc.pid} ya había finalizado con código {proc.returncode}")
            return True

        try:
            logger.info(f"Enviando SIGTERM al proceso PID {proc.pid}. Esperando {grace_seconds}s...")
            proc.terminate()

            # Esperar el tiempo de gracia especificado
            try:
                await asyncio.wait_for(proc.wait(), timeout=grace_seconds)
                logger.info(f"Proceso PID {proc.pid} finalizó de forma limpia tras SIGTERM")
                return True
            except asyncio.TimeoutError:
                logger.warning(f"Tiempo de gracia agotado para PID {proc.pid}. Escalando a SIGKILL...")
                proc.kill()
                await proc.wait()
                logger.info(f"Proceso PID {proc.pid} finalizado forzosamente mediante SIGKILL")
                return True

        except ProcessLookupError:
            logger.warning(f"El proceso PID {proc.pid} ya no existía al intentar cancelarlo")
            return True
        except Exception as e:
            logger.error(f"Error inesperado al cancelar el proceso PID {proc.pid}: {e}")
            return False

    async def stream_output(
        self,
        proc: asyncio.subprocess.Process,
        stdout_path: str,
        stderr_path: str
    ) -> int:
        """
        Lee de forma concurrente los flujos stdout y stderr del proceso hijo,
        escribe las salidas en sus respectivos archivos en disco y retorna el código de salida.

        Args:
            proc (asyncio.subprocess.Process): Proceso en ejecución.
            stdout_path (str): Ruta del archivo donde se guardará la salida estándar.
            stderr_path (str): Ruta del archivo donde se guardarán los errores.

        Returns:
            int: Código de salida (returncode) del proceso al finalizar.
        """
        # Asegurar la existencia de los directorios de destino
        for path in (stdout_path, stderr_path):
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)

        async def _write_stream(stream: Optional[asyncio.StreamReader], file_path: str):
            if not stream:
                return
            with open(file_path, "w", encoding="utf-8") as f:
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded_line = line.decode("utf-8", errors="replace")
                    f.write(decoded_line)
                    f.flush()

        # Consumir stdout y stderr simultáneamente usando asyncio.gather
        await asyncio.gather(
            _write_stream(proc.stdout, stdout_path),
            _write_stream(proc.stderr, stderr_path)
        )

        # Esperar la finalización total del proceso y obtener su código de retorno
        returncode = await proc.wait()
        logger.info(f"Proceso PID {proc.pid} completó stream_output con retorno {returncode}")
        return returncode