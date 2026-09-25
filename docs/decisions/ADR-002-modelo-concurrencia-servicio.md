# ADR-001: Modelo de concurrencia del servicio JobRunner (Python)

- Estado: Aceptado
- Fecha: 2026-09-21
- Requisitos relacionados: RF-04, RF-05, RF-18, RF-19, RF-22, RNF-04, RNF-07, RNF-24, RNF-27

## Contexto y problema
El servicio debe atender simultáneamente múltiples clientes (locales y remotos) y controlar N procesos hijos en ejecución, sin bloquear la atención de nuevas solicitudes. En Python hay que decidir el modelo de concurrencia considerando el GIL (Global Interpreter Lock), que impide paralelismo real de hilos en CPU-bound pero no penaliza trabajo I/O-bound como sockets y espera de procesos.

## Alternativas consideradas

### Alternativa A: `threading` — un hilo por conexión + estructuras compartidas con `threading.Lock`/`Condition`
- Descripción: cada cliente conectado se atiende en un `threading.Thread`; un hilo adicional vigila los procesos hijos con `subprocess.Popen.poll()` en un bucle con `time.sleep`. El estado de trabajos/cola vive en un diccionario protegido por `threading.Lock`.
- Ventajas: modelo conocido, encaja con el uso de sockets bloqueantes (`socket.accept()`, `recv()`), fácil de explicar en la defensa individual.
- Desventajas/riesgos: el GIL serializa la ejecución de bytecode entre hilos (no da paralelismo real, aunque para I/O no es grave); hay que ser disciplinados con los `Lock` en cada acceso al diccionario de trabajos para cumplir RNF-27; el polling de `Popen.poll()` agrega latencia en la detección de término.

### Alternativa B: `asyncio` — un solo event loop con `asyncio.start_server` y `asyncio.create_subprocess_exec`
- Descripción: todo el servicio corre como corutinas sobre un único event loop. Los sockets de clientes se manejan con `asyncio.StreamReader`/`StreamWriter`; los procesos hijos se lanzan con `asyncio.create_subprocess_exec`, y `await proc.wait()` notifica la terminación sin polling manual (asyncio internamente usa el manejo de `SIGCHLD` vía su *child watcher*).
- Ventajas: al no haber hilos, no hace falta `Lock` para el estado compartido (todo el código que toca el diccionario de trabajos corre en el mismo hilo lógico); es la forma "nativa" en Python de multiplexar E/S; se integra directamente con la detección de fin de proceso (ADR-002) y el framing de protocolo (ADR-004) sin polling.
- Desventajas/riesgos: cualquier llamada bloqueante hecha por accidente dentro de una corutina (p. ej. una consulta SQLite sin `run_in_executor`) congela todo el servicio; el equipo debe aprender a evitar código síncrono bloqueante dentro del loop.

## Decisión
 **Alternativa B (`asyncio`)**. Es la opción que más reduce el riesgo de condiciones de carrera (RF-26, RNF-27) porque el estado de trabajos se modifica siempre desde el mismo hilo lógico, y Python la soporta de forma nativa sin dependencias externas. La condición es documentar explícitamente qué operaciones son bloqueantes (por ejemplo, escritura en SQLite) y despacharlas con `loop.run_in_executor()` para no congelar el event loop.

## Consecuencias
- Positivas: menos bugs de concurrencia difíciles de reproducir; consistente con ADR-002 y ADR-004.
- Negativas: el equipo debe aprender a identificar y aislar llamadas bloqueantes (E/S de disco, `sqlite3` síncrono) para no violar el modelo.
- Riesgos y mitigación: una corutina que se cuelga bloquea todo el servicio → usar `asyncio.wait_for()` con timeouts en operaciones externas y probarlo en TC-002/TC-017.

## Evidencia / prototipo
Prototipo mínimo: servidor `asyncio` que acepta 3 conexiones simultáneas y mantiene 3 jobs corriendo con `asyncio.create_subprocess_exec`, con evidencia de estrés en `verif/results/`, ligado a TC-002 y TC-017.
