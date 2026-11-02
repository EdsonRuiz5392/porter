# ADR-008: Política de cancelación: alcance, escalamiento y estado final (Python)

- Estado: Aceptado
- Fecha: 2026-10-20
- Requisitos relacionados: RF-10, RF-26, RF-29, RF-30, RNF-09, RNF-27, RNF-30
- Relación con otros ADR: **Reemplaza la "Decisión de escalamiento" (Alternativa C) de ADR-005.** **Modifica ADR-002** (cómo se lanza el proceso hijo). ADR-010 y ADR-011 se apoyan en esta decisión.

## Contexto y problema
La política de ADR-005 (`proc.terminate()`, esperar `grace_seconds`, `proc.kill()`) funcionaba con procesos simples, pero las pruebas encontraron cuatro problemas:

1. **La señal solo llegaba al hijo directo.** Con `bash -c "sleep 40; echo x"`, la cancelación mataba `bash`, pero el `sleep` (nieto) seguía vivo con los pipes abiertos. El trabajo seguía RUNNING 8 s después y ocupaba el cupo, así que el siguiente trabajo no arrancaba.
2. **Los hijos compartían el grupo de procesos del servicio.** Un Ctrl+C en la terminal del servicio les llegaba también (SIGINT) y quedaban FAILED con código -2.
3. **Hueco entre "sacar de la cola" y "marcar RUNNING".** Una cancelación que llegaba en ese intervalo respondía `ALREADY_FINISHED` y el trabajo corría completo: pasó en **25 de 25** intentos al cancelar inmediatamente después de enviar.
4. **Toda muerte por SIGTERM o SIGKILL se etiquetaba CANCELED**, aunque nadie lo hubiera pedido (por ejemplo, un `kill -9` desde otra terminal).

## Alternativas consideradas (alcance de la señal)

### Alternativa A: señal solo al hijo directo (implementación anterior)
- Ventajas: la más simple.
- Desventajas/riesgos: los descendientes sobreviven (punto 1). Insuficiente para RF-10 y RNF-30.

### Alternativa B: un grupo de procesos propio por trabajo + `os.killpg`
- Descripción: lanzar con `asyncio.create_subprocess_exec(..., start_new_session=True)`. El trabajo queda como líder de su propio grupo (ID de grupo = PID), y la señal se manda al grupo completo con `os.killpg(pgid, señal)`.
- Ventajas: alcanza a todos los descendientes; aísla los trabajos de las señales de la terminal del servicio; da a la recuperación (ADR-010) un grupo al cual terminar. Usa solo la biblioteca estándar y no requiere root (RNF-03).
- Desventajas/riesgos: no alcanza a un proceso que se salga **a propósito** de su grupo (`setsid`, demonios).

### Alternativa C: `prctl(PR_SET_PDEATHSIG)`
- Descripción: pedir al kernel que mate al hijo cuando muera el padre.
- Desventajas/riesgos: solo afecta al hijo directo, no a los nietos; no ayuda a cancelar; en Python requiere `preexec_fn`, que la documentación desaconseja cuando hay hilos (el servicio los usa para SQLite con `run_in_executor`). **Rechazada.**

### Alternativa D: cgroups v2
- Ventajas: control total, incluso de procesos que se salen de su grupo.
- Desventajas/riesgos: requiere configuración del sistema o permisos elevados (choca con RNF-03) y una complejidad desproporcionada para el alcance. **Rechazada.**

## Decisión
**Alternativa B**, con este escalamiento (`launcher.cancel`):
1. `os.killpg(pgid, SIGTERM)` a todo el grupo.
2. Esperar hasta `grace_seconds` a que **todo el grupo** desaparezca: sondeo con `os.killpg(pgid, 0)` cada 0.1 s, no solo `proc.wait()` del líder.
3. Si queda alguien, `os.killpg(pgid, SIGKILL)`.
4. `await proc.wait()` para recoger el código y no dejar zombis.

**Reglas de estado** (`control.py`):

| Situación | Qué se hace | Respuesta | Estado final |
|---|---|---|---|
| Trabajo en la cola | Se retira de la cola; nunca se ejecuta | `CANCELING` | CANCELED |
| Ya salió de la cola pero aún no está RUNNING ("en tránsito") | Se anota como cancelación pendiente (`_en_curso` + `_cancel_requested`). `_run_job` la revisa **antes de lanzar** (no lo lanza) y **justo después de arrancar** (lo cancela) | `CANCELING` | CANCELED |
| RUNNING | Señal al grupo (escalamiento de arriba) | `CANCELING` | CANCELED, lo escribe `_run_job` al terminar el proceso (único escritor del estado final) |
| Varias cancelaciones simultáneas (RF-26) | Solo la primera envía la señal | Todas `CANCELING` | Un único estado final |
| Ya terminado | Nada | `ALREADY_FINISHED` | Sin cambio |
| No existe | Nada | Error `NOT_FOUND` | — |

**Qué cuenta como CANCELED (RF-29):** solo si alguien pidió la cancelación, ya sea un usuario o el cierre del servicio (ADR-011). Cualquier otra muerte por señal queda **FAILED** y se registra el evento `KILLED_BY_SIGNAL` con el número de la señal.

**Carrera entre cancelar y terminar solo:** gana lo que JobRunner registra primero.
- Si la solicitud se registró antes del final, el trabajo queda CANCELED, **aunque el programa haya salido con 0**.
- Si el trabajo ya estaba registrado como terminado, se responde `ALREADY_FINISHED` y se conserva su estado.

Además, la bitácora registra `CANCEL_REQUESTED` (lo que se *pidió*) por separado del estado final.

## Consecuencias
- Positivas: los nietos ya no sobreviven a la cancelación; Ctrl+C ya no mata trabajos, así que el cierre pasa siempre por ADR-011; los estados reflejan lo que realmente ocurrió; las cancelaciones inmediatas ya no se pierden.
- Negativas: el código de salida por sí solo no basta para saber si fue una cancelación: -15 puede ser CANCELED o FAILED, así que hay que mirar el estado.
- Riesgos y mitigación:
  - Un programa que se sale de su grupo a propósito (`setsid`) queda fuera de control → **límite conocido**, documentado en la guía técnica.
  - En contenedores donde el proceso 1 no recoge zombis, el sondeo puede ver el grupo "vivo" hasta agotar `grace_seconds` y escalar a SIGKILL sin necesidad. Es inofensivo.
