"""
Quien realmente prende y apaga los procesos del sistema operativo.
Responsable: Marcos.
Ver docs/technical-guide/contratos-interfaces.md, sección 8.
Se apoya en: ADR-002 (IPC con subprocess), ADR-005 (escalamiento SIGTERM -> SIGKILL).
RF que cubre: 04, 10, 26, 29, 30.
"""

import asyncio


class Launcher:
    async def start(
        self, command: str, args: list[str], job_id: str
    ) -> asyncio.subprocess.Process:
        """
        Usa asyncio.create_subprocess_exec(command, *args, stdout=PIPE,
        stderr=PIPE) para arrancar el proceso de verdad, como uno completamente
        separado del servicio (RF-04). No usar shell=True: command y args ya
        vienen separados y así se ejecutan directamente, sin pasar por un
        intérprete de comandos de por medio.
        Regresa el objeto Process, que trae el pid real y acceso a lo que el
        proceso vaya imprimiendo.
        """
        raise NotImplementedError

    async def cancel(
        self, proc: asyncio.subprocess.Process, grace_seconds: float
    ) -> None:
        """
        1. Pedir "amablemente" que se detenga: proc.terminate() (SIGTERM).
        2. Esperar hasta grace_seconds con
           await asyncio.wait_for(proc.wait(), timeout=grace_seconds).
        3. Si el tiempo se acaba y sigue vivo (asyncio.TimeoutError), forzarlo
           con proc.kill() (SIGKILL) y esperar de nuevo, esta vez sin límite,
           para asegurarnos de que sí terminó.

        Esta función puede asumir que ya alguien más (control.py) se aseguró
        de no llamarla dos veces para el mismo trabajo al mismo tiempo — aquí
        solo hay que preocuparse por escalar SIGTERM a SIGKILL correctamente.
        """
        raise NotImplementedError

    async def stream_output(
        self, proc: asyncio.subprocess.Process, stdout_path: str, stderr_path: str
    ) -> int:
        """
        Va leyendo lo que el proceso imprime, guardando stdout y stderr en dos
        archivos separados sin mezclarlos (RF-11), y cuando el proceso termina,
        regresa su código de salida.

        Importante: hay que leer stdout y stderr al mismo tiempo (por ejemplo
        con dos tareas de asyncio corriendo en paralelo), no uno completo y
        luego el otro — si un proceso llena el buffer de una de sus dos
        salidas mientras nadie la está leyendo, se queda trabado esperando a
        que alguien la vacíe, y nunca terminaría.

        Un código de salida negativo significa que el proceso murió por una
        señal (por ejemplo, por la cancelación); debe regresarse igual, sin
        tratarlo como un error de este módulo — es información de diagnóstico
        para RF-29.
        """
        raise NotImplementedError
