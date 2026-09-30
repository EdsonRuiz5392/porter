"""
Quien realmente prende y apaga los procesos del sistema operativo.
Responsable: Marcos.
Ver docs/technical-guide/contratos-interfaces.md, sección 8.
Se apoya en: ADR-002 (IPC con subprocess), ADR-005 (escalamiento SIGTERM -> SIGKILL).
RF que cubre: 04, 10, 26, 29, 30.

Módulo Launcher - Servicio de Gestión de Trabajos
Responsable de la ejecución, supervisión y control del ciclo de vida de procesos hijos.
"""

import os
import sys
import subprocess
import logging
from typing import Dict, Any, Optional, Generator

logger = logging.getLogger("servicio.gestion_trabajos.launcher")


class Launcher:
    """Clase encargada de lanzar, cancelar y transmitir la salida de procesos independientes."""

    def __init__(self, directorio_trabajo: Optional[str] = None):
        self.directorio_trabajo = directorio_trabajo or os.getcwd()
        self._procesos_activos: Dict[str, subprocess.Popen] = {}

    def start(
        self,
        trabajo_id: str,
        comando: list[str],
        env_vars: Optional[Dict[str, str]] = None
    ) -> subprocess.Popen:
        """
        Inicia la ejecución de un trabajo en un proceso hijo independiente.

        Args:
            trabajo_id (str): Identificador único del trabajo a ejecutar.
            comando (list[str]): Lista de argumentos del comando a ejecutar (ej. ['python', 'script.py']).
            env_vars (Optional[Dict[str, str]]): Variables de entorno adicionales para el proceso hijo.

        Returns:
            subprocess.Popen: Objeto del proceso hijo iniciado.
        """
        logger.info(f"Iniciando trabajo '{trabajo_id}': {' '.join(comando)}")
        
        entorno = os.environ.copy()
        if env_vars:
            entorno.update(env_vars)

        proceso = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line-buffered para streaming fluido de logs
            cwd=self.directorio_trabajo,
            env=entorno
        )

        self._procesos_activos[trabajo_id] = proceso
        return proceso

    def cancel(self, trabajo_id: str) -> bool:
        """
        Cancela la ejecución de un trabajo activo por su identificador.

        Args:
            trabajo_id (str): Identificador del trabajo que se desea cancelar.

        Returns:
            bool: True si el proceso fue terminado con éxito, False si no existía o falló.
        """
        proceso = self._procesos_activos.get(trabajo_id)
        if not proceso:
            logger.warning(f"No se encontró un trabajo activo con ID: {trabajo_id}")
            return False

        try:
            logger.info(f"Terminando trabajo '{trabajo_id}' (PID {proceso.pid})")
            proceso.terminate()
            try:
                proceso.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                logger.warning(f"Forzando cierre (kill) del trabajo '{trabajo_id}'")
                proceso.kill()

            self._procesos_activos.pop(trabajo_id, None)
            return True

        except Exception as e:
            logger.error(f"Error al intentar cancelar el trabajo '{trabajo_id}': {e}")
            return False

    def stream_output(self, trabajo_id: str) -> Generator[str, None, None]:
        """
        Transmite en tiempo real (stream) la salida de texto (stdout/stderr) producida por el trabajo.

        Args:
            trabajo_id (str): Identificador del trabajo en ejecución del cual se leerá la salida.

        Yields:
            str: Líneas individuales producidas por el proceso hijo.
        """
        proceso = self._procesos_activos.get(trabajo_id)
        if not proceso or not proceso.stdout:
            logger.warning(f"No hay flujo de salida disponible para el trabajo: {trabajo_id}")
            return

        # Lee línea por línea en tiempo real a medida que el proceso hijo escribe
        for linea in iter(proceso.stdout.readline, ''):
            yield linea

        proceso.stdout.close()
        proceso.wait()
        self._procesos_activos.pop(trabajo_id, None)