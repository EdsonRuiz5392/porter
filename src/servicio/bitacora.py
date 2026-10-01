"""
Escribe una línea por cada evento importante, para poder investigar después
qué pasó con un trabajo.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
RF que cubre: 14.
"""

from datetime import datetime, timezone


class Bitacora:
    def __init__(self, log_path: str):
        """Guarda en qué archivo se va a escribir cada línea."""
        self.log_path = log_path

    def log_event(self, job_id: str | None, event: str, detail: str = "") -> None:
        """
        Arma una línea con la fecha/hora en UTC, formato ISO 8601 (no un
        formato de texto hecho a mano), el ID del trabajo (o "-" si no
        aplica), el evento y el detalle, y la agrega al archivo. Permite
        correlacionar una solicitud con su trabajo (RNF-22).
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        job_part = job_id if job_id else "-"
        linea = f"{timestamp} | job={job_part} | {event} | {detail}\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(linea)
