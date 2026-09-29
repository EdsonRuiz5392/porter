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
import time
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple

# Configuración del logger para el módulo
logger = logging.getLogger("servicio.gestion_trabajos.launcher")


class TrabajoResultado:
    """Estructura para almacenar el resultado de la ejecución de un trabajo."""

    def __init__(
        self,
        trabajo_id: str,
        exitoso: bool,
        codigo_salida: Optional[int],
        stdout: str = "",
        stderr: str = "",
        tiempo_ejecucion: float = 0.0,
        error_mensaje: Optional[str] = None,
    ):
        self.trabajo_id = trabajo_id
        self.exitoso = exitoso
        self.codigo_salida = codigo_salida
        self.stdout = stdout
        self.stderr = stderr
        self.tiempo_ejecucion = tiempo_ejecucion
        self.error_mensaje = error_mensaje

    def a_diccionario(self) -> Dict[str, Any]:
        """Convierte el resultado a un diccionario para serialización/IPC."""
        return {
            "trabajo_id": self.trabajo_id,
            "exitoso": self.exitoso,
            "codigo_salida": self.codigo_salida,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "tiempo_ejecucion": round(self.tiempo_ejecucion, 4),
            "error_mensaje": self.error_mensaje,
        }


class Launcher:
    """Clase principal encargada de lanzar y monitorear procesos independientes."""

    def __init__(self, directorio_trabajo: Optional[str] = None):
        self.directorio_trabajo = directorio_trabajo or os.getcwd()
        self._procesos_activos: Dict[str, subprocess.Popen] = {}

    def ejecutar_trabajo(
        self,
        trabajo_id: str,
        comando: list[str],
        env_vars: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> TrabajoResultado:
        """
        Ejecuta un comando en un proceso hijo síncrono/bloqueante con límite de tiempo opcional.
        """
        logger.info(f"Lanzando trabajo ID '{trabajo_id}': {' '.join(comando)}")
        inicio = time.time()

        # Preparar variables de entorno
        entorno = os.environ.copy()
        if env_vars:
            entorno.update(env_vars)

        try:
            proceso = subprocess.Popen(
                comando,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.directorio_trabajo,
                env=entorno,
            )

            # Registrar proceso activo
            self._procesos_activos[trabajo_id] = proceso

            # Esperar a que el proceso termine con manejo de timeout
            stdout, stderr = proceso.communicate(timeout=timeout)
            duracion = time.time() - inicio

            exitoso = proceso.returncode == 0
            logger.info(
                f"Trabajo '{trabajo_id}' finalizado con código {proceso.returncode} en {duracion:.2f}s"
            )

            return TrabajoResultado(
                trabajo_id=trabajo_id,
                exitoso=exitoso,
                codigo_salida=proceso.returncode,
                stdout=stdout,
                stderr=stderr,
                tiempo_ejecucion=duracion,
            )

        except subprocess.TimeoutExpired:
            duracion = time.time() - inicio
            logger.warning(
                f"Trabajo '{trabajo_id}' excedió el tiempo límite de {timeout}s. Cancelando..."
            )
            self.cancelar_trabajo(trabajo_id)

            return TrabajoResultado(
                trabajo_id=trabajo_id,
                exitoso=False,
                codigo_salida=-1,
                tiempo_ejecucion=duracion,
                error_mensaje=f"Excedido el tiempo máximo de ejecución ({timeout}s)",
            )

        except Exception as e:
            duracion = time.time() - inicio
            logger.error(f"Error inesperado al ejecutar el trabajo '{trabajo_id}': {e}")

            return TrabajoResultado(
                trabajo_id=trabajo_id,
                exitoso=False,
                codigo_salida=None,
                tiempo_ejecucion=duracion,
                error_mensaje=str(e),
            )

        finally:
            self._procesos_activos.pop(trabajo_id, None)

    def cancelar_trabajo(self, trabajo_id: str) -> bool:
        """Forza la cancelación de un proceso activo por su ID."""
        proceso = self._procesos_activos.get(trabajo_id)
        if not proceso:
            logger.warning(f"No se encontró proceso activo para cancelar con ID: {trabajo_id}")
            return False

        try:
            logger.info(f"Terminando proceso con PID {proceso.pid} (Trabajo: {trabajo_id})")
            proceso.terminate()
            
            # Dar un margen para cierre limpio antes de forzar kill
            try:
                proceso.wait(timeout=3.0)
            except subprocess.TimeoutExpired:
                logger.warning(f"Forzando cierre (kill) del proceso PID {proceso.pid}")
                proceso.kill()

            return True

        except Exception as e:
            logger.error(f"Error al intentar cancelar el trabajo '{trabajo_id}': {e}")
            return False


# --- BLOQUE DE PRUEBA RÁPIDA DE FUNCIONAMIENTO ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    launcher = Launcher()

    print("\n--- Probando ejecución exitosa ---")
    res_ok = launcher.ejecutar_trabajo(
        trabajo_id="job_test_01",
        comando=[sys.executable, "-c", "print('¡Launcher funcionando correctamente!')"],
    )
    print("Resultado:", res_ok.a_diccionario())

    print("\n--- Probando manejo de Timeout ---")
    res_timeout = launcher.ejecutar_trabajo(
        trabajo_id="job_test_02",
        comando=[sys.executable, "-c", "import time; time.sleep(5)"],
        timeout=1.5,
    )
    print("Resultado Timeout:", res_timeout.a_diccionario())