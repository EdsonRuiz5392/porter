"""
Punto de arranque real del servicio: arma todos los módulos con la
configuración cargada, recupera el historial (RF-13), pone a entrada.py a
escuchar conexiones, y maneja el cierre controlado (RF-15).

No implementa lógica de negocio propia — es solo el "ensamblador" que conecta
las piezas que los demás construyen. Responsable: Angel (usa directamente
operacion.py). 
"""

import asyncio
import os
import signal
from contextlib import suppress

from src.servicio import bitacora, entrada, operacion, persistencia
from src.servicio.gestion_trabajos import cola, control, launcher


async def arrancar() -> None:
    config = operacion.load_config()
    os.makedirs(config["data_dir"], exist_ok=True)
    os.makedirs(f"{config['data_dir']}/output", exist_ok=True)

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

    # RF-15: cierre controlado al recibir Ctrl+C o una señal de terminación,
    # en vez de matar el proceso en seco.
    loop = asyncio.get_running_loop()
    detener = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, detener.set)

    try:
        await detener.wait()
    finally:
        await operacion.shutdown(ctrl)
        server_task.cancel()
        with suppress(asyncio.CancelledError):
            await server_task


if __name__ == "__main__":
    asyncio.run(arrancar())
