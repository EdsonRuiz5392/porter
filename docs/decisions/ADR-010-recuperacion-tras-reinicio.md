# ADR-010: Recuperación tras reinicio (Python)

- Estado: Aceptado
- Fecha: 2026-10-20
- Requisitos relacionados: RF-12, RF-13, RF-25, RNF-10, RNF-28, RNF-30, RNF-31
- Relación con otros ADR: **Complementa ADR-003** (persistencia en SQLite) con la semántica de recuperación, que es una de las "decisiones funcionales obligatorias". Usa los grupos de procesos de ADR-008.

## Contexto y problema
ADR-003 garantiza que la base sobreviva a una caída, pero no definía **qué pasa con cada trabajo** al reiniciar. Las pruebas encontraron:

1. **Huérfanos.** Tras `kill -9` al servicio con 3 trabajos corriendo, los 3 procesos siguieron vivos sin control. Al reiniciar se marcaban FAILED, pero seguían ahí: llegó a haber 4 procesos vivos con un límite de 3 (RNF-30).
2. **El servicio no arrancaba** si en la base había más trabajos QUEUED que `JOBRUNNER_MAX_QUEUE`, porque `cola.enqueue()` lanzaba `QueueFullError` dentro de `recover_on_startup`. Pasaba por los trabajos fantasma (ver ADR-006), pero también puede pasar **legítimamente** si el administrador baja `MAX_QUEUE` entre un arranque y otro.
3. **Riesgo de reutilización de PID.** Para terminar un huérfano hay que usar el PID guardado en la base, pero Linux puede haber asignado ese número a otro programa.

## Decisión 1: estado de cada trabajo al reiniciar

### Alternativas
- **A. Volver a ejecutar los que estaban RUNNING.** Rechazada: un comando no necesariamente es seguro de repetir (por ejemplo, un respaldo incremental o el envío de un correo).
- **B. Marcarlos FAILED con código -1 y el evento `INTERRUPTED` en la bitácora.** El diagnóstico queda registrado.
- **C. Crear un estado nuevo `INTERRUPTED`.** Rechazada: RF-06 define los estados y uno nuevo obliga a cambiar el protocolo y los clientes; el diagnóstico ya está en la bitácora.

### Decisión: B
| Estado en la base al arrancar | Qué se hace |
|---|---|
| SUCCEEDED / FAILED / CANCELED | No se toca |
| QUEUED | Vuelve a la cola en su orden original (`load_all` ordena por `submitted_at`) y se ejecuta |
| RUNNING | Se termina su grupo de procesos si sigue vivo y es nuestro (Decisión 3), y se marca FAILED (-1) con `INTERRUPTED` |

## Decisión 2: hay más pendientes que lugares en la cola

### Alternativas
- **A. Marcar el exceso como fallido.** Rechazada: pierde trabajos que ya fueron aceptados y nunca corrieron (RF-25: "sin perder trabajos aceptados").
- **B. No arrancar y pedir intervención.** Rechazada: deja el servicio abajo.
- **C. Recuperarlos todos aunque se exceda el límite, y rechazar envíos nuevos hasta que la cola baje.**

### Decisión: C
`JOBRUNNER_MAX_QUEUE` limita la **admisión de trabajos nuevos**, no la conservación de los ya aceptados. Se agregó `cola.restore(job_id)`, que reencola sin aplicar el límite y que solo se usa en la recuperación (se registra en el contrato de interfaces). Mientras la cola esté por encima del límite, `is_full()` devuelve `True` y los envíos nuevos reciben `QUEUE_FULL`. Se registra el evento `RECOVERY_OVER_CAPACITY` con las cifras.

## Decisión 3: procesos que siguen vivos tras una caída

### Alternativas
- **A. No tocarlos** (implementación anterior). Viola RNF-30.
- **B. `os.killpg(pid_guardado)` sin verificar.** Rechazada: si el número fue reutilizado, se mataría el grupo de otro programa.
- **C. `os.killpg` con verificación de identidad.**

### Decisión: C (`control._terminar_grupo_huerfano`)
Se compara la hora de arranque real del proceso con el `started_at` guardado en la base. La hora real se calcula con el campo 22 de `/proc/<pid>/stat` más el `btime` de `/proc/stat`, con una tolerancia de ±2 s.

| Lo que se encuentra | Qué se hace | Evento |
|---|---|---|
| El proceso existe y la hora coincide | Es nuestro: `os.killpg(pid, SIGKILL)` | `ORPHAN_KILLED` |
| El proceso existe y la hora **no** coincide | Es de otro programa: no se toca | `ORPHAN_SKIPPED` |
| No existe ningún proceso con ese PID | Se intenta `os.killpg` de todos modos: si el grupo existe, solo pueden quedar descendientes nuestros, porque POSIX no reutiliza el ID de un grupo que aún tiene miembros | `ORPHAN_KILLED` si había algo |
| Sin permiso | No se toca | `ORPHAN_ERROR` |

## Consecuencias
- Positivas: cumple RNF-10, RNF-30 y RNF-31; nunca se pierde un trabajo aceptado; el servicio arranca aunque cambie `MAX_QUEUE`; nunca se mata un proceso ajeno por un PID reutilizado.
- Negativas: entre la caída y el reinicio los huérfanos siguen corriendo; se limpian al reiniciar, no antes. La verificación depende de `/proc`, lo cual es aceptable porque la plataforma declarada es Linux (RNF-01).
- Riesgos y mitigación:
  - Si el reloj del sistema cambia mucho entre la caída y el reinicio, la verificación puede no reconocer un proceso propio. Entonces **no lo mata** (falla segura) y lo registra como `ORPHAN_SKIPPED` → límite conocido.
  - Los trabajos lanzados por versiones anteriores del código no tienen grupo propio y no se pueden limpiar → **borrar `data/` al migrar a esta versión**. Además, una base vieja puede contener trabajos fantasma que ahora sí se ejecutarían.
