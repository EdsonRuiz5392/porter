# Mapa de uso entre módulos — JobRunner

Complemento de `contratos-interfaces.md` (cómo funciona cada módulo) y `modulos-explicados.md` (explicación en prosa). 
Este archivo detalla los modulos en base a las funciónes/relaciones que ejercen con los demás, en la colección de los conceptos adoptados en la arquitectura alcanzada, esto es: **quién llama a cada módulo, cuándo, y con qué función**.

El objetivo es mostrar de forma concreta cómo se distribuyen las responsabilidades y cómo fluye la comunicación entre los distintos componentes del sistema.

---

## models (Job, JobStatus)

Es utilizado por: todos los demás módulos, para crear, leer o pasar información de un trabajo.

---

## protocolo

Es utilizado por: `entrada`, `cli`.
- `entrada` lo usa al recibir una solicitud (`read_message`) y al responder (`write_message`).
- `cli` lo usa al mandar una solicitud (`write_message`) y al leer la respuesta (`read_message`).

---

## cola

Es utilizada por: `control`.
- Al llegar un trabajo nuevo: `is_full()`, y si hay espacio, `enqueue(job_id)`.
- Al arrancar el siguiente: `dequeue()`.
- Al cancelar uno que sigue en cola: `remove(job_id)`.
- Para el resumen de salud: `size()`.

---

## launcher

Es utilizado por: `control`.
- Al pasar un trabajo de `QUEUED` a `RUNNING`: `start(command, args, job_id)`.
- Al cancelar uno que ya corre: `cancel(proc, grace_seconds)`.
- Para capturar su salida mientras corre: `stream_output(proc, stdout_path, stderr_path)`.

---

## persistencia

Es utilizada por: `control`.
- Crear o actualizar un trabajo: `save_job(job)`.
- Consultar uno por ID: `load_job(job_id)`.
- Al arrancar el servicio: `load_all()`.
- Revisar duplicados: `find_by_client_request_id(client_request_id)`.

---

## bitacora

Es utilizada por: `control`.
- Eventos: `CREATED`, `STARTED`, `FINISHED`, `CANCELED`, `REJECTED` → `log_event(job_id, event, detail)`.

---

## control

Es utilizado por: `entrada` (operaciones de trabajos), `operacion` (salud y cierre), `main` (recuperación al arrancar).

- `entrada` lo usa según el tipo de mensaje: `submit`, `get`, `list`, `request_cancel`, `get_output`.
- `operacion` lo usa para: `is_accepting()`, `running_count()`, `queued_count()`, `recent_errors_count()`, `stop_accepting()`.
- `main` lo usa una sola vez, al arrancar: `recover_on_startup()`.

---

## operacion

Es utilizada por: `entrada` (mensaje `health`), `main` (configuración y cierre).

- `entrada`: `health_summary(job_manager)`.
- `main`: `load_config()`, `shutdown(job_manager)`.

---

## entrada

Es utilizado por: `main`, que lo arranca una sola vez con `main(host, port, allowed_networks, job_manager, max_message_bytes)`.

---

## cli

Es utilizado por: nadie — lo ejecuta directamente la persona usuaria en la terminal.

---

## main

Es utilizado por: nadie — es el punto de entrada del proceso del servicio (`python -m src.servicio.main`).

---

## Vista rápida (quién depende de quién)

```
main ──► operacion (config, recover, shutdown)
main ──► entrada (arranca el servidor)

cli ────────► protocolo
                  ▲
                  │
entrada ──────────┴──► operacion ──► control (health/shutdown)
   │
   ▼
control ──► cola
   │  │
   │  └──► launcher
   │
   ├──► persistencia
   └──► bitacora
```

Una flecha `A ──► B` significa "A usa a B". Ningún módulo de la parte de abajo (`cola`, `launcher`, `persistencia`, `bitacora`) llama de vuelta hacia `control` — la comunicación va en un solo sentido.
