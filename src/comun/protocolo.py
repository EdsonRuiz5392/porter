import struct
import json

async def read_message(reader) -> dict:
    """
    Lee un mensaje del stream con framing explícito (Header de 4 bytes Big-Endian).
    Satisfacen RF-21, RNF-13 y Caso de Prueba TC-012.
    """
    header = await reader.readexactly(4)
    if not header:
        raise ConnectionError("Conexión cerrada abruptamente.")
    
    (length,) = struct.unpack("!I", header)
    payload_bytes = await reader.readexactly(length)
    return json.loads(payload_bytes.decode("utf-8"))

async def write_message(writer, message: dict) -> None:
    """
    Empaqueta un diccionario a JSON, antepone el header de 4 bytes con su longitud 
    y lo escribe en el stream de red.
    Satisfacen RF-21, RNF-13 y Caso de Prueba TC-012.
    """
    payload_bytes = json.dumps(message).encode("utf-8")
    length = len(payload_bytes)
    header = struct.pack("!I", length)
    
    writer.write(header + payload_bytes)
    await writer.drain()
