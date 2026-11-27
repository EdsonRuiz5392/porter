"""
Escribe una línea por cada evento importante, para poder investigar después
qué pasó con un trabajo.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
RF que cubre: 14, 24 (errores recientes).

Avance 3 (ADR-017): además de escribir el archivo, recuerda en memoria los
errores y rechazos de los últimos JOBRUNNER_ERROR_WINDOW segundos, para que
el resumen de salud informe errores *recientes* y no un contador desde el
arranque.

Monitor web: quien quiera ver los eventos en vivo se registra con
add_listener(); cada evento escrito en el archivo se le entrega también.
"""

import time
from collections import deque
from datetime import datetime, timezone

# Eventos que cuentan como "error" en el resumen de salud: fallas del lado del
# servicio o de los trabajos. ERROR no se cuenta porque siempre acompaña a un
# FAILED del mismo trabajo (se contaría dos veces).
# ADR-018: PERSIST_ERROR = no se pudo guardar el resultado final de un trabajo
# en la base; no va acompañado de FAILED, así que sí se cuenta.
EVENTOS_DE_ERROR = frozenset({
    "FAILED", "INTERRUPTED", "INTERNAL_ERROR", "SERVICE_ERROR", "ORPHAN_ERROR",
    "PERSIST_ERROR",
})
# Solicitudes rechazadas: no son fallas del servicio, pero el administrador
# quiere verlas (accesos no autorizados, saturación, mensajes inválidos).
EVENTOS_DE_RECHAZO = frozenset({
    "REJECTED", "ACCESS_DENIED", "CLIENT_REJECTED", "PROTOCOL_ERROR", "REQUEST_ID_CONFLICT",
})
MAX_DETALLE_RECIENTE = 200
MAX_RECIENTES = 1000          # tope de memoria, aunque la ventana sea muy grande


def _limpiar(texto: str) -> str:
    """Una línea por evento: los saltos de línea de un comando no pueden fingir eventos."""
    return str(texto).replace("\r", "\\r").replace("\n", "\\n")


class Bitacora:
    def __init__(self, log_path: str, ventana_errores: float = 900.0):
        """Guarda en qué archivo se va a escribir cada línea."""
        self.log_path = log_path
        self.ventana_errores = ventana_errores
        self._errores: deque = deque(maxlen=MAX_RECIENTES)
        self._rechazos: deque = deque(maxlen=MAX_RECIENTES)
        # Oyentes en vivo (p. ej. el monitor web): cada uno recibe un dict por evento.
        self._listeners: list = []

    def add_listener(self, funcion) -> None:
        """Registra una función que recibirá cada evento en cuanto se escriba."""
        self._listeners.append(funcion)

    def log_event(self, job_id: str | None, event: str, detail: str = "") -> None:
        """
        Arma una línea con la fecha/hora en UTC, formato ISO 8601 (no un
        formato de texto hecho a mano), el ID del trabajo (o "-" si no
        aplica), el evento y el detalle, y la agrega al archivo. Permite
        correlacionar una solicitud con su trabajo (RNF-22).
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        job_part = job_id if job_id else "-"
        detail = _limpiar(detail)
        linea = f"{timestamp} | job={job_part} | {event} | {detail}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(linea)

        registro = (time.monotonic(), timestamp, job_id, event, detail[:MAX_DETALLE_RECIENTE])
        if event in EVENTOS_DE_ERROR:
            self._errores.append(registro)
        elif event in EVENTOS_DE_RECHAZO:
            self._rechazos.append(registro)

        # Aviso en vivo: si un oyente falla, la bitácora NUNCA debe romperse.
        evento = {"ts": timestamp, "job_id": job_id, "event": event, "detail": detail}
        for oyente in self._listeners:
            try:
                oyente(evento)
            except Exception:
                pass

    def _vigentes(self, cola: deque) -> deque:
        limite = time.monotonic() - self.ventana_errores
        while cola and cola[0][0] < limite:
            cola.popleft()
        return cola

    def errores_recientes(self) -> int:
        return len(self._vigentes(self._errores))

    def rechazos_recientes(self) -> int:
        return len(self._vigentes(self._rechazos))

    def ultimos_errores(self, cuantos: int = 5) -> list[dict]:
        """Los errores más recientes dentro de la ventana, del más viejo al más nuevo."""
        vigentes = list(self._vigentes(self._errores))[-cuantos:]
        return [{"at": ts, "job_id": job, "event": ev, "detail": det}
                for _, ts, job, ev, det in vigentes]
