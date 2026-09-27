"""
El idioma compartido entre el cliente y el servicio: cómo se empaca un
mensaje para mandarlo por la red, y cómo se desempaca al recibirlo.

Responsable: Juan.

Detalle en docs/technical-guide/contratos-interfaces.md, sección 5.

Se apoya en: ADR-004.

RF que cubre: 21 (que el framing tolere mensajes que llegan en pedazos).

Cómo viaja un mensaje en el cable: primero 4 bytes que dicen cuánto mide el
mensaje (en network byte order), y después el mensaje mismo en JSON, en UTF-8.
"""

import asyncio
import json
import struct
from typing import Any

LENGTH_PREFIX_FORMAT = "!I"  # entero sin signo de 4 bytes, network byte order
LENGTH_PREFIX_SIZE = struct.calcsize(LENGTH_PREFIX_FORMAT)


class ProtocolError(Exception):
    """Clase base para cualquier problema al leer o escribir un mensaje."""


class MessageTooLargeError(ProtocolError):
    """El mensaje anuncia que mide más de lo permitido (protege RNF-14)."""


class InvalidMessageError(ProtocolError):
    """Llegaron bytes, pero no son JSON válido, o no son un objeto (un dict)."""


async def read_message(reader: asyncio.StreamReader, max_len: int) -> dict[str, Any]:
    """
    Lee un mensaje completo del socket y lo regresa ya como diccionario.

    Pasos a seguir:
      1. Leer exactamente LENGTH_PREFIX_SIZE bytes con reader.readexactly() —
         ahí viene el tamaño del mensaje que sigue.
      2. Decodificar esos bytes a un número con struct.unpack().
      3. Si ese número es mayor que max_len, no seguir leyendo: lanzar
         MessageTooLargeError. Así un mensaje enorme no se intenta cargar
         completo a memoria.
      4. Si el tamaño es aceptable, leer exactamente esa cantidad de bytes con
         reader.readexactly() — esta función ya espera sola a que lleguen
         todos los bytes, aunque lleguen repartidos en varios paquetes.
      5. Decodificar esos bytes como UTF-8 y luego con json.loads().
      6. Verificar que lo que salió sea un diccionario (no una lista, ni un
         número suelto); si no lo es, lanzar InvalidMessageError.

    Si el cliente se desconecta a la mitad de un mensaje, reader.readexactly()
    lanza por su cuenta un asyncio.IncompleteReadError — no hay que armarlo a
    mano, solo dejar que se propague para que entrada.py sepa que fue una
    desconexión y no un mensaje inválido (RF-28).
    """
    raise NotImplementedError


async def write_message(writer: asyncio.StreamWriter, message: dict[str, Any]) -> None:
    """
    Hace lo contrario a read_message: toma un diccionario, lo convierte a
    texto JSON, lo codifica a bytes UTF-8, le pone por delante los 4 bytes con
    su tamaño, escribe todo junto en el writer, y por último hace
    `await writer.drain()` (esto es necesario para no acumular datos sin
    enviar si la red va lenta).
    """
    raise NotImplementedError


# Códigos de error que puede traer un mensaje tipo "error" (ver el esquema
# completo de mensajes en contratos-interfaces.md, sección 5).
ERROR_INVALID_REQUEST = "INVALID_REQUEST"
ERROR_QUEUE_FULL = "QUEUE_FULL"
ERROR_NOT_FOUND = "NOT_FOUND"
ERROR_VERSION_UNSUPPORTED = "VERSION_UNSUPPORTED"
ERROR_SERVICE_CLOSING = "SERVICE_CLOSING"  # el servicio está apagándose (RF-15)
ERROR_INTERNAL = "INTERNAL_ERROR"

PROTOCOL_VERSION = 1
