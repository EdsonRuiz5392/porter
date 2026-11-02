# ADR-012: Retención y eliminación de resultados (Python)

- Estado: Aceptado
- Fecha: 2026-10-20
- Requisitos relacionados: RF-12, RNF-05, RNF-06
- Relación con otros ADR: complementa ADR-003 (persistencia). Afecta a ADR-007, porque los folios se liberan si se borran trabajos.

> **Nota:** este ADR no corresponde a un cambio de código. Las especificaciones ("Decisiones funcionales obligatorias") exigen registrar en un ADR la política de **retención y eliminación de resultados**, y ningún ADR anterior la cubría.

## Contexto y problema
Cada trabajo deja una fila en `data/jobs.db` y dos archivos en `data/output/` (stdout y stderr), y la bitácora `data/jobrunner.log` crece con cada evento. Hoy nada se borra. Hay que decidir si el servicio elimina resultados y cuándo.

## Alternativas consideradas

### Alternativa A: conservar todo; el administrador limpia a mano
- Ventajas: no hay código nuevo; nunca se pierde evidencia ni historial (RF-12); cumple RNF-06 (al menos 500 registros sin pérdida).
- Desventajas/riesgos: el disco crece sin límite.

### Alternativa B: borrado automático por antigüedad
- Descripción: eliminar los trabajos **terminados** con más de N días, junto con sus archivos de salida, por ejemplo al arrancar o de forma periódica.
- Ventajas: crecimiento acotado.
- Desventajas/riesgos: más código y más casos de prueba; puede borrar evidencia que todavía se necesita; libera folios (ADR-007), así que un reintento muy tardío crearía un trabajo nuevo.

### Alternativa C: límite por cantidad (conservar los últimos N trabajos)
- Ventajas: un tamaño máximo predecible.
- Desventajas/riesgos: igual que B, y además con mucha carga se podrían borrar resultados recientes.

## Decisión
**Alternativa A** para esta etapa del proyecto. La carga es académica y la evidencia de las pruebas debe conservarse.

**Procedimiento documentado de limpieza (guía de usuario):**
1. Detener el servicio con cierre controlado (ADR-011).
2. Borrar la carpeta `JOBRUNNER_DATA_DIR` **completa**: `jobs.db`, `jobs.db-wal`, `jobs.db-shm`, `output/` y `jobrunner.log`.

Nunca se debe borrar solo `jobs.db` dejando los archivos `-wal` y `-shm`, ni borrar archivos de `output/` de trabajos que siguen en la base.

## Consecuencias
- Positivas: comportamiento simple y verificable; nada se pierde sin intervención explícita.
- Negativas: crecimiento ilimitado del disco; `health` no reporta el espacio usado.
- Riesgos y mitigación: llenar el disco haría fallar las escrituras (SQLite y salidas) → se documentará en la guía de usuario como límite conocido. **Mejora futura:** la Alternativa B, con su propio ADR, que deberá definir también qué pasa con los folios liberados.
