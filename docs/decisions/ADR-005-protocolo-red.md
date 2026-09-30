# ADR-004: Formato y framing del protocolo de red (Python)

- Estado:Propuesto
- Fecha: 2026-09-25
- Requisitos relacionados: RF-18, RF-21, RF-22, RNF-14, RNF-24, RNF-32

## Contexto y problema
El cliente CLI remoto habla con el servicio por socket TCP. El protocolo debe delimitar mensajes correctamente ante lecturas/escrituras parciales y fragmentación (RF-21, RNF-24), validar longitud/formato (RNF-14), y declarar compatibilidad de versión (RNF-32). En Python conviene apoyarse en `asyncio.StreamReader`, que ya maneja acumulación de buffer.

## Alternativas consideradas

### Alternativa A: Mensajes de texto delimitados por línea (`\n`) con `json.dumps`/`json.loads`
- Descripción: cada mensaje es una línea JSON; con `asyncio.StreamReader.readline()` el propio stream se encarga de acumular bytes hasta encontrar el `\n`.
- Ventajas: muy fácil de depurar (se puede probar con `nc`/`telnet`); `readline()` ya resuelve gran parte del framing sin código adicional; simple de versionar agregando un campo `"version"` al JSON.
- Desventajas/riesgos: si el payload (p. ej. stdout de un job) contiene saltos de línea, hay que escaparlo dentro del JSON (el propio `json.dumps` ya escapa `\n` como `\\n`, así que es manejable, pero hay que ser explícitos en la guía técnica); `readline()` sin límite puede consumir memoria si un cliente malicioso no envía nunca `\n` — mitigar con el parámetro `limit` de `asyncio.StreamReader`.

### Alternativa B: Framing binario con longitud prefijada usando `struct.pack('!I', len(payload))` + `asyncio.StreamReader.readexactly(n)`
- Descripción: cada mensaje empieza con 4 bytes de longitud en network byte order (`struct`), seguidos del payload JSON codificado en UTF-8. `readexactly(n)` de `asyncio` ya maneja la espera hasta tener exactamente `n` bytes o lanza `IncompleteReadError` si la conexión se cierra a medias.
- Ventajas: framing robusto sin depender del contenido; `readexactly()` resuelve directamente el problema de lecturas parciales (RF-21) con una sola llamada; permite rechazar mensajes con longitud fuera de un máximo antes de leerlos completos (protege RNF-14 contra agotamiento de memoria).
- Desventajas/riesgos: menos fácil de probar a mano con herramientas de texto simples; requiere manejar `struct.error`/`IncompleteReadError` explícitamente.

## Decisión
 **Alternativa B**, usando `struct` para el prefijo de longitud y JSON como payload interno (combina el framing robusto de B con la legibilidad de A una vez extraído el payload). El campo `"version"` va dentro del JSON y se rechaza explícitamente si no es compatible (RNF-32), cerrando la conexión con un mensaje de error claro.

## Consecuencias
- Positivas: robusto ante fragmentación gracias a `readexactly()`; el límite de longitud protege contra solicitudes maliciosas o mal formadas sin escribir un parser de texto a mano.
- Negativas: depuración manual requiere una herramienta pequeña (o el propio cliente CLI) en vez de `nc` directo.
- Riesgos y mitigación: longitud corrupta o excesiva → validar contra un máximo configurable antes de llamar a `readexactly()`, y cerrar la conexión con un error explícito sin tumbar el servicio (RNF-08).

## Evidencia / prototipo
Prueba enviando el mensaje fragmentado byte a byte (simulando `asyncio.sleep` entre envíos parciales) y verificando reensamblado correcto con `readexactly()`; prueba enviando una longitud absurda y verificando rechazo controlado (TC-012, TC-023).
