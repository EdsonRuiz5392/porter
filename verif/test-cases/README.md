# Casos de prueba — Porter

Cada archivo `TC-XXX.md` sigue el formato del doc 05: identificador y título, requisitos, objetivo, precondiciones, entorno y configuración, datos de entrada, pasos reproducibles, resultado esperado, resultado observado, evidencia, estado y responsable.

**Diseña los casos:** Edson (líder de verificación). **Los ejecuta:** el dueño del módulo, y un revisor distinto confirma los críticos (doc 05).

**Estados:** `PENDIENTE` (no ejecutado), `PASS`, `FAIL` (abre un issue de defecto), `BLOCKED` (no se pudo ejecutar; se anota la causa).

**Evidencia:** cada ejecución formal se guarda en `verif/results/<run-id>/` con commit, entorno, comando, salidas y resumen (doc 04). Por defecto, `run-id` = `<fecha>_<hora>_<commit corto>`; se puede elegir otro con `--run-id`.

## Preparación común (referida por todos los casos)

Entorno de referencia: Ubuntu 24.04 LTS, Python 3.12, sin root, desde la raíz del repositorio.

**Terminal 1 — servicio.** Se fija toda la configuración por variables de entorno para no depender de valores por defecto, y se usa una carpeta de datos temporal para no dejar rastro en el repositorio:

```bash
source .venv/bin/activate
export JOBRUNNER_HOST=127.0.0.1 JOBRUNNER_PORT=9000 JOBRUNNER_DATA_DIR=/tmp/porter-tc
export JOBRUNNER_MAX_CONCURRENCY=3 JOBRUNNER_MAX_QUEUE=20 JOBRUNNER_GRACE_SECONDS=5 JOBRUNNER_SHUTDOWN_TIMEOUT=30
export JOBRUNNER_ALLOWED_NETWORKS=127.0.0.1 JOBRUNNER_MAX_MESSAGE_BYTES=65536
rm -rf /tmp/porter-tc
python -m src.servicio.main
```

**Terminal 2 — cliente.** El cliente lee `JOBRUNNER_HOST`, `JOBRUNNER_PORT` y `JOBRUNNER_MAX_MESSAGE_BYTES`; deben coincidir con los del servicio:

```bash
source .venv/bin/activate
export JOBRUNNER_HOST=127.0.0.1 JOBRUNNER_PORT=9000 JOBRUNNER_MAX_MESSAGE_BYTES=65536
```

Alias usado en los pasos: `porter` equivale a `python -m src.cliente.cli`.

Cuando un caso pide otra configuración (por ejemplo `JOBRUNNER_MAX_CONCURRENCY=1`), lo indica en su sección de entorno; hay que reiniciar el servicio con ese valor.

## Casos y resultado de la corrida `2026-11-02_avance02-final`

La línea base anterior a las correcciones está en `verif/results/2026-10-21_avance01-linea-base_bc113057/` (23 de 57). La corrida final dio 57 de 57 en Ubuntu 24.04.

| Caso | Título | Requisitos | Estado |
|---|---|---|---|
| [TC-001](TC-001.md) | Enviar trabajo válido | RF-01, RF-02, RNF-14 | PASS |
| [TC-002](TC-002.md) | Cola y límite de concurrencia | RF-03, RF-04, RF-05, RNF-04, RNF-07 | PASS |
| [TC-003](TC-003.md) | Estados y tiempos | RF-06, RF-07 | PASS |
| [TC-004](TC-004.md) | Consultar y listar | RF-08, RF-09, RNF-05, RNF-06 | PASS (intermitente en Kali) |
| [TC-005](TC-005.md) | Cancelar en cola y en ejecución | RF-10 | PASS |
| [TC-006](TC-006.md) | stdout, stderr y código de salida | RF-11, RF-07 | PASS |
| [TC-007](TC-007.md) | Reinicio y recuperación | RF-12, RF-13, RNF-10, RNF-11, RNF-30, RNF-31 | PASS |
| [TC-008](TC-008.md) | Aislamiento de fallo | RNF-08, RNF-09 | PASS |
| [TC-009](TC-009.md) | Cierre controlado | RF-15, RNF-25, RNF-30 | PASS |
| [TC-012](TC-012.md) | Fragmentación y mensajes inválidos | RF-21, RF-22, RNF-14, RNF-24 | PASS |
| [TC-013](TC-013.md) | Configuración y salud | RF-16, RF-24 | PASS |
| [TC-014](TC-014.md) | Construcción desde clon limpio | RNF-01, RNF-02, RNF-03 | PENDIENTE |
| [TC-015](TC-015.md) | Ayuda y códigos de salida del cliente | RF-17, RNF-21 | PASS (parte automatizada) |
| [TC-016](TC-016.md) | Saturación de cola | RF-23, RF-25, RNF-29 | PASS |
| [TC-017](TC-017.md) | Cancelaciones concurrentes | RF-26, RNF-27 | PASS |
| [TC-018](TC-018.md) | Solicitud duplicada (a y b) | RF-27 | PASS |
| [TC-019](TC-019.md) | Desconexión durante una solicitud | RF-28, RF-22 | PASS |
| [TC-020](TC-020.md) | Terminación inesperada del hijo | RF-29, RNF-30 | PASS |
| [TC-021](TC-021.md) | Escalamiento de la cancelación | RF-30 | PASS |
| [TC-022](TC-022.md) | Interrupción durante la persistencia | RNF-28, RNF-31 | PASS (intermitente en Kali) |
| [TC-023](TC-023.md) | Compatibilidad de protocolo | RNF-32 | PASS |
| [TC-024](TC-024.md) | Liberación de recursos bajo carga | RNF-33 | PASS (intermitente en Kali) |

TC-010 y TC-011 (operación remota y restricción de red) corresponden al Hito 3.
