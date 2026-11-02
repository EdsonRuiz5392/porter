# Cómo funciona cada módulo — JobRunner (Name Porter)

Este documento es para explicar, en prosa simple, **qué hace cada módulo y qué necesita saber de los demás**. 

Es el complemento narrado de `contratos-interfaces.md`, que define las interfaces y firmas de las funciones, y de `mapa-de-uso.md`, que muestra las relaciones de uso entre los módulos.

Describe el comportamiento implementado en el Avance 02. Si algo no coincide con el código, manda el código; las firmas exactas están en `contratos-interfaces.md`, y las razones, en los ADR.

---

## `models.py` — el vocabulario compartido

No hace nada por sí solo: define `JobStatus` (los 5 estados posibles) y `Job` (la "ficha" de un trabajo, con todos sus datos). Cuando cualquier módulo dice "regreso un `Job`", se refiere exactamente a esta ficha.

---

## `comun/protocolo.py` — cómo se empacan y desempacan los mensajes

**Qué hace**: convierte un mensaje (un diccionario, como `{"type": "submit", ...}`) en bytes para mandar por la red, y al revés.

**`read_message`**: lee primero 4 bytes que dicen cuánto mide el mensaje. Si es más grande de lo permitido, corta ahí (protección contra mensajes gigantes). Si no, espera a que lleguen todos los bytes del mensaje (aunque lleguen repartidos en pedazos) y los convierte de JSON a diccionario.

**`write_message`**: al revés — convierte el diccionario a JSON, mide cuánto pesa, escribe primero ese tamaño y luego el mensaje.

**Las excepciones** (`MessageTooLargeError`, `InvalidMessageError`) permiten que `entrada.py` responda con un error útil antes de cerrar la conexión, sin que el servicio se caiga.

**Quién lo usa**: `entrada.py` (para leer lo que pide el cliente y responderle) y `cli.py` (igual, pero del otro lado).

---

## `gestion_trabajos/cola.py` — la fila de espera

**Qué hace**: guarda IDs de trabajos que esperan su turno, con un límite máximo.

**`is_full` / `enqueue` / `dequeue` / `size`**: lo esperado — revisar si está llena, meter uno al final, sacar el que lleva más tiempo esperando, contar cuántos hay.

**`remove(job_id)`**: esta es la que fácilmente se pasa por alto. Cuando alguien cancela un trabajo que todavía está `QUEUED` (nunca llegó a correr), hay que sacarlo de la fila — si no, seguiría "ocupando un lugar" en la cola aunque ya esté cancelado, y eso haría que la cola pareciera más llena de lo que realmente está.

**`restore(job_id)`**: reencola sin aplicar el límite. Solo se usa al recuperar tras un reinicio, para no perder trabajos ya aceptados aunque ahora no quepan (ADR-010).

**Qué necesita de otros módulos**: nada, es independiente.

---

## `gestion_trabajos/launcher.py` — quien de verdad prende y apaga procesos

**Qué hace**: es el único módulo que toca al sistema operativo directamente.

**`start`**: crea el proceso hijo en su **propio grupo de procesos** (`start_new_session=True`), separado del servicio (RF-04), y sin entrada estándar. Así se puede terminar a toda su "familia" y el Ctrl+C de la terminal del servicio no le llega. Regresa un objeto con su PID real y acceso a lo que va imprimiendo.

**`cancel`**: primero pide "por favor" (SIGTERM) a **todo el grupo**, espera el tiempo de gracia a que desaparezca y, si queda alguien, usa SIGKILL. Después recoge el proceso para no dejar zombis.

**`stream_output`**: va guardando lo que el proceso imprime, stdout y stderr en archivos separados, por bloques de bytes, de modo que una línea enorme no rompe la lectura y la salida se puede consultar mientras corre. El detalle importante aquí es que hay que leer los dos **al mismo tiempo**, no uno después del otro — si un proceso llena el "buzón" de una de sus salidas mientras nadie lo está vaciando, se queda esperando ahí trabado, y nunca terminaría. Cuando el proceso termina, regresa su código de salida (un número negativo significa que lo mató una señal, y eso también hay que guardarlo como información útil).

**Qué necesita de otros módulos**: nada del proyecto, solo capacidades de Python.

---

## `gestion_trabajos/control.py` — quien decide y coordina todo

