"""
Configuración, arranque/cierre ordenado, y resumen de salud del servicio.
Responsable: Ángel.
Ver docs/technical-guide/contratos-interfaces.md, sección 9.
RF que cubre: 15, 16, 23, 24.
"""

import asyncio
import os


def _numero(nombre: str, defecto, minimo, maximo=None, tipo=int):
    """Lee una variable numérica y termina con un mensaje claro si es inválida."""
    texto = os.getenv(nombre, str(defecto))
    try:
        valor = tipo(texto)
    except ValueError:
        raise SystemExit(f"[-] Configuración inválida: {nombre}={texto!r} debe ser un número.")
    if valor < minimo or (maximo is not None and valor > maximo):
        rango = f"entre {minimo} y {maximo}" if maximo is not None else f"al menos {minimo}"
        raise SystemExit(f"[-] Configuración inválida: {nombre}={valor} debe ser {rango}.")
    return valor


def load_config() -> dict:
    """
    Lee las variables de entorno (ver contratos-interfaces.md, sección 13) y
    regresa un diccionario con los valores ya convertidos al tipo correcto.
    Si un valor es inválido, el servicio no arranca y dice cuál y por qué.
    """
    allowed_networks_str = os.getenv("JOBRUNNER_ALLOWED_NETWORKS", "127.0.0.1")
    allowed_networks = [net.strip() for net in allowed_networks_str.split(",") if net.strip()]

    return {
        "host": os.getenv("JOBRUNNER_HOST", "127.0.0.1"),
        "port": _numero("JOBRUNNER_PORT", 9000, 1, 65535),
        "max_concurrency": _numero("JOBRUNNER_MAX_CONCURRENCY", 3, 1),
        "max_queue": _numero("JOBRUNNER_MAX_QUEUE", 100, 1),
        "grace_seconds": _numero("JOBRUNNER_GRACE_SECONDS", 5.0, 0, tipo=float),
        "data_dir": os.getenv("JOBRUNNER_DATA_DIR", "./data"),
        "allowed_networks": allowed_networks,
        "max_message_bytes": _numero("JOBRUNNER_MAX_MESSAGE_BYTES", 1048576, 1024),
        "shutdown_timeout": _numero("JOBRUNNER_SHUTDOWN_TIMEOUT", 30.0, 0, tipo=float),
    }


# Margen para que _run_job registre el estado final tras las señales.
_MARGEN_REGISTRO_S = 5.0


async def shutdown(job_manager, timeout: float) -> None:
    """
    Cierre controlado (RF-15, decisión D6):
      1. Deja de aceptar trabajos nuevos (submit responde SERVICE_CLOSING).
      2. Espera hasta `timeout` segundos a que los trabajos en curso terminen solos.
      3. Si alguno sigue, lo cancela con el escalamiento normal
         (SIGTERM -> grace_seconds -> SIGKILL); quedan CANCELED.
      4. Regresa. Los trabajos QUEUED se quedan en la base y corren al reiniciar.
    Tiempo máximo de cierre: timeout + grace_seconds + un margen pequeño.
    """
    job_manager.stop_accepting()
    loop = asyncio.get_running_loop()

    limite = loop.time() + timeout
    while job_manager.in_progress_count() > 0 and loop.time() < limite:
        await asyncio.sleep(0.2)

    if job_manager.in_progress_count() > 0:
        await job_manager.cancel_all_running(
            "Cierre del servicio: se agotó JOBRUNNER_SHUTDOWN_TIMEOUT"
        )
        limite = loop.time() + _MARGEN_REGISTRO_S
        while job_manager.in_progress_count() > 0 and loop.time() < limite:
            await asyncio.sleep(0.1)


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
