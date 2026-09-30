# Casos de prueba — Porter

Cada archivo `TC-XXX.md` sigue el formato del doc 05: identificador y título, requisitos, objetivo, precondiciones, entorno y configuración, datos de entrada, pasos reproducibles, resultado esperado, resultado observado, evidencia, estado y responsable.

**Diseña los casos:** Edson (líder de verificación). **Los ejecuta:** el dueño del módulo, y un revisor distinto confirma los críticos (doc 05).

**Estados:** `PENDIENTE` (no ejecutado), `PASS`, `FAIL` (abre un issue de defecto), `BLOCKED` (no se pudo ejecutar; se anota la causa).

**Evidencia:** cada ejecución formal se guarda en `verif/results/<run-id>/` con commit, entorno, comando, salidas y resumen (doc 04). `run-id` = `AAAAMMDD-HHMM-<commit corto>`.

## Preparación común (referida por todos los casos)

Entorno de referencia: Ubuntu 24.04 LTS, Python 3.12, sin root, desde la raíz del repositorio.

**Terminal 1 — servicio.** Se fija toda la configuración por variables de entorno para no depender de valores por defecto, y se usa una carpeta de datos temporal para no dejar rastro en el repositorio:

```bash
source .venv/bin/activate
export JOBRUNNER_HOST=127.0.0.1 JOBRUNNER_PORT=9000 JOBRUNNER_DATA_DIR=/tmp/porter-tc
export JOBRUNNER_MAX_CONCURRENCY=3 JOBRUNNER_MAX_QUEUE=20 JOBRUNNER_GRACE_SECONDS=5
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

## Casos del Avance 01 (núcleo local)

| Caso | Título | Requisitos | Ejecuta |
|---|---|---|---|
| TC-001 | Enviar trabajo válido | RF-01, RF-02 | Dylan |
| TC-002 | Cola y procesos separados (parcial) | RF-03, RF-04 | Dylan, Marcos |
| TC-003 | Estados y tiempos | RF-06, RF-07 | Dylan |
| TC-004 | Consultar y listar | RF-08, RF-09 | Dylan |
| TC-005 | Cancelar en cola y en ejecución | RF-10 | Marcos |
| TC-006 | stdout, stderr y código de salida | RF-11, RF-07 | Ángel, Marcos |
| TC-008 | Aislamiento de fallo | RNF-08, RNF-09 | Juan, Marcos |
| TC-014 | Construcción desde clon limpio | RNF-01, RNF-02, RNF-03 | Edson |
| TC-015 | Usabilidad del cliente | RF-17, RNF-21 | Dylan |
