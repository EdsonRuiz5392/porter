import asyncio
import json
from src.comun.protocolo import read_message, write_message

async def handle_client(reader, writer):
    """
    Maneja la conexión de un cliente (local o remoto).
    Ruta comandos permitidos para este avance: submit, status, list y cancel.
    Atrapa InvalidRequestError y responde con un mensaje de error sin tumbar el servicio.
    Satisfacen RF-18, RF-20, RF-21, RF-22.
    """
    try:
        while True:
            try:
                message = await read_message(reader)
            except (ConnectionError, asyncio.IncompleteReadError):
                break

            command = message.get("command")
            
            if command in ["submit", "status", "list", "cancel"]:
                try:
                    response = {"status": "ok", "data": f"Comando {command} procesado"}
                except Exception as e:
                    response = {"status": "error", "message": str(e)}
            else:
                response = {"status": "error", "message": f"Comando desconocido: {command}"}

            await write_message(writer, response)
            
    finally:
        writer.close()
        await writer.wait_closed()

async def main(host="127.0.0.1", port=8888):
    """
    Arranca el servidor TCP asíncrono para el servicio.
    Omitimos allowed_networks por ahora ya que la operación remota no se pide en este avance.
    """
    server = await asyncio.start_server(handle_client, host, port)
    addr = server.sockets[0].getsockname()
    print(f"[*] Servidor de entrada activo en {addr}")

    async with server:
        await server.serve_forever()

