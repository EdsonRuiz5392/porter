# Cómo funciona cada módulo — JobRunner (Name Porter)

Este documento es para explicar, en prosa simple, **qué hace cada módulo y qué necesita saber de los demás**. 

Es el complemento narrado de `contratos-interfaces.md`, que define las interfaces y firmas de las funciones, y de `mapa-de-uso.md`, que muestra las relaciones de uso entre los módulos.

Los módulos del proyecto contienen únicamente sus contratos, mediante `raise NotImplementedError`. 

Se describe el comportamiento que deberá cumplir cada función cuando sea implementada, a definir todavía una implementación concreta.

Nota: Consideremos que algunos elementos pueden ser inexactos, la prosa simple ayuda a entender pero es importante apegarse a las consideraciones de los 
docstrings de las funciones (Contratos) con aspectos mas exactos y actualizados para una implementación mas conciente o exacta; aún con eso puede haber ciertas partes logicas que ajustar. Esos posibles ajustes se determinarán durante la implementación de cada módulo.

---

## `models.py` — el vocabulario compartido

No hace nada por sí solo: define `JobStatus` (los 5 estados posibles) y `Job` (la "ficha" de un trabajo, con todos sus datos). Cuando cualquier módulo dice "regreso un `Job`", se refiere exactamente a esta ficha.

---

## `comun/protocolo.py` — cómo se empacan y desempacan los mensajes

**Qué hace**: convierte un mensaje (un diccionario, como `{"type": "submit", ...}`) en bytes para mandar por la red, y al revés.

**`read_message`**: lee primero 4 bytes que dicen cuánto mide el mensaje. Si es más grande de lo permitido, corta ahí (protección contra mensajes gigantes). Si no, espera a que lleguen todos los bytes del mensaje (aunque lleguen repartidos en pedazos) y los convierte de JSON a diccionario.

**`write_message`**: al revés — convierte el diccionario a JSON, mide cuánto pesa, escribe primero ese tamaño y luego el mensaje.

**Las excepciones** (`MessageTooLargeError`, `InvalidMessageError`) existen para que quien use estas funciones (`entrada.py`) pueda distinguir "el mensaje era demasiado grande" de "el mensaje no era JSON válido", y responder con el código de error correcto en cada caso, sin que el servicio se caiga.

**Quién lo usa**: `entrada.py` (para leer lo que pide el cliente y responderle) y `cli.py` (igual, pero del otro lado).

---

## `gestion_trabajos/cola.py` — la fila de espera

**Qué hace**: guarda IDs de trabajos que esperan su turno, con un límite máximo.

**`is_full` / `enqueue` / `dequeue` / `size`**: lo esperado — revisar si está llena, meter uno al final, sacar el que lleva más tiempo esperando, contar cuántos hay.

**`remove(job_id)`**: esta es la que fácilmente se pasa por alto. Cuando alguien cancela un trabajo que todavía está `QUEUED` (nunca llegó a correr), hay que sacarlo de la fila — si no, seguiría "ocupando un lugar" en la cola aunque ya esté cancelado, y eso haría que la cola pareciera más llena de lo que realmente está.

**Qué necesita de otros módulos**: nada, es independiente.

---

## `gestion_trabajos/launcher.py` — quien de verdad prende y apaga procesos

**Qué hace**: es el único módulo que toca al sistema operativo directamente.

**`start`**: crea el proceso hijo de verdad, completamente separado del servicio (RF-04). Regresa un objeto con su PID real y acceso a lo que va imprimiendo.

**`cancel`**: primero pide "por favor" (SIGTERM), espera un tiempo de gracia, y si no obedece, lo mata a la fuerza (SIGKILL). Es el plan B para que un trabajo nunca se quede corriendo para siempre.

**`stream_output`**: va guardando lo que el proceso imprime, stdout y stderr en archivos separados. El detalle importante aquí es que hay que leer los dos **al mismo tiempo**, no uno después del otro — si un proceso llena el "buzón" de una de sus salidas mientras nadie lo está vaciando, se queda esperando ahí trabado, y nunca terminaría. Cuando el proceso termina, regresa su código de salida (un número negativo significa que lo mató una señal, y eso también hay que guardarlo como información útil).

