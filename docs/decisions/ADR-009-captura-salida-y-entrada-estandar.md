# ADR-009: Captura de la salida y entrada estándar de los trabajos (Python)

- Estado: Aceptado
- Fecha: 2026-10-20
- Requisitos relacionados: RF-05, RF-11, RF-29, RNF-07, RNF-09, RNF-33
- Relación con otros ADR: **Modifica ADR-002** (cómo se leen `proc.stdout` y `proc.stderr` y qué entrada recibe el hijo).

## Contexto y problema
ADR-002 dejó abierta la forma de leer los `StreamReader`, y la implementación usó `readline()`. Las pruebas encontraron:

1. **Límite de 64 KiB por línea.** Un trabajo que escribió 200,000 caracteres sin salto de línea hizo fallar `readline()`. El trabajo quedó FAILED (-1) en 0.11 s, **pero el proceso siguió vivo y sin control**.
2. **Doble descuento del cupo.** En ese mismo camino de error, `_run_job` restaba la reserva de concurrencia aunque `mark_running` ya la había restado. Con un límite de 2 llegaron a correr 3 trabajos (RF-05, RNF-07).
3. **La salida no se veía mientras el trabajo corría.** El archivo se escribía con búfer, así que un `output` a mitad de la ejecución devolvía vacío.
4. **Entrada heredada.** El hijo heredaba el stdin del servicio: un `cat` lanzado con el servicio abierto en una terminal quedaba esperando entrada para siempre.

## Alternativas consideradas (lectura de la salida)

### Alternativa A: `readline()` (implementación anterior)
- Desventajas/riesgos: tiene un límite de largo de línea y, al superarlo, deja el proceso sin control. **Rechazada.**

### Alternativa B: `readline()` con un `limit` mayor en el `StreamReader`
- Ventajas: un cambio mínimo.
- Desventajas/riesgos: solo mueve el límite, no lo quita, y aumenta la memoria por trabajo.

### Alternativa C: leer por bloques con `read(65536)`, guardar los bytes tal cual y hacer `flush()` por bloque
- Ventajas: no hay límite de largo de línea; se guardan exactamente los bytes que escribió el programa; la salida es visible mientras corre (RF-11).
- Desventajas/riesgos: los archivos pueden contener bytes que no son UTF-8 válido, así que hay que decodificar con tolerancia al consultarlos; hay más escrituras a disco con salidas muy grandes.

## Alternativas consideradas (entrada del trabajo)
- **Heredar el stdin del servicio** (anterior): rechazada por el punto 4.
- **`stdin=DEVNULL`**: el trabajo recibe una entrada vacía (fin de archivo inmediato).
- **`stdin=PIPE`** para enviarle datos: no lo pide ningún requisito; se descarta por ahora.

## Decisión
- **Alternativa C** para la salida (`launcher.stream_output`): bloques de 64 KiB, archivo abierto en modo binario (`"wb"`) y `flush()` después de cada bloque. Se sigue usando `asyncio.gather` para leer stdout y stderr al mismo tiempo, como en ADR-002.
- `control.get_output` decodifica con `encoding="utf-8", errors="replace"`: los bytes inválidos se muestran como `�`.
- **`stdin=DEVNULL`** en `launcher.start`.
- **Si la captura falla después de lanzar el proceso** (`_run_job`):
  1. se termina el grupo del proceso con el escalamiento de ADR-008, con gracia 0;
  2. el trabajo se marca FAILED (-1) con el evento `ERROR` en la bitácora;
  3. la reserva de cupo se libera **una sola vez**, gracias a una bandera `arrancado` que indica si `mark_running` ya la convirtió en ejecución.

## Consecuencias
- Positivas: no hay límite de largo de línea; la salida se puede consultar mientras el trabajo corre; ningún error de captura deja procesos sin control; el límite de concurrencia se respeta también ante errores.
- Negativas: los trabajos interactivos (que esperan escribir en el teclado) no están soportados, y debe documentarse en la guía de usuario. Los caracteres inválidos se muestran como `�`.
- Riesgos y mitigación: `output` devuelve el archivo completo, sin límite. Una salida de varios MB puede exceder `JOBRUNNER_MAX_MESSAGE_BYTES` en el cliente (se midió una respuesta de 3.97 MiB contra un máximo de 1 MiB). → **Límite conocido**; la mejora futura es paginar o truncar `output`.