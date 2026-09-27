"""
Interfaz de linea de comandos del cliente. 

Recibe e interpreta los comandos introducidos
por el usuario desde la terminal, por ejemplo:
    python -m src.cliente.cli submit backup.sh --full

Su responsabilidad es convertir los argumentos del comando en una
solicitud válida conforme al protocolo, enviarla al servicio y presentar
la respuesta en un formato comprensible para el usuario.

Responsable: Dylan.
Detalle en docs/technical-guide/contratos-interfaces.md, sección 10.
RF que cubre: 17.
"""

import asyncio
import sys

from src.comun import protocolo


def _leer_configuracion_conexion() -> tuple[str, int, int]:
    """
    El CLI es un programa aparte del servicio (corre en su propia terminal, y
    puede incluso estar en otra máquina), así que NO debe importar
    servicio.operacion — eso mezclaría el cliente con el paquete del servicio.
    En vez de eso, esta función lee directamente, con os.getenv(), solo las
    tres cosas que el cliente necesita para conectarse:
      - JOBRUNNER_HOST (a dónde conectarse)
      - JOBRUNNER_PORT (a qué puerto)
      - JOBRUNNER_MAX_MESSAGE_BYTES (el mismo límite que usa el servicio, para
        poder leer su respuesta sin rechazarla por "demasiado grande")
    usando los mismos valores por defecto que trae src/.env.example.
    Regresa (host, port, max_message_bytes).
    """
    raise NotImplementedError


async def _enviar_solicitud(host: str, port: int, mensaje: dict, max_len: int) -> dict:
    """
    La única función de este archivo que es "async" (por eso lleva guion bajo:
    es de uso interno, no forma parte de lo que otros módulos llaman).
    Hace, en orden:
      1. Abrir la conexión con await asyncio.open_connection(host, port).
      2. Mandar el mensaje con protocolo.write_message().
      3. Leer la respuesta con protocolo.read_message().
      4. Cerrar la conexión (writer.close(), await writer.wait_closed()).
      5. Regresar la respuesta ya como diccionario.
    Existe separada de main() porque main() es una función normal —main()
    la llama con asyncio.run(_enviar_solicitud(...)) para poder usar estas
    funciones "async" sin que todo el programa tenga que serlo.
    """
    raise NotImplementedError


def main() -> int:
    """
    El punto de entrada del programa. En orden:
      1. Leer lo que la persona escribió en la terminal (sys.argv). Los
         comandos que debe reconocer son: submit, status, list, cancel,
         output, health.
      2. Si pidió --help, o no escribió suficientes argumentos para el
         comando elegido, mostrar un mensaje de ayuda explicando cómo se usa
         cada comando, y terminar con código 0 (pedir ayuda no es un error).
      3. Armar el diccionario del mensaje que le toca a ese comando —el
         formato exacto de cada uno está en contratos-interfaces.md, sección
         5, tabla de "Esquema de mensajes"—.
      4. Llamar a _leer_configuracion_conexion() para saber a dónde conectarse.
      5. Usar asyncio.run(_enviar_solicitud(host, port, mensaje, max_len)) para
         mandar el mensaje y obtener la respuesta del servicio.
      6. Si la respuesta es de tipo "error", mostrar el mensaje de error de
         forma clara y terminar con un código distinto de 0.
      7. Si la respuesta fue exitosa, mostrarla de forma legible (por ejemplo,
         para "submit_response" mostrar el job_id que le tocó) y terminar con
         código 0.

    Por qué importa el código de salida (RF-17): si alguien usa este CLI
    dentro de un script, necesita poder preguntar "¿salió bien o mal?" sin
    tener que leer el texto que imprimió — el código de salida es justo esa
    respuesta corta que cualquier script puede revisar.
    """
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
