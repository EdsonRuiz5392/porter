"""
La lista de espera de trabajos: quién va antes, quién va después, y hasta
cuántos caben.
Responsable: Dylan.
Ver docs/technical-guide/contratos-interfaces.md, sección 7.
Se apoya en: ADR-005 (decisión de saturación: rechazo inmediato).
RF que cubre: 03, 25.

Nota propia: esta cola solo guarda IDs de trabajo (texto). Los datos completos del
trabajo (Job) viven en persistencia — la cola no necesita saber nada más que
a quién le toca después.
"""

from collections import deque
from typing import Optional


class QueueFullError(Exception):
    """Se intenta meter un trabajo cuando ya no hay espacio (RF-25)."""
    pass


class Cola:
    def __init__(self, max_size: int):
        """
        Guarda cuántos trabajos caben como máximo, y prepara una lista vacía
        donde ir guardando los IDs en el orden en que llegan (una fila
        "FIFO": el primero que entra es el primero que sale).
        """
        self.max_size = max_size
        self._queue: deque[str] = deque()

    def is_full(self) -> bool:
        """True si ya se llegó al máximo permitido."""
        return len(self._queue) >= self.max_size

    async def enqueue(self, job_id: str) -> None:
        """
        Agrega un job_id al final de la fila de forma asíncrona.
        Quien llame a esta función debería haber revisado is_full() antes —
        pero conviene que enqueue() también se proteja a sí misma y lance
        QueueFullError si de todos modos se le pide meter algo sin espacio.
        """
        if self.is_full():
            raise QueueFullError("La cola de trabajos está llena.")
        self._queue.append(job_id)

    async def dequeue(self) -> Optional[str]:
        """
        Saca y regresa el job_id que lleva más tiempo esperando (el primero
        que entró) de forma asíncrona. Si la fila está vacía, regresa None en vez de fallar.
        """
        if len(self._queue) > 0:
            return self._queue.popleft()
        return None

    def remove(self, job_id: str) -> bool:
        """
        Saca un job_id específico de la fila, esté donde esté (no
        necesariamente al frente). Hace falta para cuando alguien cancela un
        trabajo que todavía está QUEUED: si no lo sacamos de aquí, seguiría
        contando como "ocupando espacio en la cola" aunque ya esté cancelado.
        Regresa True si lo encontró y lo quitó, False si ese job_id no estaba
        en la fila.
        """
        try:
            self._queue.remove(job_id)
            return True
        except ValueError:
            return False

    def size(self) -> int:
        """Cuántos trabajos hay esperando en este momento."""
        return len(self._queue)