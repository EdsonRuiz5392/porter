"""
La puerta del servicio: acepta conexiones, valida acceso de red, y conecta lo
que llega con gestion_trabajos.control (traduciendo mensajes de red a
llamadas de función, y de vuelta).
Responsable: Juan.
Ver docs/technical-guide/contratos-interfaces.md, sección 6.
Se apoya en: ADR-004 (framing/protocolo), ADR-001 (servidor asyncio).
RF que cubre: 18, 19, 20, 21, 22, 28.
"""

import asyncio

from src.comun import protocolo
from src.comun.protocolo import (
    ERROR_INVALID_REQUEST,
    ERROR_NOT_FOUND,
    ERROR_VERSION_UNSUPPORTED,
    ERROR_INTERNAL,
)
from src.servicio import operacion
from src.servicio.gestion_trabajos.control import ControlError


def _error(code: str, message: str) -> dict:
    """Arma un mensaje tipo 'error' con el esquema exacto del protocolo."""
    return {
        "type": "error",
        "version": protocolo.PROTOCOL_VERSION,
        "code": code,
        "message": message,
    }


async def handle_client(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    job_manager,
    max_message_bytes: int,
) -> None:
    """
    Atiende a un cliente mientras la conexión siga abierta: lee un mensaje,
    lo rutea a la función de job_manager (u operacion, para "health") que le
    corresponde, y manda la respuesta. Ninguna solicitud inválida, mensaje
    demasiado grande, o desconexión debe tumbar el servicio (RNF-08).
    """
    try:
        while True:
            try:
                message = await protocolo.read_message(reader, max_message_bytes)
            except (protocolo.ProtocolError, asyncio.IncompleteReadError, ConnectionError):
                break

            if message.get("version") != protocolo.PROTOCOL_VERSION:
                await protocolo.write_message(
                    writer,
                    _error(ERROR_VERSION_UNSUPPORTED, "Versión de protocolo no soportada."),
                )
                continue

            msg_type = message.get("type")

            try:
                if msg_type == "submit":
                    job = await job_manager.submit(
                        command=message.get("command"),
                        args=message.get("args", []),
                        client_request_id=message.get("client_request_id"),
                    )
                    response = {
                        "type": "submit_response",
                        "version": protocolo.PROTOCOL_VERSION,
                        "ok": True,
                        "job_id": job.id,
                        "status": job.status.value,
                    }

                elif msg_type == "status":
                    job = await job_manager.get(message.get("job_id"))
                    if not job:
                        response = _error(ERROR_NOT_FOUND, "Trabajo no encontrado.")
                    else:
                        response = {
                            "type": "status_response",
                            "version": protocolo.PROTOCOL_VERSION,
                            "job": {
                                "id": job.id,
                                "command": job.command,
                                "args": job.args,
                                "status": job.status.value,
                                "client_request_id": job.client_request_id,
                                "pid": job.pid,
                                "submitted_at": job.submitted_at,
                                "started_at": job.started_at,
                                "finished_at": job.finished_at,
                                "exit_code": job.exit_code,
                            },
                        }

                elif msg_type == "list":
                    jobs = await job_manager.list(message.get("status_filter"))
                    response = {
                        "type": "list_response",
                        "version": protocolo.PROTOCOL_VERSION,
                        "jobs": [
                            {
                                "id": j.id,
                                "command": j.command,
                                "status": j.status.value,
                                "exit_code": j.exit_code,
                            }
                            for j in jobs
                        ],
                    }

                elif msg_type == "cancel":
                    resultado = await job_manager.request_cancel(message.get("job_id"))
                    if resultado == "NOT_FOUND":
                        response = _error(ERROR_NOT_FOUND, "Trabajo no encontrado.")
                    else:
                        response = {
                            "type": "cancel_response",
                            "version": protocolo.PROTOCOL_VERSION,
                            "job_id": message.get("job_id"),
                            "result": resultado,
                        }

                elif msg_type == "output":
                    contenido = await job_manager.get_output(
                        message.get("job_id"), message.get("stream", "stdout")
                    )
                    if contenido is None:
                        response = _error(ERROR_NOT_FOUND, "Trabajo no encontrado.")
                    else:
                        response = {
                            "type": "output_response",
                            "version": protocolo.PROTOCOL_VERSION,
                            "job_id": message.get("job_id"),
                            "stream": message.get("stream", "stdout"),
                            "content": contenido,
                        }

                elif msg_type == "health":
                    response = {
                        "type": "health_response",
                        "version": protocolo.PROTOCOL_VERSION,
                        **await operacion.health_summary(job_manager),
                    }

                else:
                    response = _error(ERROR_INVALID_REQUEST, f"Tipo de mensaje desconocido: {msg_type!r}")

            except ControlError as exc:
                response = _error(exc.code, str(exc))
            except Exception as exc:
                response = _error(ERROR_INTERNAL, f"Error interno: {exc}")

            await protocolo.write_message(writer, response)

    finally:
        writer.close()
        await writer.wait_closed()


async def main(
    host: str,
    port: int,
    allowed_networks: list[str],
    job_manager,
    max_message_bytes: int,
) -> None:
    """
    Arranca el servidor TCP asíncrono. (Para Avance 1, allowed_networks no se
    valida todavía — no se requiere operación remota.)
    """

    async def _on_connect(reader, writer):
        await handle_client(reader, writer, job_manager, max_message_bytes)

    server = await asyncio.start_server(_on_connect, host, port)
    addr = server.sockets[0].getsockname()
    print(f"[*] Servidor de entrada activo en {addr}")

    async with server:
        await server.serve_forever()
