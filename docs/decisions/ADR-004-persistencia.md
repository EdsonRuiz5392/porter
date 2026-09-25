# ADR-003: Persistencia de metadatos y recuperación (Python)

- Estado: Aceptado
- Fecha: 2026-09-25
- Requisitos relacionados: RF-12, RF-13, RNF-06, RNF-10, RNF-11, RNF-28, RNF-31

## Contexto y problema
Se debe conservar metadatos de trabajos tras reiniciar el servicio, sin corromper el almacenamiento ante una caída a mitad de escritura, soportando al menos 500 registros con consultas en menos de 1s. En Python conviene evaluar primero lo que ya trae la librería estándar antes de agregar dependencias.

## Alternativas consideradas

### Alternativa A: Archivos JSON por trabajo + escritura atómica con `os.replace()`
- Descripción: un archivo por job en `data/jobs/<id>.json`, usando el módulo `json`; cada actualización se escribe a un archivo temporal (`tempfile.NamedTemporaryFile` en el mismo directorio) y se reemplaza con `os.replace()`, atómico en el mismo sistema de archivos.
- Ventajas: cero dependencias externas; fácil de inspeccionar a mano; `os.replace()` resuelve RNF-28 de forma directa.
- Desventajas/riesgos: listar/filtrar 500+ trabajos implica abrir muchos archivos si no se mantiene un índice en memoria al arrancar (riesgo para RNF-05); hay que programar a mano la reconstrucción del índice al iniciar (RF-13).

### Alternativa B: `sqlite3` (módulo estándar de Python) con una tabla `jobs` y transacciones
- Descripción: una sola base de datos embebida usando el módulo `sqlite3`, que ya viene incluido en Python (no es una dependencia externa que declarar); cada transición de estado es una transacción SQL con `commit()`/`rollback()`.
- Ventajas: atomicidad la da la librería (cumple RNF-28 sin código propio); consultas y filtros (RF-09) triviales con SQL; ya está en la librería estándar, sin agregar dependencias a `requirements.txt`; buen desempeño con 500 registros.
- Desventajas/riesgos: `sqlite3.Connection` no es segura para usarse desde varios hilos sin `check_same_thread=False` y disciplina extra; si el servicio usa `asyncio` (ADR-001), las llamadas a `sqlite3` son bloqueantes y deben despacharse con `loop.run_in_executor()` (o usar la librería de terceros `aiosqlite` si el equipo prefiere evitar ese despacho manual).

## Decisión
 **Alternativa B (`sqlite3` en modo WAL)**, por ser la opción con menos código propio para garantizar atomicidad y por venir en la librería estándar de Python (no complica RNF-02 de construcción reproducible). Ante el uso de `asyncio` en ADR-001, despachar cada operación de base de datos con `loop.run_in_executor()` para no bloquear el event loop, y documentarlo explícitamente en la guía técnica.

## Consecuencias
- Positivas: menos código propio de manejo de E/S; transacciones simplifican TC-022 (interrupción durante persistencia); sin dependencias nuevas que declarar.
- Negativas: el equipo debe recordar despachar las llamadas a `sqlite3` fuera del event loop si se usa `asyncio`, o se viola el modelo de ADR-001.
- Riesgos y mitigación: bloqueo del event loop por una consulta lenta → usar `run_in_executor()` y transacciones cortas; probar con TC-024.

## Evidencia / prototipo
Matar el proceso (`kill -9` o `os.kill(pid, signal.SIGKILL)` desde un script externo) repetidamente a mitad de una transacción y verificar, al reiniciar, que ningún trabajo queda en un estado imposible (TC-007 y TC-022).
