"""
Configuración, arranque/cierre ordenado, y resumen de salud del servicio.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
RF que cubre: 15, 16, 23, 24.
"""

import asyncio
import os


def load_config() -> dict:
    """
    Lee las variables de entorno (ver contratos-interfaces.md, sección 13) y
    regresa un diccionario con los valores ya convertidos al tipo correcto.
    """
    allowed_networks_str = os.getenv("JOBRUNNER_ALLOWED_NETWORKS", "127.0.0.1")
    allowed_networks = [net.strip() for net in allowed_networks_str.split(",") if net.strip()]

    return {
        "host": os.getenv("JOBRUNNER_HOST", "127.0.0.1"),
        "port": int(os.getenv("JOBRUNNER_PORT", 9000)),
        "max_concurrency": int(os.getenv("JOBRUNNER_MAX_CONCURRENCY", 3)),
        "max_queue": int(os.getenv("JOBRUNNER_MAX_QUEUE", 100)),
        "grace_seconds": float(os.getenv("JOBRUNNER_GRACE_SECONDS", 5.0)),
        "data_dir": os.getenv("JOBRUNNER_DATA_DIR", "./data"),
        "allowed_networks": allowed_networks,
        "max_message_bytes": int(os.getenv("JOBRUNNER_MAX_MESSAGE_BYTES", 1048576)),
    }


async def shutdown(job_manager) -> None:
    """
    Cierre controlado (RF-15): deja de aceptar trabajos nuevos y espera a que
    los que ya estaban corriendo terminen solos antes de regresar.
    """
    job_manager.stop_accepting()
    while job_manager.running_count() > 0:
        await asyncio.sleep(0.5)


async def health_summary(job_manager) -> dict:
    """Arma el resumen que espera el mensaje "health_response" (RF-24)."""
    return {
        "active": job_manager.is_accepting(),
        "running": job_manager.running_count(),
        "queued": job_manager.queued_count(),
        "recent_errors": job_manager.recent_errors_count(),
    }


def check_rate_limit(current_count: int, max_allowed: int) -> bool:
    """True si current_count ya alcanzó (o pasó) max_allowed (RF-23)."""
    return current_count >= max_allowed
