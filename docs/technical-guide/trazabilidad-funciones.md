# Trazabilidad por función — JobRunner (Name Porter)

Este documento relaciona cada función con los requisitos funcionales (RF) y no funcionales (RNF) que contribuye a cumplir. La asignación/interpretación ya está definida en las tablas de cada módulo, por lo que al crear un Issue basta con localizar la función correspondiente y tomar de allí los RF/RNF asociados.

Considerar casos en los que se programe algo que no parece estar aqui (comentarlo con el equipo, producto: Angel), aunque esto puede deberse a que simplemente no haya un RF/RNF asociado a esa clase de tarea, (Podria quedarse simplemente sin RF/RNF por pertenecer a otro nivel no a esta trazabilidad).

---

## `comun/protocolo.py`

| Función / elemento | RF | RNF |
|---|---|---|
| `read_message` | RF-21 | RNF-14, RNF-24 |
| `write_message` | RF-21 | RNF-24 |
| `MessageTooLargeError` | — | RNF-14 |
| `InvalidMessageError` | RF-02 (apoyo) | RNF-14 |

## `gestion_trabajos/cola.py`

| Función | RF | RNF |
|---|---|---|
| `__init__` | RF-03 | — |
| `is_full` | RF-25 | RNF-29 |
| `enqueue` | RF-03 | RNF-07 |
| `dequeue` | RF-03 | — |
| `remove` | RF-10 (apoyo) | RNF-27 |
| `size` | RF-24 (apoyo) | — |

## `gestion_trabajos/control.py`

| Función | RF | RNF |
|---|---|---|
| `__init__` | RF-05 | RNF-27 |
| `submit` | RF-01, 02, 03, 06, 07, 25, 27; RF-15 (apoyo) | RNF-08, RNF-27, RNF-29 |
| `get` | RF-08 | — |
| `list` | RF-09 | — |
| `request_cancel` | RF-26; RF-10 (apoyo) | RNF-27 |
| `get_output` | RF-11 (apoyo) | — |
| `mark_running` | RF-06, RF-07 | — |
| `mark_finished` | RF-04, RF-06, RF-07 | RNF-27 |
| `_try_dispatch` | RF-04, RF-05 | RNF-07, RNF-29 |
| `_run_job` | RF-04, RF-07; RF-29 (apoyo) | RNF-09 (apoyo) |
| `recover_on_startup` | RF-13 (apoyo) | RNF-10, RNF-31 |
| `is_accepting` / `stop_accepting` | RF-15 (apoyo) | — |
| `running_count` / `queued_count` / `recent_errors_count` | RF-24 (apoyo) | — |

## `gestion_trabajos/launcher.py`

| Función | RF | RNF |
|---|---|---|
| `start` | RF-04 | RNF-03 |
| `cancel` | RF-10, RF-30 | RNF-27 (apoyo, junto a RF-26) |
| `stream_output` | RF-07, RF-11, RF-29 | RNF-09, RNF-33 |

## `servicio/persistencia.py`

| Función / elemento | RF | RNF |
|---|---|---|
| `__init__` | RF-12 | RNF-28 |
| `save_job` | RF-12 | RNF-11, RNF-28 |
| `load_job` | RF-08 (apoyo) | — |
| `load_all` | RF-13 | RNF-06, RNF-31 |
| `find_by_client_request_id` | RF-27 | — |
| `DuplicateClientRequestError` | RF-27 | RNF-27 |

## `servicio/bitacora.py`

| Función | RF | RNF |
|---|---|---|
| `log_event` | RF-14 | RNF-15, RNF-22 |

## `servicio/operacion.py`

| Función | RF | RNF |
|---|---|---|
| `load_config` | RF-16 | — |
| `shutdown` | RF-15 | RNF-30 |
| `health_summary` | RF-24 | — |
| `check_rate_limit` | RF-23 | RNF-29 |

## `servicio/entrada.py`

| Función | RF | RNF |
|---|---|---|
| `handle_client` | RF-18, RF-19, RF-21, RF-22, RF-28 | RNF-08, RNF-14, RNF-24 |
| `main` | RF-18, RF-20 | RNF-12, RNF-13, RNF-25, RNF-26 |

## `cliente/cli.py`

| Función | RF | RNF |
|---|---|---|
| `_leer_configuracion_conexion` | RF-16 (lado cliente) | — |
| `_enviar_solicitud` | RF-18 (lado cliente) | — |
| `main` | RF-17 | — |

## `servicio/main.py`

No implementa RF/RNF propios (es ensamblaje). Su única relación: llama a `control.recover_on_startup()` (RF-13) y a `operacion.shutdown()` (RF-15) en el momento correcto.

---

## Propuesta de formato de uso al abrir un Issue

1. Ubica la función en la tabla de su archivo.
2. Copia los RF/RNF de esa fila a la descripción del Issue.
3. Crear (si no existen ya) las etiquetas de GitHub correspondientes a esos números y asígnarlas al Issue.
4. Si el Issue agrupa varias funciones relacionadas (válido para funciones chicas, como toda `cola.py` junta), simplemente juntar los RF/RNF de todas las filas que se agruparon.

"(apoyo)" en la tabla significa: esta función ayuda a que ese RF/RNF se cumpla, pero la responsabilidad de defenderlo en la revisión sigue siendo de quien lo tiene asignado en `project-management/matriz-responsabilidades.md` — no cambia quién es el dueño del requisito, solo aclara en qué código vive el mecanismo.
