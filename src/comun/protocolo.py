"""
El idioma compartido entre el cliente y el servicio: cómo se empaca un
mensaje para mandarlo por la red, y cómo se desempaca al recibirlo.
Responsable: Juan.
Ver docs/technical-guide/contratos-interfaces.md, sección 5.
Se apoya en: ADR-004 (framing), ADR-014 (tiempos de espera), ADR-015 (salida por partes).
RF que cubre: 21 (que el framing tolere mensajes que llegan en pedazos).

Avance 3: sigue siendo la versión 1. Los cambios son compatibles hacia atrás
(campos opcionales nuevos y códigos de error nuevos); un cliente del avance 2
sigue funcionando. Ver ADR-015 para la regla de compatibilidad.
"""

import asyncio
import json
import struct

PROTOCOL_VERSION = 1

ERROR_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_QUEUE_FULL = "QUEUE_FULL"
ERROR_NOT_FOUND = "NOT_FOUND"
ERROR_VERSION_UNSUPPORTED = "VERSION_UNSUPPORTED"
ERROR_SERVICE_CLOSING = "SERVICE_CLOSING"
ERROR_INTERNAL = "INTERNAL_ERROR"
# D3: el client_request_id ya se usó con un comando o argumentos distintos.
ERROR_REQUEST_ID_CONFLICT = "REQUEST_ID_CONFLICT"
# Avance 3 (ADR-013 y ADR-014).
ERROR_ACCESS_DENIED = "ACCESS_DENIED"          # la IP del cliente no está en la lista permitida
ERROR_TOO_MANY_CLIENTS = "TOO_MANY_CLIENTS"    # se alcanzó JOBRUNNER_MAX_CLIENTS
ERROR_TIMEOUT = "TIMEOUT"                      # el mensaje no terminó de llegar a tiempo
ERROR_RESPONSE_TOO_LARGE = "RESPONSE_TOO_LARGE"  # la respuesta no cabe en un mensaje

TAMANO_ENCABEZADO = 4


class ProtocolError(Exception):
    """Clase base para cualquier problema al leer o escribir un mensaje."""
    code = ERROR_INVALID_REQUEST


class MessageTooLargeError(ProtocolError):
    """El mensaje anuncia que mide más de lo permitido (protege RNF-14)."""


class InvalidMessageError(ProtocolError):
    """Llegaron bytes, pero no son JSON válido, o no son un objeto (un dict)."""


class MessageTimeoutError(ProtocolError):
    """Empezó a llegar un mensaje pero no se completó a tiempo (ADR-014)."""
    code = ERROR_TIMEOUT


class ClientIdleTimeout(Exception):
    """
    El cliente no mandó nada en JOBRUNNER_IDLE_TIMEOUT segundos. No es un
    error de protocolo: simplemente se cierra la conexión para liberar el lugar.
    """


class ResponseTooLargeError(Exception):
    """La respuesta codificada excede el máximo que el otro lado acepta."""


async def read_message(reader, max_len: int, idle_timeout: float | None = None,
                       message_timeout: float | None = None) -> dict:
    """
    Lee un mensaje del stream con framing explícito (header de 4 bytes,
    network byte order), lo valida contra max_len, y regresa el diccionario.

    idle_timeout: cuánto esperar a que EMPIECE un mensaje (ClientIdleTimeout).
    message_timeout: cuánto esperar a que el cuerpo llegue completo una vez
    leído el encabezado (MessageTimeoutError). Así un cliente que manda el
    encabezado y nunca el cuerpo no retiene la conexión para siempre.
    Con None no hay límite (comportamiento del avance 2).

    Si el cliente se desconecta a la mitad de un mensaje, reader.readexactly()
    lanza asyncio.IncompleteReadError: se deja propagar para que entrada.py
    sepa que fue una desconexión (RF-28), no un mensaje inválido.
    """
    try:
        header = await asyncio.wait_for(reader.readexactly(TAMANO_ENCABEZADO), idle_timeout)
    except asyncio.TimeoutError:
        raise ClientIdleTimeout() from None
    (length,) = struct.unpack("!I", header)

    if length > max_len:
        raise MessageTooLargeError(
            f"El mensaje anuncia {length} bytes, el máximo permitido es {max_len}."
        )

    try:
        payload_bytes = await asyncio.wait_for(reader.readexactly(length), message_timeout)
    except asyncio.TimeoutError:
        raise MessageTimeoutError(
            f"El mensaje no llegó completo en {message_timeout:g} s."
        ) from None
    try:
        mensaje = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidMessageError("El mensaje no es JSON válido.") from exc

    if not isinstance(mensaje, dict):
        raise InvalidMessageError("El mensaje debe ser un objeto JSON (dict).")

    return mensaje


def encode_message(message: dict) -> bytes:
    """Encabezado de 4 bytes con la longitud + el JSON en UTF-8."""
    payload_bytes = json.dumps(message).encode("utf-8")
    return struct.pack("!I", len(payload_bytes)) + payload_bytes


async def write_message(writer, message: dict, timeout: float | None = None,
                        max_len: int | None = None) -> None:
    """
    Empaqueta un diccionario a JSON, antepone el header de 4 bytes con su
    longitud, lo escribe en el stream y espera a que se vacíe el buffer.

    max_len: si la respuesta no cabe, lanza ResponseTooLargeError SIN escribir
    nada, para que quien llama mande un error en su lugar.
    timeout: límite para drain(); un cliente que no lee no retiene al servicio
    (asyncio.TimeoutError).
    """
    datos = encode_message(message)
    if max_len is not None and len(datos) - TAMANO_ENCABEZADO > max_len:
        raise ResponseTooLargeError(
            f"La respuesta mide {len(datos) - TAMANO_ENCABEZADO} bytes y el máximo es {max_len}."
        )
    writer.write(datos)
    await asyncio.wait_for(writer.drain(), timeout)
