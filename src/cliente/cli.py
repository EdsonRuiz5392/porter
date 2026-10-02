"""
Interfaz de línea de comandos del cliente. Traduce lo que la persona escribió
en la terminal a un mensaje del protocolo, lo manda al servicio, y muestra la
respuesta de forma legible, por ejemplo:
    python -m src.cliente.cli submit "sleep 5"
Responsable: Dylan.
Ver docs/technical-guide/contratos-interfaces.md, sección 10.
RF que cubre: 17.
"""

import asyncio
import os
import sys

from src.comun import protocolo


def _leer_configuracion_conexion() -> tuple[str, int, int]:
    """
    El CLI es un programa aparte del servicio, así que lee sus propias
    variables de entorno en vez de importar servicio.operacion. Regresa
    (host, port, max_message_bytes).
    """
    host = os.getenv("JOBRUNNER_HOST", "127.0.0.1")
    port = int(os.getenv("JOBRUNNER_PORT", 9000))
    max_message_bytes = int(os.getenv("JOBRUNNER_MAX_MESSAGE_BYTES", 1048576))
    return host, port, max_message_bytes


async def _enviar_solicitud(host: str, port: int, mensaje: dict, max_len: int) -> dict:
    """Abre la conexión, manda el mensaje, lee la respuesta, y cierra."""
    reader, writer = await asyncio.open_connection(host, port)
    try:
        await protocolo.write_message(writer, mensaje)
        return await protocolo.read_message(reader, max_len)
    finally:
        writer.close()
        await writer.wait_closed()


def main() -> int:
    """Punto de entrada del CLI: lee argumentos, manda la solicitud, muestra la respuesta."""
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("Uso: python -m src.cliente.cli <comando> [argumentos]")
        print("Comandos disponibles:")
        print("  submit <comando> [args...]   Enviar un nuevo trabajo")
        print("  status <job_id>               Consultar estado de un trabajo")
        print("  list                          Listar todos los trabajos")
        print("  cancel <job_id>               Cancelar un trabajo")
        return 0

    comando = sys.argv[1]
    mensaje = {"version": protocolo.PROTOCOL_VERSION, "type": comando}

    if comando == "submit":
        if len(sys.argv) < 3:
            print("[-] Error: falta especificar el comando a ejecutar.")
            return 1
        mensaje["command"] = sys.argv[2]
        mensaje["args"] = sys.argv[3:]

    elif comando in ("status", "cancel"):
        if len(sys.argv) < 3:
            print(f"[-] Error: falta especificar el ID del trabajo para '{comando}'.")
            return 1
        mensaje["job_id"] = sys.argv[2]

    elif comando == "list":
        pass  # no requiere argumentos adicionales

    else:
        print(f"[-] Error: comando desconocido '{comando}'. Usa --help para ver la lista.")
        return 1

    host, port, max_len = _leer_configuracion_conexion()

    try:
        respuesta = asyncio.run(_enviar_solicitud(host, port, mensaje, max_len))
    except (ConnectionError, OSError) as exc:
        print(f"[-] Error de conexión con el servicio: {exc}")
        return 1

    if respuesta.get("type") == "error":
        print(f"[-] Error del servidor [{respuesta.get('code', 'UNKNOWN')}]: {respuesta.get('message', 'sin descripción')}")
        return 1

    if comando == "submit":
        print(f"[+] Trabajo enviado. ID: {respuesta.get('job_id')} | Estado: {respuesta.get('status')}")
    elif comando == "status":
        job = respuesta.get("job", {})
        print(f"[*] ID: {job.get('id')} | Comando: '{job.get('command')}' | Estado: {job.get('status')} | Exit code: {job.get('exit_code')}")
    elif comando == "list":
        jobs = respuesta.get("jobs", [])
        print("[*] Trabajos registrados:")
        for job in jobs:
            print(f"    ID: {job.get('id')} | Comando: '{job.get('command')}' | Estado: {job.get('status')} | Exit code: {job.get('exit_code')}")
    elif comando == "cancel":
        print(f"[*] Cancelación procesada. ID: {respuesta.get('job_id')} | Resultado: {respuesta.get('result')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())