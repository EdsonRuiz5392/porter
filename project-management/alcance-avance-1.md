# Alcance del Avance 1 — qué implementar y hasta dónde

Ya tenemos el esqueleto completo en `src/`, con todas las funciones y sus docstrings. Pero no todo lo que está ahí hay que implementarlo ya — bastante de lo que ven en los contratos es para Hito 2 y 3. Para no perder tiempo ni pisarnos el trabajo, aquí les dejo exactamente qué implementar en cada archivo para este primer avance, y hasta qué punto.

El avance solo pide: enviar un trabajo, obtener su ID, ejecutarlo como proceso separado, consultar su estado, listar trabajos, cancelarlo, obtener su código de salida, y que un comando inválido no tumbe el servicio. Nada de operación remota todavía.

Para cada función les pongo una de tres etiquetas:
- **Completa**: impleméntenla tal como dice su docstring.
- **Mínima**: `main.py` la llama sin condición al arrancar o al cerrar el servicio, así que aunque su comportamiento final sea de otro hito, necesita algo que no truene.
- **Sin tocar**: se queda con su `raise NotImplementedError`, porque nadie la llama todavía en este avance.

## `comun/models.py`
Nadie tiene que tocarlo, ya está completo.

## `comun/protocolo.py` — Juan
| Función | Alcance |
|---|---|
| `read_message` | Completa |
| `write_message` | Completa |

## `servicio/entrada.py` — Juan
| Función | Alcance |
|---|---|
| `handle_client` | Completa, pero solo necesitamos rutear `submit`, `status`, `list` y `cancel`. Todavía no hace falta `output` ni `health`. Sí hay que atrapar `InvalidRequestError` de `control` y responder con un mensaje `"error"` — ahí es donde cumplimos lo de "manejar comandos inválidos sin tumbar el servicio". |
| `main` | Completa en la parte de arrancar el servidor (`asyncio.start_server` + `serve_forever`), pero pueden omitir por completo la validación de `allowed_networks` — aceptamos cualquier conexión por ahora, no se requiere operación remota en este avance. |

## `gestion_trabajos/cola.py` — Dylan
Las seis funciones (`__init__`, `is_full`, `enqueue`, `dequeue`, `remove`, `size`) van **completas** — son sencillas, no vale la pena posponer ninguna. Usen un `max_size` generoso (por ejemplo 100) para que en la práctica no se llene; el rechazo explícito de cola llena (RF-25) es de Hito 2.

## `gestion_trabajos/control.py` — Dylan
| Función | Alcance |
|---|---|
| `submit` | Completa, **excepto** el paso de deduplicar por `client_request_id` — sáltenlo, traten siempre la solicitud como nueva |
| `get`, `list` | Completas |
| `request_cancel` | Completa |
| `mark_running`, `mark_finished` | Completas |
| `_try_dispatch`, `_run_job` | Completas — aquí vive lo de ejecutar como proceso separado y obtener el código de salida |
| `get_output` | Sin tocar — nadie la llama todavía |
| `recover_on_startup` | Mínima: que solo haga `return` sin hacer nada real — `main.py` la llama siempre al arrancar |
| `is_accepting`, `stop_accepting`, `running_count`, `queued_count`, `recent_errors_count` | Mínimas (una variable cada una) — `operacion.shutdown()` las necesita al presionar Ctrl+C |

## `gestion_trabajos/launcher.py` — Marcos
Las tres funciones (`start`, `cancel`, `stream_output`) van **completas** — es el corazón de este avance.

## `servicio/persistencia.py` — Ángel
| Función | Alcance |
|---|---|
| `__init__`, `save_job`, `load_job` | Completas |
| `load_all` | Sin tocar — nadie la llama en este avance |
| `find_by_client_request_id` | Sin tocar — como no deduplicamos todavía en `submit`, no hace falta |

## `servicio/bitacora.py` — Ángel
`log_event` va **completa**. No está en la lista de funcionalidad mínima del avance, pero `control.submit()` la usa en su flujo normal — si no existe, se cae `control.py` con ella.

## `servicio/operacion.py` — Ángel
| Función | Alcance |
|---|---|
| `load_config` | Completa — `main.py` la llama primero que nada, sin ella no arranca el servicio |
| `shutdown` | Mínima: que llame a `job_manager.stop_accepting()` y regrese, sin esperar de verdad a que todo termine |
| `health_summary`, `check_rate_limit` | Sin tocar — nadie las llama en este avance |

## `cliente/cli.py` — Dylan
`_leer_configuracion_conexion` y `_enviar_solicitud` van **completas**. `main` también, pero solo reconociendo `submit`, `status`, `list` y `cancel`.

## `servicio/main.py`
Ya viene resuelto, nadie tiene que tocarlo.

---

**Por qué existen las "mínimas"**: `main.py` llama a `load_config()`, `recover_on_startup()` y `shutdown()` sin condición. Su comportamiento completo (recuperar el historial de verdad, cerrar esperando a que todo termine) es de Hito 2 — pero necesitamos una versión que no truene, para poder arrancar y detener el servicio durante nuestras pruebas de este avance.

Cualquier duda de qué le toca a cada quien, revisen `matriz-responsabilidades.md`; para el detalle de qué hace cada función paso a paso, está en `modulos-explicados.md`.
