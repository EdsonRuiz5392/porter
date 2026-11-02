# ADR-002: IPC entre el servicio y los procesos hijos de cada trabajo (Python)

- Estado: Aceptado
- Fecha: 2026-09-21
- Requisitos relacionados: RF-04, RF-07, RF-11, RF-29, RNF-09, RNF-25, RNF-30

## Contexto y problema
Cada trabajo corre en un proceso hijo lanzado por el servicio. Hay que definir cómo, en Python, se captura stdout/stderr por separado (RF-11), se detecta la terminación —normal o inesperada— y se recupera el código de salida (RF-29), y cómo se envían señales de cancelación (RF-10, RF-30).

## Alternativas consideradas

### Alternativa A: `subprocess.Popen` con `stdout=PIPE, stderr=PIPE` y polling con `.poll()` en un hilo dedicado
- Descripción: se lanza el job con `subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)`; un hilo por trabajo (o un hilo central) llama `.poll()` periódicamente y lee de los pipes con `.communicate()` o lectura manual no bloqueante.
- Ventajas: API simple y muy documentada; funciona igual de bien fuera de `asyncio`.
- Desventajas/riesgos: el polling agrega latencia en detectar terminación; leer de dos pipes sin bloquear requiere `select.select()` o hilos separados por descriptor, lo que complica el código; consistente solo si se eligió la Alternativa A (`threading`) en ADR-001.

### Alternativa B: `asyncio.create_subprocess_exec` con `stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE`
- Descripción: el proceso hijo se crea como una corutina; `proc.stdout` y `proc.stderr` son `StreamReader` independientes que se leen con `await stream.readline()` / `await stream.read()`; la terminación se obtiene con `await proc.wait()`, que la propia librería resuelve mediante su manejo interno de `SIGCHLD`, sin que el equipo escriba polling.
- Ventajas: detección de término inmediata (evento, no polling); separación de stdout/stderr nativa vía dos `StreamReader`; se integra directamente con el event loop de ADR-001 sin hilos adicionales.
- Desventajas/riesgos: solo aplica si el servicio ya usa `asyncio` (ADR-001, Alternativa B); hay que recordar hacer `await proc.wait()` siempre para no dejar procesos zombis (RNF-30).

## Decisión
 **Alternativa B**, con razón de consistentencia a la Alternativa B de ADR-001. 

## Consecuencias
- Positivas: stdout/stderr separados de forma nativa; terminación de un hijo no afecta a otros (RNF-09) porque cada `Popen`/subproceso de asyncio tiene sus propios streams.
- Negativas: hay que cerrar explícitamente los streams (`proc.stdout.close()` no siempre es necesario con asyncio, pero sí vigilar que no queden tareas de lectura colgadas) para no fugar descriptores bajo carga (RNF-33).
- Riesgos y mitigación: fuga de descriptores/tareas asyncio pendientes → prueba de estrés TC-024 verificando descriptores y tareas activas antes/después con `asyncio.all_tasks()`.

## Evidencia / prototipo
Job que escribe a stdout y stderr intercalado; verificar que `asyncio` los recupera por separado y que `proc.returncode` coincide con el real, incluyendo el caso de un hijo terminado por señal (RF-29, valor negativo de `returncode` en Python cuando el proceso muere por señal).
