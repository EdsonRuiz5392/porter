"""
Configuración, arranque/cierre ordenado, y resumen de salud del servicio.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
RF que cubre: 15, 16, 23, 24.
"""


def load_config() -> dict:
    """
    Lee las variables de entorno (ver contratos-interfaces.md, sección 13):
    JOBRUNNER_HOST, JOBRUNNER_PORT, JOBRUNNER_MAX_CONCURRENCY,
    JOBRUNNER_MAX_QUEUE, JOBRUNNER_GRACE_SECONDS, JOBRUNNER_DATA_DIR,
    JOBRUNNER_ALLOWED_NETWORKS, JOBRUNNER_MAX_MESSAGE_BYTES.

    Regresa un diccionario con esas mismas claves en minúsculas (host, port,
    max_concurrency, max_queue, grace_seconds, data_dir, allowed_networks,
    max_message_bytes), ya convertidas al tipo correcto (números como
    int/float, allowed_networks como lista de textos separando por comas), y
    usando un valor por defecto razonable si la variable no está puesta (ver
    src/.env.example).
    """
    raise NotImplementedError


async def shutdown(job_manager) -> None:
    """
    Cierre controlado del servicio (RF-15):
      1. job_manager.stop_accepting() — desde aquí, cualquier submit() nuevo
         se rechaza.
      2. Esperar (por ejemplo revisando cada tanto en un bucle) hasta que
         job_manager.running_count() llegue a 0 — dejar que los trabajos que
         ya estaban corriendo terminen solos, sin matarlos a la fuerza solo
         por estar cerrando el servicio.
      3. Regresar cuando ya no quede nada corriendo bajo su responsabilidad.
    """
    raise NotImplementedError


async def health_summary(job_manager) -> dict:
    """
    Arma el resumen que espera el mensaje "health_response" del protocolo
    (RF-24), preguntándole directamente a job_manager (no necesita saber cómo
    guarda esos números por dentro):
        {
            "active": job_manager.is_accepting(),
            "running": job_manager.running_count(),
            "queued": job_manager.queued_count(),
            "recent_errors": job_manager.recent_errors_count(),
        }
    """
    raise NotImplementedError


def check_rate_limit(current_count: int, max_allowed: int) -> bool:
    """
    Regresa True si current_count ya alcanzó (o pasó) max_allowed — es decir,
    si aceptar una solicitud más rompería el límite. Se usa para rechazar y
    registrar solicitudes que excedan límites configurados (RF-23).
    """
    raise NotImplementedError