**Qué hace**: es el "cerebro". No prende procesos, ni guarda en disco, ni escribe la cola él mismo — usa a `launcher`, `persistencia` y `bitacora` como herramientas, y decide **qué hacer y en qué orden**.

**Al crearlo** (`__init__`), además de guardarse los otros módulos, prepara su propia memoria: cuántos trabajos corren de verdad ahora, un diccionario de "procesos activos" (para poder cancelarlos), si sigue aceptando trabajos, y un contador de errores. También necesita llevar la cuenta de cuántos trabajos ya se sacaron de la cola pero todavía no terminan de arrancar — es como cuando un restaurante reserva una mesa antes de que llegue el cliente: si no se reserva, dos meseros podrían sentar a más gente de la que caben las mesas, porque ninguno sabe todavía que el otro ya prometió un lugar. Sin esta reserva, si llegan dos solicitudes casi al mismo tiempo, ambas podrían "ver" que hay espacio libre y arrancar, aunque juntas se pasen del límite.

**`submit`** — paso a paso: revisa que el servicio no esté cerrando y valida tipos y tamaños. Después, con el candado `_submit_lock` (un envío a la vez, ADR-006): revisa si el folio ya existe (mismo comando devuelve el original; otro comando es `REQUEST_ID_CONFLICT`, ADR-007), revisa que la cola no esté llena, crea el `Job`, lo guarda, lo encola y avisa a la bitácora. Fuera del candado, intenta arrancarlo. `persistencia` sigue rechazando un folio repetido como red de seguridad.

**`get` / `list`**: le preguntan directamente a `persistencia`.

**`request_cancel`**: si el trabajo está en cola, lo saca (con `cola.remove`) y lo marca cancelado. Si ya salió de la cola, anota la cancelación; si ya tiene proceso, le pide a `launcher.cancel` que lo detenga, y si está arrancando, `_run_job` lo revisa antes y después de lanzarlo. Si piden cancelar dos veces casi al mismo tiempo, solo la primera manda la señal.

**`get_output`**: esta función responde a la parte de RF-11 que antes faltaba — no basta con guardar la salida de un trabajo, alguien tiene que poder pedirla de vuelta. Busca el trabajo, encuentra en qué archivo quedó guardada su salida (stdout o stderr, según se pida), y la lee.

**`mark_running` / `mark_finished`**: actualizan el estado del trabajo cuando arranca de verdad y cuando termina, respectivamente. `mark_finished` es también quien le da su turno al siguiente trabajo en cola, para que uno terminando no bloquee la atención de los demás.

**`_try_dispatch` / `_run_job`** (funciones internas, con guion bajo): son las piezas que realmente sacan trabajos de la cola y los ponen a correr. Sin ellas, los trabajos se quedarían esperando para siempre — nada los sacaría de ahí.

**`recover_on_startup`**: al arrancar el servicio, trae el historial guardado. Lo que se quedó `RUNNING` se marca `FAILED` con una nota de "interrumpido", y antes se termina su grupo de procesos si sigue vivo y se comprueba que sea nuestro. Lo que se quedó `QUEUED` vuelve a la fila con `restore` (ADR-010).

**`cancel_all_running` / `in_progress_count`**: las usa el cierre para cancelar lo que siga corriendo y saber cuándo ya terminó todo.

**`is_accepting` / `stop_accepting` / `running_count` / `queued_count` / `recent_errors_count`**: pequeñas funciones de consulta que usa `operacion.py` para armar el resumen de salud y para saber cuándo ya es seguro cerrar el servicio.

---

## `persistencia.py` — la memoria del sistema

**Qué hace**: guarda los trabajos en SQLite para que sobrevivan a un reinicio.

**`save_job` / `load_job` / `load_all`**: guardar uno (con `ON CONFLICT(id) DO UPDATE`, que nunca borra filas), buscar uno por ID y traer todos (lo usan la recuperación y `list`).

**`find_by_client_request_id`**: busca si ya existe un trabajo creado con ese mismo identificador, para que `control.py` pueda detectar duplicados.

