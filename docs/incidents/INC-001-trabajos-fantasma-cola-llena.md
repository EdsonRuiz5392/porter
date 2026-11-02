# INC-001 — La cola llena con envíos simultáneos crea trabajos fantasma

| | |
|---|---|
| **Estado** | Cerrado |
| **Severidad** | Crítica |
| **Detectado** | 15 de octubre de 2026, en la auditoría de robustez de verificación |
| **Corregido** | 27 de octubre de 2026 (PR #54, con PR #52) |
| **Issues** | #35 y #36 |
| **Requisitos** | RF-13, RF-25, RNF-27, RNF-28, RNF-29, RNF-31 |
| **Decisiones** | ADR-006 y ADR-010 |
| **Responsables** | Detecta: Edson · Corrige: Dylan · Confirma: corrida de verificación |

## Síntomas

Con la cola casi llena y varios clientes enviando al mismo tiempo:

- Los rechazados recibían `INTERNAL_ERROR` en lugar de `QUEUE_FULL`.
- Esos trabajos, que el cliente creía rechazados, quedaban guardados como `QUEUED` en la base sin estar en la cola.
- `health` y la base no coincidían.
- Al reiniciar, **el servicio no arrancaba**.

## Evidencia

Auditoría del 15 de octubre, sobre `e8dca95`, con `MAX_CONCURRENCY=1`, `MAX_QUEUE=2` y 10 clientes simultáneos:

| Dónde | Observado |
|---|---|
| Respuestas | 3 `QUEUED` y 7 `INTERNAL_ERROR: La cola de trabajos está llena.` |
| Base de datos | 9 `QUEUED` y 1 `RUNNING` |
| `health` | `queued: 2` |
| Reinicio | `QueueFullError` en `recover_on_startup`; el servicio termina |

Línea base del 21 de octubre, sobre `bc11305`, en `verif/results/2026-10-21_avance01-linea-base_bc113057/`:

```
test_carrera_diez_envios_con_un_lugar ... FAIL
Counter({'INTERNAL_ERROR': 9, 'QUEUED': 1}) != Counter({'QUEUE_FULL': 9, 'QUEUED': 1})

test_bajar_max_queue_con_pendientes ... FAIL
src.servicio.gestion_trabajos.cola.QueueFullError: La cola de trabajos está llena.
```

## Hipótesis

1. **Límite de `MAX_QUEUE` mal aplicado:** descartada. Los envíos de uno en uno se rechazaban bien, con `QUEUE_FULL`. Solo fallaba con envíos simultáneos.
2. **Carrera entre revisar la cola y encolar:** confirmada al leer `control.submit`.
3. **Corrupción de la base:** descartada. Las filas eran válidas; lo incorrecto era que se hubieran guardado.

## Causa

En `control.submit` había un `await` entre revisar y actuar:

1. `cola.is_full()` responde que hay lugar.
2. `await persistencia.save_job(job)`: aquí `asyncio` deja correr a otros clientes, que también ven lugar.
3. `cola.enqueue(job_id)` lanza `QueueFullError` para los que ya no caben, **cuando su fila ya está guardada**.

Había además dos clases con el mismo nombre: `cola.QueueFullError` y `control.QueueFullError`. `entrada.py` solo traduce la de control, por eso la otra salía como `INTERNAL_ERROR`.

Al reiniciar, `recover_on_startup` intentaba encolar todas esas filas `QUEUED` con `enqueue`, que aplica el límite, y el servicio terminaba.

## Corrección

| PR | Autor | Cambio |
|---|---|---|
| #52 | Dylan | `cola.restore()`: reencola sin aplicar el límite; solo se usa al recuperar |
| #54 | Dylan | `_submit_lock`: un solo envío a la vez entre revisar y encolar. `recover_on_startup` usa `restore()` |

Se considera un trabajo aceptado aunque exceda `MAX_QUEUE` después de un reinicio: el límite controla la admisión de trabajos nuevos, no la conservación de los ya aceptados (ADR-010).

## Prueba de regresión

| Prueba | Comprueba |
|---|---|
| `TC016Saturacion.test_carrera_diez_envios_con_un_lugar` | 10 envíos con 1 lugar: 1 `QUEUED`, 9 `QUEUE_FULL` y sin filas fantasma |
| `TC022RecuperacionCapacidad.test_bajar_max_queue_con_pendientes` | Arranca con 8 pendientes y capacidad 3, y no pierde ninguno |

Para repetirlas:

```bash
python3 verif/scripts/run_verificacion.py --filtro tc016
```
```bash
python3 verif/scripts/run_verificacion.py --filtro tc022
```

**Resultado:** PASS en `verif/results/2026-11-02_avance02-final/` (57 de 57, Ubuntu 24.04).

## Qué aprendimos

- En `asyncio`, "un solo hilo" no significa "sin carreras": todo `await` entre revisar y actuar es un punto donde otra tarea puede entrar.
- Los envíos de uno en uno no habrían encontrado este defecto; hacía falta probar con clientes simultáneos.
