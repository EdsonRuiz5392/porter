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


class QueueFullError(Exception):
    """Se intenta meter un trabajo cuando ya no hay espacio (RF-25)."""


class Cola:
    def __init__(self, max_size: int):
        """
        Guarda cuántos trabajos caben como máximo, y prepara una lista vacía
        donde ir guardando los IDs en el orden en que llegan (una fila
        "FIFO": el primero que entra es el primero que sale).
        """
        raise NotImplementedError

    def is_full(self) -> bool:
        """True si ya se llegó al máximo permitido."""
        raise NotImplementedError

    def enqueue(self, job_id: str) -> None:
        """
        Agrega un job_id al final de la fila.
        Quien llame a esta función debería haber revisado is_full() antes —
        pero conviene que enqueue() también se proteja a sí misma y lance
        QueueFullError si de todos modos se le pide meter algo sin espacio,
        por si algún día alguien se le olvida checar primero.
        """
        raise NotImplementedError

    def dequeue(self) -> str | None:
        """
        Saca y regresa el job_id que lleva más tiempo esperando (el primero
        que entró). Si la fila está vacía, regresa None en vez de fallar.
        """
        raise NotImplementedError

    def remove(self, job_id: str) -> bool:
        """
        Saca un job_id específico de la fila, esté donde esté (no
        necesariamente al frente). Hace falta para cuando alguien cancela un
        trabajo que todavía está QUEUED: si no lo sacamos de aquí, seguiría
        contando como "ocupando espacio en la cola" aunque ya esté cancelado.
        Regresa True si lo encontró y lo quitó, False si ese job_id no estaba
        en la fila.
        """
        raise NotImplementedError

    def size(self) -> int:
        """Cuántos trabajos hay esperando en este momento."""
        raise NotImplementedError