**Sobre `DuplicateClientRequestError`**: la tabla de la base de datos debe tener una regla que le impida guardar dos trabajos con el mismo `client_request_id` (una restricción UNIQUE). Esto es una segunda capa de protección, además de la revisión que ya hace `control.py` antes de crear un trabajo — porque dos solicitudes casi simultáneas podrían pasar esa primera revisión al mismo tiempo, y solo la base de datos, al final, puede garantizar que no se dupliquen de verdad.

---

## `bitacora.py` — el diario de eventos

**`log_event`**: escribe una línea con fecha y hora, el ID del trabajo (o un guion si no aplica), el nombre del evento, y cualquier detalle, al final de un archivo. Sin dependencias de nadie más.

---

## `operacion.py` — la administración del servicio

**`load_config`**: lee la configuración del entorno (puerto, límites, carpeta de datos, etc.), la valida y la regresa organizada. Si un valor es inválido, el servicio no arranca y dice cuál.

**`shutdown`**: le dice a `control` que deje de aceptar trabajos nuevos, espera hasta `timeout` segundos a que terminen los que ya corren y, si queda alguno, lo cancela con el escalamiento normal (ADR-011).

**`health_summary`**: junta un resumen preguntándole a `control` cuántos hay corriendo, en cola, y si sigue aceptando — sin necesitar saber cómo `control` guarda esos números por dentro.

**`check_rate_limit`**: una comprobación simple de "¿ya se pasó del límite?".

---

## `entrada.py` — la puerta de llegada

**Qué hace**: es lo primero que toca cualquier solicitud. Traduce bytes de red a un mensaje entendible, decide a qué función de `control` (u `operacion`, para `health`) corresponde, y traduce la respuesta de vuelta a bytes.

**`handle_client`**: por cada tipo de mensaje (`submit`, `status`, `list`, `cancel`, `output`, `health`) llama a la función correspondiente. Si `control` lanza uno de sus errores (`InvalidRequestError`, `QueueFullError`, `ServiceClosingError`, `RequestIdConflictError`, o "no encontrado"), lo convierte en un mensaje `"error"` con su código, en vez de dejar que tumbe la conexión.

**`main`**: pone al servicio a escuchar en la red de verdad, y se queda corriendo indefinidamente (con `server.serve_forever()`) hasta que algo lo cancele desde afuera — así es como el servicio "se mantiene ejecutándose" en vez de terminar apenas arranca. Necesita que le entreguen ya armado a `control` (aquí llamado `job_manager`) y el tamaño máximo de mensaje permitido, para poder pasárselos a `handle_client` en cada conexión nueva.

**Qué necesita de otros módulos**: de `protocolo`, leer/escribir mensajes. De `control`, todas sus funciones públicas. De `operacion`, solo `health_summary`.

---

## `cli.py` — lo que la persona usuaria escribe en la terminal

**Qué hace**: traduce lo que alguien escribió (`submit backup.sh`, por ejemplo) en un mensaje del protocolo, lo manda, y muestra la respuesta.

**`_leer_configuracion_conexion`**: el CLI es un programa completamente aparte del servicio (puede incluso correr en otra máquina), así que no debe importar nada de `servicio.operacion` — en vez de eso, lee directamente sus propias tres variables de entorno (host, puerto, tamaño máximo de mensaje).

**`_enviar_solicitud`**: la única función `async` de este archivo — abre la conexión, manda el mensaje, lee la respuesta, cierra la conexión.

**`main`**: lee lo que escribió la persona, muestra ayuda si hace falta, arma el mensaje correcto para `submit`, `status`, `list`, `cancel`, `output` o `health`, usa `asyncio.run(_enviar_solicitud(...))` para mandarlo (porque `main` en sí no es `async`, pero `protocolo.py` sí lo es), y termina con código `0` si salió bien o distinto de `0` si hubo un error (RF-17) — así cualquier script que use este CLI puede saber si tuvo éxito sin tener que leer el texto que imprimió.

---

## `servicio/main.py` — quien arma todas las piezas y arranca de verdad

Es el único que conoce a todos los módulos del servicio a la vez y los conecta en orden: valida la configuración, verifica que el puerto esté libre, construye `persistencia`, `bitacora`, `cola`, `launcher` y `control`, le pide a `control` que recupere el historial (RF-13), arranca `entrada.main(...)` y espera SIGINT o SIGTERM para cerrar de forma ordenada (RF-15). Registra los eventos del ciclo de vida del servicio en la bitácora.
