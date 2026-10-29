"""
Punto de arranque real del servicio: arma todos los módulos con la
configuración cargada, recupera el historial (RF-13), pone a entrada.py a
escuchar conexiones, y maneja el cierre controlado (RF-15).

No implementa lógica de negocio propia — es solo el "ensamblador" que conecta
las piezas que los demás construyen. Responsable: Ángel (usa directamente
operacion.py).
"""

import asyncio
import os
import signal
import socket
from contextlib import suppress

from src.servicio import bitacora, entrada, operacion, persistencia
from src.servicio.gestion_trabajos import cola, control, launcher


def _verificar_puerto_libre(host: str, port: int) -> None:
    """
    F14: si el puerto está ocupado, avisar y no arrancar. Se revisa ANTES de
    recuperar el historial, para no lanzar trabajos recuperados en un servicio
    que no va a poder atender a nadie.
    """
    try:
        with socket.create_server((host, port)):
            pass
    except OSError as exc:
        raise SystemExit(
            f"[-] No se puede escuchar en {host}:{port}: {exc.strerror}. "
            "¿Hay otro servicio usando ese puerto? Cambia JOBRUNNER_PORT o detén el otro proceso."
        )


async def arrancar() -> None:
    config = operacion.load_config()
    os.makedirs(config["data_dir"], exist_ok=True)
    os.makedirs(f"{config['data_dir']}/output", exist_ok=True)
    _verificar_puerto_libre(config["host"], config["port"])

    p = persistencia.Persistencia(f"{config['data_dir']}/jobs.db")
    b = bitacora.Bitacora(f"{config['data_dir']}/jobrunner.log")
    c = cola.Cola(max_size=config["max_queue"])
    l = launcher.Launcher()

    ctrl = control.Control(
        cola=c,
        launcher=l,
        persistencia=p,
        bitacora=b,
        max_concurrency=config["max_concurrency"],
        grace_seconds=config["grace_seconds"],
        data_dir=config["data_dir"],
    )

    b.log_event(
        None, "SERVICE_STARTED",
        f"{config['host']}:{config['port']} concurrencia={config['max_concurrency']} "
        f"cola={config['max_queue']} grace={config['grace_seconds']}s "
        f"cierre={config['shutdown_timeout']}s",
    )

    # RF-13: recuperar el historial antes de aceptar conexiones nuevas.
    await ctrl.recover_on_startup()

    server_task = asyncio.create_task(
        entrada.main(
            host=config["host"],
            port=config["port"],
            allowed_networks=config["allowed_networks"],
            job_manager=ctrl,
            max_message_bytes=config["max_message_bytes"],
        )
    )

    # RF-15: cierre controlado con SIGINT (Ctrl+C) o SIGTERM (kill -TERM).
    # Desde F4 los trabajos viven en su propio grupo de procesos, así que
    # Ctrl+C ya no les llega: ambas señales hacen exactamente el mismo cierre.
    loop = asyncio.get_running_loop()
    detener = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, detener.set)

    espera_senal = asyncio.create_task(detener.wait())
    # F14: si el servidor se cae (p. ej. no pudo escuchar), no quedarse dormido.
    hechas, _ = await asyncio.wait(
        {server_task, espera_senal}, return_when=asyncio.FIRST_COMPLETED
    )

    fallo_servidor = server_task in hechas
    if fallo_servidor:
        espera_senal.cancel()
        exc = None if server_task.cancelled() else server_task.exception()
        print(f"[-] El servidor de entrada se detuvo inesperadamente: {exc}")
        b.log_event(None, "SERVICE_ERROR", f"El servidor de entrada se detuvo: {exc}")

    b.log_event(None, "SHUTDOWN_STARTED", "Dejando de aceptar trabajos nuevos")
    await operacion.shutdown(ctrl, 0 if fallo_servidor else config["shutdown_timeout"])

    server_task.cancel()
    with suppress(asyncio.CancelledError, Exception):
        await server_task
    b.log_event(None, "SERVICE_STOPPED", "Cierre completo")

    if fallo_servidor:
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(arrancar())
