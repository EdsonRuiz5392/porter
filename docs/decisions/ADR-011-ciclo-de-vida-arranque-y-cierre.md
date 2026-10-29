# ADR-011: Ciclo de vida del servicio: arranque y cierre controlado (Python)

- Estado: Aceptado
- Fecha: 2026-10-20
- Requisitos relacionados: RF-14, RF-15, RF-16, RNF-21, RNF-25, RNF-30
- Relación con otros ADR: complementa ADR-001 (event loop); usa la cancelación de ADR-008; los trabajos QUEUED que quedan al cerrar se recuperan según ADR-010.

## Contexto y problema
RF-15 pide iniciar y detenerse "de forma controlada, sin aceptar trabajos nuevos durante el cierre". La implementación anterior tenía tres problemas:

1. **El cierre no tenía límite de tiempo.** El servicio esperaba a que los trabajos terminaran solos: un trabajo de 3 horas significaba 3 horas para apagarse, y uno que nunca termina impedía apagarlo.
2. **Ctrl+C mataba los trabajos** por compartir el grupo de procesos. Esto ya se corrigió en ADR-008, y por eso ahora el cierre es el **único** mecanismo que termina trabajos al apagar, y debe estar definido.
3. **Puerto ocupado.** Si el puerto ya estaba en uso, el servicio quedaba vivo sin escuchar y sin avisar (el error solo aparecía al apagarlo), y aun así ejecutaba los trabajos recuperados.

## Alternativas consideradas (cierre)

### Alternativa A: esperar sin límite (implementación anterior)
- Ventajas: nunca se interrumpe un trabajo.
- Desventajas/riesgos: el cierre puede no terminar nunca, así que difícilmente es "controlado".

### Alternativa B: esperar hasta un tiempo configurable y luego cancelar con el escalamiento normal
- Ventajas: el cierre siempre termina en un tiempo acotado y conocido; reutiliza ADR-008 sin código nuevo de señales.
- Desventajas/riesgos: los trabajos largos se cortan al apagar.

### Alternativa C: cancelar todo de inmediato
- Desventajas/riesgos: se pierde trabajo que estaba por terminar.

**Estado de los trabajos cancelados por el cierre:** se compararon **CANCELED** (el servicio los terminó a propósito) y **FAILED con `INTERRUPTED`**. Este último se reserva para las caídas no controladas de ADR-010, así que distinguir ambos casos facilita el diagnóstico.

## Decisión
**Alternativa B**, implementada en `operacion.shutdown(job_manager, timeout)`, que cambia de firma, y en `main.py`:
1. `stop_accepting()`: los `submit` responden `SERVICE_CLOSING` (con el evento `REJECTED` en la bitácora). Las consultas (`status`, `list`, `output`, `health`) siguen funcionando; `health` reporta `active=false`.
2. Esperar hasta **`JOBRUNNER_SHUTDOWN_TIMEOUT`** segundos (variable nueva, número ≥ 0, por defecto **30**) a que terminen los trabajos en curso. Se cuentan también los que están "en tránsito", con `in_progress_count()`.
3. Los que sigan se cancelan con `cancel_all_running(motivo)` usando el escalamiento de ADR-008 y quedan **CANCELED**. La bitácora registra `CANCEL_REQUESTED` con el motivo "Cierre del servicio: se agotó JOBRUNNER_SHUTDOWN_TIMEOUT". Después se espera hasta 5 s a que se registre el estado final.
4. Los trabajos **QUEUED no se tocan**: siguen en la base y se ejecutan al reiniciar (ADR-010).
5. **SIGINT (Ctrl+C) y SIGTERM (`kill -TERM`) producen exactamente el mismo cierre.** `kill -9` sigue siendo una caída no controlada (ADR-010).

Tiempo máximo de cierre ≈ `SHUTDOWN_TIMEOUT + GRACE_SECONDS + 5 s` (unos 40 s con los valores por defecto). Con `JOBRUNNER_SHUTDOWN_TIMEOUT=0` se cancela de inmediato.

**Arranque (`main.py`, `operacion.load_config`):**
- **Configuración inválida** (un número no numérico o fuera de rango, por ejemplo `MAX_CONCURRENCY=0` o `PORT=99999`): el servicio no arranca, termina con código distinto de 0 y explica cuál variable falló y por qué (RNF-21).
- **Puerto ocupado**: se comparó verificar el puerto **antes** de recuperar el historial, vigilar solo la tarea del servidor, y abrir el socket con `start_serving=False` (más limpio, pero cambia el contrato de `entrada.main`). Se eligió **verificar antes**, para no lanzar trabajos recuperados en un servicio que no podrá atender a nadie. **Además**, como respaldo, `main.py` espera lo que ocurra primero entre la señal de cierre y la caída de la tarea del servidor (`asyncio.wait(..., FIRST_COMPLETED)`); si el servidor se cae, se cierra con código 1 y el evento `SERVICE_ERROR`.
- **Eventos del ciclo de vida en la bitácora (RF-14):** `SERVICE_STARTED` (incluye la configuración usada, sin datos sensibles; RNF-15), `SHUTDOWN_STARTED`, `SERVICE_STOPPED` y `SERVICE_ERROR`.

## Consecuencias
- Positivas: el cierre siempre termina en un tiempo conocido; no quedan procesos vivos al apagar (RNF-25, RNF-30); ningún trabajo en cola se pierde; los errores de arranque son claros e inmediatos.
- Negativas: los trabajos más largos que `SHUTDOWN_TIMEOUT` se cancelan al apagar (configurable). La verificación del puerto tiene una ventana mínima entre verificar y abrir, cubierta por la vigilancia de la tarea del servidor.
- Riesgos y mitigación: un proceso que escapó de su grupo (límite de ADR-008) puede retener los pipes, y el estado final no alcanzaría a registrarse en el margen de 5 s. En ese caso el servicio sale de todos modos; el trabajo queda RUNNING en la base y la siguiente recuperación lo marca `INTERRUPTED` (ADR-010).
