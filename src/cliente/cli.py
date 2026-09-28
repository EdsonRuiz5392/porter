"""
Interfaz de linea de comandos del cliente. 

Recibe e interpreta los comandos introducidos
por el usuario desde la terminal, por ejemplo:
    python -m src.cliente.cli submit "sleep 5"

Su responsabilidad es convertir los argumentos del comando en una
solicitud válida conforme al protocolo, enviarla al servicio y presentar
la respuesta en un formato comprensible para el usuario.

Responsable: Dylan.
Detalle en docs/technical-guide/contratos-interfaces.md, sección 10.
RF que cubre: 17.
"""

import asyncio
import os
import sys

from src.comun import protocolo


def _leer_configuracion_conexion() -> tuple[str, int, int]:
    """
    Lee las variables de entorno para la conexión con los valores por defecto del proyecto.
    Regresa (host, port, max_message_bytes).
    """
    host = os.getenv("JOBRUNNER_HOST", "127.0.0.1")
    port = int(os.getenv("JOBRUNNER_PORT", 8765))
    max_message_bytes = int(os.getenv("JOBRUNNER_MAX_MESSAGE_BYTES", 1048576)) # 1MB por defecto
    return host, port, max_message_bytes


async def _enviar_solicitud(host: str, port: int, mensaje: dict, max_len: int) -> dict:
    """
    1. Abre la conexión con asyncio.open_connection(host, port).
    2. Manda el mensaje con protocolo.write_message().
    3. Lee la respuesta con protocolo.read_message().
    4. Cierra la conexión.
    5. Regresa la respuesta como diccionario.
    """
    reader, writer = await asyncio.open_connection(host, port)
    try:
        await protocolo.write_message(writer, mensaje)
        respuesta = await protocolo.read_message(reader, max_len)
        return respuesta
    finally:
        writer.close()
        await writer.wait_closed()


def main() -> int:
    """
    Punto de entrada del CLI para procesar argumentos de terminal y comunicarse con el servicio.
    """
    if len(sys.argv) < 2 or sys.argv[1] in ["--help", "-h"]:
        print("Uso: python -m src.cliente.cli <comando> [argumentos]")
        print("Comandos disponibles:")
        print("  submit <comando>     Enviar un nuevo trabajo")
        print("  status <job_id>      Consultar estado de un trabajo")
        print("  list                 Listar todos los trabajos")
        print("  cancel <job_id>      Cancelar un trabajo")
        return 0

    comando = sys.argv[1]
    mensaje = {"version": protocolo.PROTOCOL_VERSION, "type": comando}

    if comando == "submit":
        if len(sys.argv) < 3:
            print("[-] Error: Falta especificar el comando a ejecutar.")
            return 1
        mensaje["command"] = sys.argv[2]
        mensaje["args"] = sys.argv[3:]
        
    elif comando in ["status", "cancel"]:
        if len(sys.argv) < 3:
            print(f"[-] Error: Falta especificar el ID del trabajo para '{comando}'.")
            return 1
        try:
            mensaje["job_id"] = str(sys.argv[2])
        except ValueError:
            print("[-] Error: El ID del trabajo debe ser válido.")
            return 1
            
    elif comando == "list":
        pass # No requiere argumentos adicionales obligatorios
        
    else:
        print(f"[-] Error: Comando desconocido '{comando}'. Usa --help para ver la lista.")
        return 1

    host, port, max_len = _leer_configuracion_conexion()

    try:
        respuesta = asyncio.run(_enviar_solicitud(host, port, mensaje, max_len))
    except Exception as e:
        print(f"[-] Error de conexión con el servicio: {e}")
        return 1

    # Procesar respuesta del servicio
    if respuesta.get("type") == "error":
        print(f"[-] Error del servidor [{respuesta.get('code', 'UNKNOWN')}]: {respuesta.get('message', 'Sin descripción')}")
        return 1

    # Imprimir resultados exitosos según el tipo de respuesta
    if comando == "submit":
        print(f"[+] Trabajo enviado con éxito. ID: {respuesta.get('job_id')} | Estado: {respuesta.get('status')}")
    elif comando == "status":
        job = respuesta.get("job", {})
        print(f"[*] ID: {job.get('id')} | Comando: '{job.get('command')}' | Estado: {job.get('status')} | Exit Code: {job.get('exit_code')}")
    elif comando == "list":
        jobs = respuesta.get("jobs", [])
        print("[*] Trabajos registrados en el sistema:")
        for job in jobs:
            print(f"    ID: {job.get('id')} | Comando: '{job.get('command')}' | Estado: {job.get('status')} | Exit Code: {job.get('exit_code')}")
    elif comando == "cancel":
        print(f"[*] Solicitud de cancelación procesada. ID: {respuesta.get('job_id')} | Resultado: {respuesta.get('result')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())