**Qué necesita de otros módulos**: nada del proyecto, solo capacidades de Python.

---

## `gestion_trabajos/control.py` — quien decide y coordina todo

**Qué hace**: es el "cerebro". No prende procesos, ni guarda en disco, ni escribe la cola él mismo — usa a `launcher`, `persistencia` y `bitacora` como herramientas, y decide **qué hacer y en qué orden**.

**Al crearlo** (`__init__`), además de guardarse los otros módulos, prepara su propia memoria: cuántos trabajos corren de verdad ahora, un diccionario de "procesos activos" (para poder cancelarlos), si sigue aceptando trabajos, y un contador de errores. También necesita llevar la cuenta de cuántos trabajos ya se sacaron de la cola pero todavía no terminan de arrancar — es como cuando un restaurante reserva una mesa antes de que llegue el cliente: si no se reserva, dos meseros podrían sentar a más gente de la que caben las mesas, porque ninguno sabe todavía que el otro ya prometió un lugar. Sin esta reserva, si llegan dos solicitudes casi al mismo tiempo, ambas podrían "ver" que hay espacio libre y arrancar, aunque juntas se pasen del límite.

**`submit`** — paso a paso: revisa que el servicio no esté cerrando, revisa si es un duplicado (por `client_request_id`), valida que la solicitud tenga sentido, revisa que la cola no esté llena, y si todo bien: crea el `Job`, lo guarda, avisa a la bitácora, lo encola, e intenta arrancarlo de inmediato. Un detalle extra: aunque ya revisó duplicados, dos solicitudes idénticas podrían llegar tan juntas que ambas "vean" que no existe todavía antes de que cualquiera termine de guardar — por eso `persistencia` debe rechazar por sí misma un `client_request_id` repetido, y `submit` debe saber recuperarse de ese caso en vez de fallar.

**`get` / `list`**: le preguntan directamente a `persistencia`.

**`request_cancel`**: si el trabajo está en cola, simplemente lo saca de ahí (con `cola.remove`) y lo marca cancelado. Si ya está corriendo, le pide a `launcher.cancel` que lo detenga de verdad. Si a un mismo trabajo le piden cancelar dos veces casi al mismo tiempo, la segunda vez no debe volver a mandar otra señal — debe darse cuenta de que ya hay una cancelación en curso.

**`get_output`**: esta función responde a la parte de RF-11 que antes faltaba — no basta con guardar la salida de un trabajo, alguien tiene que poder pedirla de vuelta. Busca el trabajo, encuentra en qué archivo quedó guardada su salida (stdout o stderr, según se pida), y la lee.

**`mark_running` / `mark_finished`**: actualizan el estado del trabajo cuando arranca de verdad y cuando termina, respectivamente. `mark_finished` es también quien le da su turno al siguiente trabajo en cola, para que uno terminando no bloquee la atención de los demás.

**`_try_dispatch` / `_run_job`** (funciones internas, con guion bajo): son las piezas que realmente sacan trabajos de la cola y los ponen a correr. Sin ellas, los trabajos se quedarían esperando para siempre — nada los sacaría de ahí.

**`recover_on_startup`**: al arrancar el servicio, trae el historial guardado; lo que se quedó `RUNNING` (de antes de un reinicio) ya no tiene proceso real detrás, así que se marca como fallido con una nota de "interrumpido"; lo que se quedó `QUEUED` se vuelve a formar en la fila.

**`is_accepting` / `stop_accepting` / `running_count` / `queued_count` / `recent_errors_count`**: pequeñas funciones de consulta que usa `operacion.py` para armar el resumen de salud y para saber cuándo ya es seguro cerrar el servicio.

---

## `persistencia.py` — la memoria del sistema

**Qué hace**: guarda los trabajos en SQLite para que sobrevivan a un reinicio.

**`save_job` / `load_job` / `load_all`**: guardar uno, buscar uno por ID, traer todos (esto último se usa una sola vez, al arrancar, para recuperar el historial).

**`find_by_client_request_id`**: busca si ya existe un trabajo creado con ese mismo identificador, para que `control.py` pueda detectar duplicados.

