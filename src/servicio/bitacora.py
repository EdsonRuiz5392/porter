"""
Escribe una línea por cada evento importante, para poder investigar después
qué pasó con un trabajo.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
RF que cubre: 14.
"""


class Bitacora:
    def __init__(self, log_path: str):
        """Guarda en qué archivo se va a escribir cada línea."""
        raise NotImplementedError

    def log_event(self, job_id: str | None, event: str, detail: str = "") -> None:
        """
        Arma una línea con: la fecha y hora exactas (UTC), el ID del trabajo
        (o un guion "-" si el evento no es de ningún trabajo en particular),
        el nombre del evento (por ejemplo "CREATED", "STARTED", "FINISHED",
        "CANCELED", "REJECTED"), y cualquier detalle extra que ayude a
        entender qué pasó, y la agrega al final del archivo de bitácora.
        Debe permitir correlacionar una solicitud con su trabajo (RNF-22).
        """
        raise NotImplementedError
