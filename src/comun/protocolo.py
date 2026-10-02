"""
El idioma compartido entre el cliente y el servicio: cómo se empaca un
mensaje para mandarlo por la red, y cómo se desempaca al recibirlo.
Responsable: Juan.
Ver docs/technical-guide/contratos-interfaces.md, sección 5.
Se apoya en: ADR-004.
RF que cubre: 21 (que el framing tolere mensajes que llegan en pedazos).
"""

import struct
import json

PROTOCOL_VERSION = 1

ERROR_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_QUEUE_FULL = "QUEUE_FULL"
ERROR_NOT_FOUND = "NOT_FOUND"
ERROR_VERSION_UNSUPPORTED = "VERSION_UNSUPPORTED"
ERROR_SERVICE_CLOSING = "SERVICE_CLOSING"
ERROR_INTERNAL = "INTERNAL_ERROR"


class ProtocolError(Exception):
    """Clase base para cualquier problema al leer o escribir un mensaje."""


class MessageTooLargeError(ProtocolError):
    """El mensaje anuncia que mide más de lo permitido (protege RNF-14)."""


class InvalidMessageError(ProtocolError):
    """Llegaron bytes, pero no son JSON válido, o no son un objeto (un dict)."""


async def read_message(reader, max_len: int) -> dict:
    """
    Lee un mensaje del stream con framing explícito (header de 4 bytes,
    network byte order), lo valida contra max_len, y regresa el diccionario.

    Si el cliente se desconecta a la mitad de un mensaje, reader.readexactly()
    lanza por su cuenta asyncio.IncompleteReadError — no hay que detectarlo a
    mano, se deja propagar para que entrada.py sepa que fue una desconexión
    (RF-28), no un mensaje inválido.
    """
    header = await reader.readexactly(4)
    (length,) = struct.unpack("!I", header)

    if length > max_len:
        raise MessageTooLargeError(
            f"El mensaje anuncia {length} bytes, el máximo permitido es {max_len}."
        )

    payload_bytes = await reader.readexactly(length)
    try:
        mensaje = json.loads(payload_bytes.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise InvalidMessageError("El mensaje no es JSON válido.") from exc

    if not isinstance(mensaje, dict):
        raise InvalidMessageError("El mensaje debe ser un objeto JSON (dict).")

    return mensaje


async def write_message(writer, message: dict) -> None:
    """
    Empaqueta un diccionario a JSON, antepone el header de 4 bytes con su
    longitud, lo escribe en el stream y espera a que se vacíe el buffer.
    """
    payload_bytes = json.dumps(message).encode("utf-8")
    header = struct.pack("!I", len(payload_bytes))

    writer.write(header + payload_bytes)
    await writer.drain()
