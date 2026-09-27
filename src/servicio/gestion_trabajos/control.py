"""
El "cerebro" de los trabajos: decide qué pasa con cada uno y en qué momento,
usando a cola.py, launcher.py y persistencia.py como sus herramientas.
Responsable: Dylan.
Ver docs/technical-guide/contratos-interfaces.md, sección 7.
Se apoya en: ADR-005 (saturación y duplicados), ADR-001 (modelo de concurrencia).
RF que cubre: 01, 02, 03, 05, 06, 07, 08, 09, 17, 25, 27.

Nota propia RF compartidos. Algunas funciones de aquí abajo (cancelar,
consultar la salida, recuperar al arrancar, salud, cierre) apoyan RF
correspondientes a (RF-04/10 de Marcos, RF-11/13/
15/23/24 de Ángel) — viven en este archivo porque necesitan el estado interno
de la cola y de los trabajos activos.

"""

import asyncio

from src.comun.models import Job, JobStatus


class ControlError(Exception):
    """
    Clase base para errores de negocio (no de red ni de programación) que
    entrada.py puede traducir directamente a un código de error del protocolo.
    """
    code = "INTERNAL_ERROR"


class InvalidRequestError(ControlError):
    """La solicitud no tiene sentido, ej. un comando vacío (RF-02)."""
    code = "INVALID_REQUEST"


class QueueFullError(ControlError):
    """La cola ya está llena y no se puede aceptar un trabajo más (RF-25)."""
    code = "QUEUE_FULL"


class ServiceClosingError(ControlError):
    """El servicio está en proceso de apagarse y ya no acepta nada (RF-15)."""
    code = "SERVICE_CLOSING"


