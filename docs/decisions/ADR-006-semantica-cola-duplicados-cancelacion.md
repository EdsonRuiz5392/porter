# ADR-005: Semántica de saturación de cola, duplicados y escalamiento de cancelación (Python)

- Estado: Propuesto
- Fecha: 2026-09-25
- Requisitos relacionados: RF-25, RF-27, RF-30, RNF-29

## Contexto y problema
Tras la lectura del cliente, este exige decidir explícitamente, antes de implementar: qué pasa cuando la cola se satura, cómo se tratan solicitudes duplicadas, y qué hace el sistema si un trabajo no responde a la cancelación normal. Estas decisiones son en gran medida independientes del lenguaje, pero se describen aquí con las primitivas concretas de Python que las implementan.

## Alternativas consideradas

### Alternativa A (saturación): Rechazo inmediato con error explícito cuando `len(cola) >= capacidad_maxima`
- Ventajas: cumple RF-25/RNF-29 de forma directa y simple de probar (TC-016); se implementa con una sola comprobación antes de encolar (`if len(queue) >= max_size: return error`).
- Desventajas: el usuario debe reintentar manualmente.

### Alternativa A2 (saturación): Backpressure con espera acotada (`await asyncio.wait_for(slot_disponible, timeout=N)`) antes de rechazar
- Ventajas: absorbe picos breves de carga.
- Desventajas: complica la prueba (hay que medir tiempos) y puede violar "no bloquear indefinidamente" si el timeout se configura mal.

### Decisión de saturación
**Alternativa A** (rechazo inmediato y explícito), la más verificable y la más segura respecto a "no bloquear indefinidamente".

---

### Alternativa B (duplicados): Sin deduplicación — cada solicitud recibida crea un `uuid.uuid4()` nuevo
- Ventajas: semántica más simple de implementar con `uuid.uuid4()` de la librería estándar.
- Desventajas: un reenvío accidental del cliente (p. ej. por timeout de red) crea trabajos duplicados reales.

### Alternativa B2 (duplicados): Idempotencia vía `client_request_id` opcional en el mensaje — si se repite el mismo ID en una ventana de tiempo, se devuelve el job ya creado (buscado en un `dict` en memoria o con una consulta `SELECT` en SQLite) en vez de crear uno nuevo
- Ventajas: resuelve RF-27 de forma explícita y protege contra RF-28 (desconexión durante solicitud, reintento del cliente).
- Desventajas: el cliente CLI debe generar y enviar ese ID (`uuid.uuid4()` en el propio cliente); algo más de estado a mantener (ventana de deduplicación, p. ej. un `dict` con expiración simple usando timestamps).

### Alternativa B3 (duplicados): Idempotencia vía `client_request_id` obligatorio, generado automáticamente por el CLI — mismo mecanismo de B2, pero el campo es requerido en todo mensaje de envío de trabajo y el servicio rechaza (RF-02) cualquier solicitud que no lo incluya
- Ventajas: un solo comportamiento que implementar y probar (no hay "camino con ID" y "camino sin ID"); toda solicitud queda protegida contra duplicados por igual, sin depender de que el cliente decida incluirlo; el usuario final no nota nada porque el CLI genera el `uuid.uuid4()` de forma transparente en cada llamada.
- Desventajas: cualquier otro cliente que hable el protocolo (no el CLI oficial) debe generar también el ID o su solicitud será rechazada; ligeramente menos flexible que B2.

### Decisión de duplicados
**Alternativa B2**, documentando la ventana de deduplicación (p. ej. mientras el job siga en `QUEUED`/`RUNNING`, verificado con una consulta simple antes de insertar). Se prefiere sobre B3 porque mantiene el protocolo base simple para cualquier cliente que lo implemente (relevante para RF-18 y la verificación cruzada entre equipos, donde otro equipo debe poder hablar el protocolo sin depender de un campo adicional obligatorio), mientras que el propio CLI del equipo puede generar el `client_request_id` de forma transparente para beneficiarse de la deduplicación. Por contraparte el equipo implementará y probará explícitamente ambos caminos: con el campo (TC-018a) y sin él (TC-018b).

---

### Alternativa C (escalamiento de cancelación): `proc.terminate()` (SIGTERM) inmediato, y si el proceso sigue vivo tras un tiempo de gracia configurable, `proc.kill()` (SIGKILL)
- Descripción en Python: con `asyncio.create_subprocess_exec`, se llama `proc.terminate()` y se espera con `await asyncio.wait_for(proc.wait(), timeout=grace_seconds)`; si expira el timeout (`asyncio.TimeoutError`), se llama `proc.kill()` y se espera de nuevo sin timeout.
- Ventajas: patrón estándar en sistemas Unix, expresado de forma directa con las primitivas de `asyncio.subprocess`; verificable con un job que ignora `SIGTERM` (TC-021).
- Desventajas: ninguna relevante; es la práctica establecida.

### Decisión de escalamiento
**Alternativa C**, con `grace_seconds` configurable (por defecto, por ejemplo, 5s) documentado en la guía de configuración.

## Consecuencias
- Positivas: comportamiento predecible y fácil de verificar en los tres casos, expresado con primitivas estándar de Python (`asyncio`, `uuid`, `subprocess`).
- Negativas: la deduplicación agrega un campo opcional al protocolo (coordinar con ADR-004) y estado adicional (ventana de tiempo) a persistir o mantener en memoria; al ser opcional, hay dos comportamientos que probar por separado (TC-018a/TC-018b).
- Riesgos y mitigación: si el cliente reintenta después de que el job ya llegó a un estado final (`SUCCEEDED`/`FAILED`/`CANCELED`), ya no se deduplica y se crea un trabajo nuevo — es el comportamiento esperado dado que la deduplicación es por estado, no por tiempo, y debe quedar probado explícitamente (TC-018a).

## Evidencia / prototipo
TC-016 (rechazo de cola llena), TC-018a (mismo `client_request_id` dos veces → se deduplica) y TC-018b (dos solicitudes idénticas sin `client_request_id` → se crean dos jobs distintos), TC-021 (job que ignora `SIGTERM` con `signal.signal(signal.SIGTERM, signal.SIG_IGN)` en un script de prueba, y se verifica el `SIGKILL` posterior).
