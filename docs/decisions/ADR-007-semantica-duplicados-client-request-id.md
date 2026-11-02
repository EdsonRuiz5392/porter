# ADR-007: Semántica de solicitudes duplicadas (`client_request_id`) (Python)

- Estado: Aceptado
- Fecha: 2026-10-20
- Requisitos relacionados: RF-12, RF-27, RF-28, RNF-14, RNF-27
- Relación con otros ADR: **Reemplaza la "Decisión de duplicados" de ADR-005** (alternativa B2 con ventana por estado). **Modifica ADR-003** (cómo se guarda una fila) y **ADR-004** (nuevo código de error `REQUEST_ID_CONFLICT`). Se apoya en ADR-006 para la atomicidad.

## Contexto y problema
ADR-005 decidió deduplicar solo mientras el trabajo siguiera QUEUED o RUNNING, y crear un trabajo nuevo si el folio se reenviaba después de que el original terminara. Al implementarlo y probarlo aparecieron tres problemas:

1. **Era incompatible con la base de datos.** La tabla `jobs` tiene `client_request_id TEXT UNIQUE` (exigido por el contrato de interfaces). Crear un segundo trabajo con el mismo folio solo "funcionaba" porque `save_job` usaba `INSERT OR REPLACE`, que, ante el choque con la restricción `UNIQUE`, **borra la fila del trabajo original** sin avisar. Comprobado: después del segundo envío, consultar el ID original respondía `NOT_FOUND`. Es pérdida de historial y contradice RF-12. Por la misma razón, `DuplicateClientRequestError` nunca llegaba a lanzarse.
2. **El folio generado automáticamente por el CLI no protege nada.** Cada invocación del CLI es un proceso nuevo; un folio aleatorio por invocación nunca se repite. Solo serviría si el propio CLI reintentara la misma solicitud, y no lo hace.
3. **No estaba definido qué pasa** si se reutiliza el folio con **otro comando**.

## Alternativas consideradas

### Alternativa A: ventana por estado (la decisión original de ADR-005)
- Descripción: deduplicar solo mientras QUEUED o RUNNING; después, crear un trabajo nuevo con el mismo folio.
- Ventajas: el folio puede reutilizarse.
- Desventajas/riesgos: exige quitar la restricción `UNIQUE` o borrar el trabajo original. Lo primero quita la red de seguridad contra duplicados simultáneos; lo segundo pierde historial (RF-12). **Rechazada.**

### Alternativa B: idempotencia total
- Descripción: mismo folio → siempre se devuelve el trabajo original, sin mirar el comando.
- Ventajas: la regla más simple.
- Desventajas/riesgos: un error del usuario pasa en silencio. Si reutiliza un folio por accidente con otro comando, cree que lanzó X y recibe el trabajo Y.

### Alternativa C: idempotencia con verificación de contenido
- Descripción: mismo folio con el **mismo comando y argumentos** = reintento → se devuelve el trabajo original, en cualquier estado. Mismo folio con **otro** comando o argumentos = error explícito.
- Ventajas: los reintentos tras una desconexión son seguros (RF-28) y los errores del usuario son visibles.
- Desventajas/riesgos: un código de error más en el protocolo; hay que comparar el comando y los argumentos.

## Decisión
**Alternativa C** (decisión del equipo).

| Situación | Resultado |
|---|---|
| Envío sin folio | Siempre se crea un trabajo nuevo (comportamiento sin cambios) |
| Folio nuevo | Se crea el trabajo; el folio queda asociado a él de forma permanente |
| Mismo folio, mismo `command` y mismos `args` | Reintento: se devuelve el trabajo original (cualquier estado); no se ejecuta nada. Bitácora: `DUPLICATE` |
| Mismo folio, `command` o `args` distintos | Error `REQUEST_ID_CONFLICT`: *"El client_request_id 'X' ya se usó con otro comando (trabajo …). Usa un client_request_id distinto."* Bitácora: `REQUEST_ID_CONFLICT` |

Se conserva de ADR-005 que el folio sea **opcional**, para que otros clientes, como los de la verificación cruzada entre equipos, puedan hablar el protocolo sin él.

**Implementación:**
- `control.submit` / `_resolver_duplicado`: busca el folio dentro del candado de ADR-006. La comparación es estricta: `existing.command == command` y `existing.args == args`, considerando orden y espacios.
- **Validación:** el folio debe ser texto no vacío de 128 caracteres como máximo; si no, `INVALID_REQUEST`.
- **Red de seguridad en la base (`persistencia.save_job`, misma firma):** se reemplazó `INSERT OR REPLACE` por `INSERT … ON CONFLICT(id) DO UPDATE SET status, exit_code, pid, started_at, finished_at`. Así solo se actualiza la fila **del mismo ID**. Si choca el folio de otro trabajo, SQLite lanza `IntegrityError`, que se convierte en `DuplicateClientRequestError`, y `submit` aplica la misma regla de la tabla. Alternativas evaluadas para este punto:
  - `INSERT OR REPLACE`: rechazada, porque borra filas.
  - `INSERT` y `UPDATE` en funciones separadas: válida, pero cambia el contrato de `persistencia`.
  - Upsert con `ON CONFLICT(id)`: **elegida**, porque no cambia la firma.
- **Protocolo:** constante nueva `ERROR_REQUEST_ID_CONFLICT = "REQUEST_ID_CONFLICT"` en `comun/protocolo.py`.
- **CLI:** opción explícita `submit --request-id FOLIO <comando> [args...]`. El CLI **no** genera folios automáticamente, por el punto 2 del contexto.

## Consecuencias
- Positivas: el historial nunca se pierde; un cliente que perdió la respuesta recupera su ID reenviando la misma solicitud (RF-28); los conflictos se reportan con un mensaje útil (RNF-21).
- Negativas: un folio no puede reutilizarse nunca, aunque su trabajo haya terminado. El usuario del CLI debe escribir el folio a mano si quiere protección contra reintentos.
- Riesgos y mitigación:
  - Si en el futuro se borran trabajos antiguos (ver ADR-012), sus folios quedarían libres → documentarlo en ese momento.
  - Argumentos equivalentes pero escritos distinto (por ejemplo, otro orden) se consideran un conflicto: es intencional, porque la comparación estricta es predecible y verificable.
  - Mejora futura opcional: que el CLI reintente automáticamente con un folio propio cuando falle la conexión.