class Control:
    def __init__(
        self,
        cola,
        launcher,
        persistencia,
        bitacora,
        max_concurrency: int,
        grace_seconds: float,
    ):
        """
        Guarda referencias a los demás módulos (se los entregan ya armados
        desde afuera, ver servicio/main.py), y prepara su propia memoria:
          - cuántos trabajos están corriendo de verdad ahora mismo
          - un diccionario de "procesos activos" (job_id -> el Process real),
            para poder cancelarlos después
          - si el servicio sigue aceptando trabajos nuevos o ya está cerrando
          - un contador de cuántos han terminado en FAILED

        Un detalle extra que conviene guardar aparte del contador de "corriendo":
        cuántos trabajos ya se sacaron de la cola pero todavía no terminan de
        arrancar (ver _try_dispatch más abajo). Es como reservar una mesa en un
        restaurante antes de que el cliente llegue: si no se reserva, dos
        meseros podrían sentar a más gente de la que caben las mesas, porque
        ninguno sabe todavía que el otro ya prometió un lugar.
        """
        raise NotImplementedError

    async def submit(
        self, command: str, args: list[str], client_request_id: str | None
    ) -> Job:
        """
        Enviar un trabajo nuevo:
          1. Si el servicio ya está cerrando, no seguir: lanzar
             ServiceClosingError (RF-15).
          2. Si viene client_request_id, preguntarle a persistencia si ya
             existe un trabajo con ese mismo ID y sigue QUEUED/RUNNING; si sí,
             regresar ese Job en vez de crear uno nuevo (RF-27).
          3. Revisar que la solicitud tenga sentido (comando no vacío, etc.);
             si no, lanzar InvalidRequestError (RF-02).
          4. Si cola.is_full(), lanzar QueueFullError (RF-25).
          5. Crear el Job con estado QUEUED, guardarlo con
             persistencia.save_job(), avisarle a bitacora ("CREATED"), y
             meterlo a la fila con cola.enqueue().
          6. Llamar a self._try_dispatch() para intentar arrancarlo de
             inmediato si hay lugar.
          7. Regresar el Job creado.

        Nota de seguridad extra: aunque el paso 2 ya revisó duplicados, dos
        solicitudes con el mismo client_request_id podrían llegar casi al
        mismo tiempo y ambas ver "todavía no existe" antes de que cualquiera
        termine de guardar. Por eso persistencia.save_job() debe fallar con
        DuplicateClientRequestError si eso llega a pasar, y este método debe
        capturar ese error y responder con el Job que sí se alcanzó a guardar,
        en vez de dejar que se caiga la solicitud.
        """
        raise NotImplementedError

    async def get(self, job_id: str) -> Job | None:
        """Regresa el Job con ese id, o None si no existe (RF-08)."""
        raise NotImplementedError

    async def list(self, status_filter: JobStatus | None = None) -> list[Job]:
        """Regresa todos los jobs, opcionalmente filtrados por estado (RF-09)."""
        raise NotImplementedError

    async def request_cancel(self, job_id: str) -> str:
        """
        Regresa uno de: "NOT_FOUND", "ALREADY_FINISHED", "CANCELING".

        Si el job no existe: "NOT_FOUND".
        Si ya terminó (SUCCEEDED/FAILED/CANCELED): "ALREADY_FINISHED".
        Si está QUEUED: sacarlo de la fila con cola.remove(job_id) (para que
        deje de ocupar espacio), marcarlo CANCELED directo, y regresar
        "CANCELING".
        Si está RUNNING: buscar su proceso real en el diccionario de procesos
        activos y pedirle a launcher.cancel(proc, self.grace_seconds) que lo
        detenga. Regresar "CANCELING" — el resultado final (que ya quedó
        CANCELED) lo confirma _run_job() cuando el proceso realmente termine.

        Sobre llamadas repetidas (RF-26): si a este mismo job_id le piden
        cancelar dos veces casi al mismo tiempo mientras está RUNNING, la
        segunda llamada no debe volver a mandar otra señal — debe darse cuenta
        de que ya hay una cancelación en curso (por ejemplo guardando el
        job_id en un conjunto de "cancelaciones pedidas") y responder igual
        "CANCELING" sin duplicar la señal.
        """
        raise NotImplementedError

    async def get_output(self, job_id: str, stream: str) -> str | None:
        """
        Consulta la salida capturada de un trabajo (la mitad de RF-11 que
        faltaba: no basta con guardarla, hay que poder pedirla).
          - stream debe ser "stdout" o "stderr".
          - Si el job no existe, regresar None.
          - Buscar el Job con persistencia.load_job() para obtener
            stdout_path o stderr_path según corresponda.
          - Si el archivo todavía no existe (el trabajo apenas va empezando),
            regresar cadena vacía "" en vez de fallar.
          - Leer el archivo. Como leer de disco bloquea, hay que hacerlo con
            loop.run_in_executor(...) para no congelar el event loop.
        """
        raise NotImplementedError

    async def mark_running(self, job_id: str, pid: int) -> None:
        """
        Se llama justo después de que el proceso arrancó de verdad. Actualiza
        el Job a RUNNING con su pid real y la hora en que empezó, persiste el
        cambio, y mueve internamente el contador de "reservado" a "corriendo"
        (ver la nota del restaurante en __init__).
        """
        raise NotImplementedError

    async def mark_finished(
        self, job_id: str, exit_code: int | None, status: JobStatus
    ) -> None:
        """
        Se llama cuando el proceso ya terminó (o se confirma su cancelación).
        Actualiza el Job con el resultado final y persiste el cambio, quita el
        job_id del diccionario de procesos activos si estaba ahí, resta uno al
        contador de "corriendo" (solo si de verdad llegó a correr — un trabajo
        cancelado mientras aún estaba QUEUED nunca ocupó ese lugar, así que no
        hay nada que restarle ahí), suma uno al contador de errores si
        status == FAILED, y por último llama a self._try_dispatch() para
        darle su turno al siguiente trabajo en cola (RF-04: que uno termine no
        debe detener la atención de los demás).
        """
        raise NotImplementedError

    async def _try_dispatch(self) -> None:
        """
        Función de apoyo (no la usa nadie de fuera de este archivo): mientras
        haya lugar disponible (corriendo + reservado < max_concurrency) y algo
        esperando en la cola, saca el siguiente job_id, aparta su lugar (suma
        al contador de "reservado"), y lo manda a correr en segundo plano con
        asyncio.create_task(self._run_job(job_id)) — sin esperar (await) a que
        termine, para no bloquear nada más mientras corre.

        Se llama sola después de submit() y después de mark_finished(); nadie
        más necesita acordarse de invocarla.
        """
        raise NotImplementedError

    async def _run_job(self, job_id: str) -> None:
        """
        Función de apoyo: el recorrido completo de un solo trabajo, corriendo
        en segundo plano:
          1. Recuperar el Job.
          2. proc = await launcher.start(job.command, job.args, job.id)
          3. Guardar proc en el diccionario de procesos activos.
          4. await self.mark_running(job.id, proc.pid)
          5. exit_code = await launcher.stream_output(proc, stdout_path, stderr_path)
          6. Decidir el estado final: SUCCEEDED si exit_code == 0, FAILED si
             no, o CANCELED si este job_id tenía pedida una cancelación.
          7. await self.mark_finished(job.id, exit_code, status)

        Si launcher.start() falla (el comando ni siquiera pudo arrancar), hay
        que liberar el lugar "reservado" igual y guardar el trabajo como
        FAILED con el motivo, sin que esto afecte a los demás trabajos.
        """
        raise NotImplementedError

    async def recover_on_startup(self) -> None:
        """
        Se llama una sola vez, al arrancar el servicio, antes de aceptar
        conexiones (RF-13):
          1. Traer todo con persistencia.load_all().
          2. Cualquier Job que se haya quedado en RUNNING ya no tiene un
             proceso real detrás (el servicio se reinició) — marcarlo FAILED
             con una nota de "interrumpido por reinicio" (RNF-10).
          3. Cualquier Job que se haya quedado QUEUED, volver a meterlo a la
             fila con cola.enqueue(), respetando el orden en que se guardaron.
          4. Llamar a self._try_dispatch() por si ya hay lugar para arrancar
             algo de inmediato.
        """
        raise NotImplementedError

    def is_accepting(self) -> bool:
        """True si el servicio sigue aceptando trabajos nuevos (RF-15)."""
        raise NotImplementedError

    def stop_accepting(self) -> None:
        """A partir de aquí, submit() debe rechazar cualquier trabajo nuevo."""
        raise NotImplementedError

    def running_count(self) -> int:
        """Cuántos trabajos están corriendo de verdad ahora mismo."""
        raise NotImplementedError

    def queued_count(self) -> int:
        """Cuántos trabajos están esperando en la cola ahora mismo."""
        raise NotImplementedError

    def recent_errors_count(self) -> int:
        """Cuántos trabajos han terminado en FAILED desde que arrancó el servicio."""
        raise NotImplementedError