**Sobre `DuplicateClientRequestError`**: la tabla de la base de datos debe tener una regla que le impida guardar dos trabajos con el mismo `client_request_id` (una restricción UNIQUE). Esto es una segunda capa de protección, además de la revisión que ya hace `control.py` antes de crear un trabajo — porque dos solicitudes casi simultáneas podrían pasar esa primera revisión al mismo tiempo, y solo la base de datos, al final, puede garantizar que no se dupliquen de verdad.

---

## `bitacora.py` — el diario de eventos

**`log_event`**: escribe una línea con fecha y hora, el ID del trabajo (o un guion si no aplica), el nombre del evento, y cualquier detalle, al final de un archivo. Sin dependencias de nadie más.

---

## `operacion.py` — la administración del servicio

**`load_config`**: lee la configuración del entorno (puerto, límites, carpeta de datos, etc.) y la regresa organizada.

**`shutdown`**: le dice a `control` que deje de aceptar trabajos nuevos, y espera a que los que ya estaban corriendo terminen solos antes de cerrar de verdad.

**`health_summary`**: junta un resumen preguntándole a `control` cuántos hay corriendo, en cola, y si sigue aceptando — sin necesitar saber cómo `control` guarda esos números por dentro.

**`check_rate_limit`**: una comprobación simple de "¿ya se pasó del límite?".

---

## `entrada.py` — la puerta de llegada

**Qué hace**: es lo primero que toca cualquier solicitud. Traduce bytes de red a un mensaje entendible, decide a qué función de `control` (u `operacion`, para `health`) corresponde, y traduce la respuesta de vuelta a bytes.

**`handle_client`**: por cada tipo de mensaje (`submit`, `status`, `list`, `cancel`, `output`, `health`) llama a la función correspondiente. Si `control` lanza uno de sus errores (`InvalidRequestError`, `QueueFullError`, `ServiceClosingError`, o "no encontrado"), lo convierte en un mensaje `"error"` con su código, en vez de dejar que tumbe la conexión.

**`main`**: pone al servicio a escuchar en la red de verdad, y se queda corriendo indefinidamente (con `server.serve_forever()`) hasta que algo lo cancele desde afuera — así es como el servicio "se mantiene ejecutándose" en vez de terminar apenas arranca. Necesita que le entreguen ya armado a `control` (aquí llamado `job_manager`) y el tamaño máximo de mensaje permitido, para poder pasárselos a `handle_client` en cada conexión nueva.

**Qué necesita de otros módulos**: de `protocolo`, leer/escribir mensajes. De `control`, todas sus funciones públicas. De `operacion`, solo `health_summary`.

---

## `cli.py` — lo que la persona usuaria escribe en la terminal

**Qué hace**: traduce lo que alguien escribió (`submit backup.sh`, por ejemplo) en un mensaje del protocolo, lo manda, y muestra la respuesta.

**`_leer_configuracion_conexion`**: el CLI es un programa completamente aparte del servicio (puede incluso correr en otra máquina), así que no debe importar nada de `servicio.operacion` — en vez de eso, lee directamente sus propias tres variables de entorno (host, puerto, tamaño máximo de mensaje).

**`_enviar_solicitud`**: la única función `async` de este archivo — abre la conexión, manda el mensaje, lee la respuesta, cierra la conexión.

**`main`**: lee lo que escribió la persona, muestra ayuda si hace falta, arma el mensaje correcto, usa `asyncio.run(_enviar_solicitud(...))` para mandarlo (porque `main` en sí no es `async`, pero `protocolo.py` sí lo es), y termina con código `0` si salió bien o distinto de `0` si hubo un error (RF-17) — así cualquier script que use este CLI puede saber si tuvo éxito sin tener que leer el texto que imprimió.

---

## `servicio/main.py` — quien arma todas las piezas y arranca de verdad

Este archivo **ya viene resuelto**, no es un contrato pendiente — es el único que conoce a todos los módulos del servicio a la vez y los conecta en orden: lee la configuración, construye `persistencia`, `bitacora`, `cola`, `launcher` y `control`, le pide a `control` que recupere el historial (RF-13), arranca `entrada.main(...)`, y espera una señal para cerrar todo de forma ordenada (RF-15). Vale la pena leerlo para entender cómo encajan las piezas, aunque no haya nada que programar ahí.
