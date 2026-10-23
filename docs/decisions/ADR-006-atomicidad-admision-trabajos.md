# ADR-006: Atomicidad en la admisión de trabajos (Python)

- Estado: Aceptado
- Fecha: 2026-10-20
- Requisitos relacionados: RF-25, RF-27, RNF-27, RNF-29
- Relación con otros ADR: **Complementa ADR-001** (modelo de concurrencia `asyncio`) y la **decisión de saturación de ADR-005** (rechazo inmediato), en cuanto a cómo se implementan sin condiciones de carrera.

## Contexto y problema
ADR-001 eligió `asyncio` argumentando que, al correr todo en un solo hilo, no hace falta `Lock` para el estado compartido. Eso es cierto solo para el código que **no tiene `await`** entre "revisar" y "actuar". En `control.submit` sí lo había:

1. revisar `cola.is_full()`,
2. `await persistencia.save_job(job)` ← aquí otra corrutina puede ejecutarse,
3. `cola.enqueue(job_id)`.

Al probarlo con 1 lugar libre y 10 envíos simultáneos, los 10 pasaron la revisión del paso 1. Resultado: 1 aceptado, **9 `INTERNAL_ERROR`** y **9 filas "fantasma"** (12 QUEUED en SQLite contra 3 en la cola en memoria). Al reiniciar, esos fantasmas no cabían en la cola y **el servicio no arrancaba** (ver ADR-010).

El error era `INTERNAL_ERROR` y no `QUEUE_FULL` porque existían dos clases distintas con el mismo nombre: `cola.QueueFullError` y `control.QueueFullError`.

La revisión de duplicados por `client_request_id` tenía el mismo patrón (buscar → `await` → guardar): 6 envíos simultáneos con el mismo folio devolvieron 6 IDs distintos, y 5 no existían.

## Alternativas consideradas

### Alternativa A: `asyncio.Lock` que cubra todo el tramo de admisión
- Descripción: un candado `self._submit_lock` en `Control`. Dentro de `async with self._submit_lock:` van, en este orden: buscar duplicado → revisar capacidad → crear el `Job` → `save_job` → `enqueue` → bitácora.
- Ventajas: una sola regla, fácil de explicar en la defensa ("un envío a la vez entre revisar y encolar"); protege también la revisión de duplicados; no requiere cambiar `cola.py` ni la base.
- Desventajas/riesgos: serializa los `submit`, incluida la escritura en SQLite. Con la carga académica no se nota (4 lotes de 90 envíos simultáneos sin errores).

### Alternativa B: contador de lugares reservados (sin candado)
- Descripción: en el mismo tramo sin `await` que `is_full()`, incrementar un contador `_pending` y liberarlo al encolar o al fallar.
- Ventajas: no serializa las escrituras a disco.
- Desventajas/riesgos: hay que liberar la reserva en **todos** los caminos de error; el proyecto ya tuvo un defecto de ese tipo con `_reserved_count` (ver ADR-009). Además no resuelve los duplicados simultáneos, que necesitarían otro mecanismo.

### Alternativa C: delegar la atomicidad a SQLite
- Descripción: contar los QUEUED e insertar dentro de una misma transacción.
- Ventajas: atómico incluso con varios procesos del servicio.
- Desventajas/riesgos: la cola real vive en memoria (`cola.py`), así que base y cola podrían seguir divergiendo; requiere más SQL y rediseñar `cola.py`.

## Decisión
**Alternativa A.** Detalles de implementación (`control.py`):
- Las validaciones baratas (servicio cerrando, tipos y tamaños) van **fuera** del candado, para no hacer esperar a nadie por una solicitud inválida.
- Se encola **inmediatamente después** de guardar y la bitácora se escribe al final. Así, si falla la escritura de la bitácora, no queda un trabajo guardado fuera de la cola.
- `_try_dispatch()` se agenda **fuera** del candado.
- Se elimina la ambigüedad del error: el rechazo por capacidad siempre lo produce `control.QueueFullError` (`QUEUE_FULL`) antes de llamar a `enqueue`.

## Consecuencias
- Positivas: el rechazo por cola llena siempre es limpio (`QUEUE_FULL`); no se crean trabajos fantasma; los duplicados simultáneos se resuelven con la misma regla (ADR-007).
- Negativas: los `submit` se atienden de uno en uno; el resto de operaciones (`status`, `list`, `cancel`, `output`, `health`) no se ven afectadas.
- Riesgos y mitigación:
  - Alguien agrega dentro del candado un `await` lento (por ejemplo, una llamada de red), y todos los envíos se frenan. → Regla en la guía técnica: dentro de `_submit_lock` solo se permite el acceso a SQLite ya existente.
  - Si en el futuro hubiera varios procesos del servicio sobre la misma base, el candado (que es local al proceso) no bastaría. → La restricción `UNIQUE` de ADR-007 sigue protegiendo los duplicados; la capacidad tendría que revisarse en otro ADR.
