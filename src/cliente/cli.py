"""
Interfaz de línea de comandos del cliente. Traduce lo que la persona escribió
en la terminal a un mensaje del protocolo, lo manda al servicio, y muestra la
respuesta de forma legible, por ejemplo:
    python -m src.cliente.cli submit sleep 5
(sin comillas alrededor de "sleep 5": el comando y cada argumento van separados)
Responsable: Dylan.
Ver docs/technical-guide/contratos-interfaces.md, sección 10.
RF que cubre: 17 (además expone RF-09, 11, 24 y 27).
"""

import asyncio
import os
import sys

from src.comun import protocolo

AYUDA = """Uso: python -m src.cliente.cli <comando> [argumentos]

Comandos disponibles:
  submit [--request-id FOLIO] <comando> [args...]
                                 Enviar un trabajo. Con --request-id, reenviar el mismo
                                 folio con el mismo comando devuelve el trabajo original
                                 (útil si se cortó la conexión); con otro comando es error.
  status <job_id>                Estado, PID, tiempos y código de salida de un trabajo
  list [--status ESTADO]         Listar trabajos (ESTADO: QUEUED, RUNNING, SUCCEEDED,
                                 FAILED o CANCELED)
  cancel <job_id>                Cancelar un trabajo en cola o en ejecución
  output <job_id> [stdout|stderr]
                                 Ver la salida capturada (stdout por defecto)
  health                         Resumen de salud del servicio

Códigos de salida: 0 = éxito, 1 = error.
Conexión: variables JOBRUNNER_HOST (127.0.0.1) y JOBRUNNER_PORT (9000)."""


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


def _error(texto: str) -> int:
    print(f"[-] Error: {texto}")
    return 1


def _armar_mensaje(argv: list[str]) -> dict | int:
    """Convierte los argumentos de la terminal en el mensaje del protocolo (o un código de error)."""
    comando = argv[0]
    mensaje = {"version": protocolo.PROTOCOL_VERSION, "type": comando}

    if comando == "submit":
        resto = argv[1:]
        # Las opciones del CLI van ANTES del comando; todo lo que sigue al
        # comando se le pasa tal cual al trabajo.
        if resto and resto[0] == "--request-id":
            if len(resto) < 2 or not resto[1].strip():
                return _error("--request-id necesita un valor, ej. --request-id pedido-001.")
            mensaje["client_request_id"] = resto[1]
            resto = resto[2:]
        if not resto:
            return _error("falta especificar el comando a ejecutar. Ej.: submit sleep 5")
        mensaje["command"] = resto[0]
        mensaje["args"] = resto[1:]

    elif comando in ("status", "cancel"):
        if len(argv) < 2:
            return _error(f"falta especificar el ID del trabajo para '{comando}'.")
        mensaje["job_id"] = argv[1]

    elif comando == "output":
        if len(argv) < 2:
            return _error("falta especificar el ID del trabajo para 'output'.")
        mensaje["job_id"] = argv[1]
        mensaje["stream"] = argv[2] if len(argv) > 2 else "stdout"
        if mensaje["stream"] not in ("stdout", "stderr"):
            return _error("el flujo debe ser 'stdout' o 'stderr'.")

    elif comando == "list":
        if len(argv) > 1:
            if argv[1] != "--status" or len(argv) < 3:
                return _error("uso: list [--status ESTADO]")
            mensaje["status_filter"] = argv[2].upper()

    elif comando == "health":
        pass

    else:
        return _error(f"comando desconocido '{comando}'. Usa --help para ver la lista.")

    return mensaje


def _mostrar(comando: str, respuesta: dict) -> None:
    if comando == "submit":
        print(f"[+] Trabajo enviado. ID: {respuesta.get('job_id')} | Estado: {respuesta.get('status')}")
    elif comando == "status":
        job = respuesta.get("job", {})
        print(f"[*] ID: {job.get('id')}")
        print(f"    Comando:   {job.get('command')} {' '.join(job.get('args') or [])}")
        print(f"    Estado:    {job.get('status')} | Exit code: {job.get('exit_code')} | PID: {job.get('pid')}")
        print(f"    Recibido:  {job.get('submitted_at')}")
        print(f"    Inicio:    {job.get('started_at')}")
        print(f"    Fin:       {job.get('finished_at')}")
        if job.get("client_request_id"):
            print(f"    Folio:     {job.get('client_request_id')}")
    elif comando == "list":
        jobs = respuesta.get("jobs", [])
        print(f"[*] Trabajos registrados: {len(jobs)}")
        for job in jobs:
            print(f"    ID: {job.get('id')} | Comando: '{job.get('command')}' | Estado: {job.get('status')} | Exit code: {job.get('exit_code')}")
    elif comando == "cancel":
        print(f"[*] Cancelación procesada. ID: {respuesta.get('job_id')} | Resultado: {respuesta.get('result')}")
    elif comando == "output":
        print(respuesta.get("content", ""), end="")
    elif comando == "health":
        estado = "activo" if respuesta.get("active") else "cerrando"
        print(f"[*] Servicio {estado} | En ejecución: {respuesta.get('running')} | "
              f"En cola: {respuesta.get('queued')} | Errores recientes: {respuesta.get('recent_errors')}")


def main() -> int:
    """Punto de entrada del CLI: lee argumentos, manda la solicitud, muestra la respuesta."""
    argv = sys.argv[1:]
    if not argv or argv[0] in ("--help", "-h"):
        print(AYUDA)
        return 0

    mensaje = _armar_mensaje(argv)
    if isinstance(mensaje, int):
        return mensaje

    host, port, max_len = _leer_configuracion_conexion()

    try:
        respuesta = asyncio.run(_enviar_solicitud(host, port, mensaje, max_len))
    except (ConnectionError, OSError) as exc:
        print(f"[-] Error de conexión con el servicio en {host}:{port}: {exc}")
        print("    ¿Está corriendo? Inícialo con: python3 -m src.servicio.main")
        return 1
    except (protocolo.ProtocolError, asyncio.IncompleteReadError) as exc:
        print(f"[-] Respuesta inválida del servicio: {exc}")
        return 1

    if respuesta.get("type") == "error":
        print(f"[-] Error del servidor [{respuesta.get('code', 'UNKNOWN')}]: {respuesta.get('message', 'sin descripción')}")
        return 1

    _mostrar(mensaje["type"], respuesta)
    return 0


if __name__ == "__main__":
    sys.exit(main())