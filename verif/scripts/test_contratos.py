"""
Prueba de contratos de interfaz entre modulos.

Comprueba que cada modulo de src/ expone las funciones definidas en
docs/technical-guide/contratos-interfaces.md, con el nombre, los parametros
y el tipo (async o sincrona) correctos. No ejecuta el servicio: solo importa
los modulos e inspecciona sus firmas, asi que se puede correr aunque un
modulo siga sin implementar.

Sirve para detectar, antes de integrar, que un modulo no encaja con lo que
los demas esperan de el.

Requisitos: RNF-17 (codigo modular), RNF-18 (interfaces documentadas),
RNF-20 (pruebas con un solo comando).
Ejecucion: python -m pytest verif/scripts/test_contratos.py -v
Responsable: Edson (verificacion).
"""
import importlib
import inspect

import pytest

# (modulo, clase o None, funcion, es_async, parametros sin self)
CONTRATOS = [
    ("src.comun.protocolo", None, "read_message", True, ["reader", "max_len"]),
    ("src.comun.protocolo", None, "write_message", True, ["writer", "message"]),
    ("src.servicio.entrada", None, "handle_client", True,
     ["reader", "writer", "job_manager", "max_message_bytes"]),
    ("src.servicio.entrada", None, "main", True,
     ["host", "port", "allowed_networks", "job_manager", "max_message_bytes"]),
    ("src.servicio.gestion_trabajos.cola", "Cola", "__init__", False, ["max_size"]),
    ("src.servicio.gestion_trabajos.cola", "Cola", "is_full", False, []),
    ("src.servicio.gestion_trabajos.cola", "Cola", "enqueue", False, ["job_id"]),
    ("src.servicio.gestion_trabajos.cola", "Cola", "dequeue", False, []),
    ("src.servicio.gestion_trabajos.cola", "Cola", "remove", False, ["job_id"]),
    ("src.servicio.gestion_trabajos.cola", "Cola", "size", False, []),
    ("src.servicio.gestion_trabajos.control", "Control", "__init__", False,
     ["cola", "launcher", "persistencia", "bitacora", "max_concurrency", "grace_seconds"]),
    ("src.servicio.gestion_trabajos.control", "Control", "submit", True,
     ["command", "args", "client_request_id"]),
    ("src.servicio.gestion_trabajos.control", "Control", "get", True, ["job_id"]),
    ("src.servicio.gestion_trabajos.control", "Control", "list", True, ["status_filter"]),
    ("src.servicio.gestion_trabajos.control", "Control", "request_cancel", True, ["job_id"]),
    ("src.servicio.gestion_trabajos.control", "Control", "get_output", True, ["job_id", "stream"]),
    ("src.servicio.gestion_trabajos.control", "Control", "mark_running", True, ["job_id", "pid"]),
    ("src.servicio.gestion_trabajos.control", "Control", "mark_finished", True,
     ["job_id", "exit_code", "status"]),
    ("src.servicio.gestion_trabajos.control", "Control", "recover_on_startup", True, []),
    ("src.servicio.gestion_trabajos.control", "Control", "is_accepting", False, []),
    ("src.servicio.gestion_trabajos.control", "Control", "stop_accepting", False, []),
    ("src.servicio.gestion_trabajos.control", "Control", "running_count", False, []),
    ("src.servicio.gestion_trabajos.control", "Control", "queued_count", False, []),
    ("src.servicio.gestion_trabajos.control", "Control", "recent_errors_count", False, []),
    ("src.servicio.gestion_trabajos.launcher", "Launcher", "start", True,
     ["command", "args", "job_id"]),
    ("src.servicio.gestion_trabajos.launcher", "Launcher", "cancel", True,
     ["proc", "grace_seconds"]),
    ("src.servicio.gestion_trabajos.launcher", "Launcher", "stream_output", True,
     ["proc", "stdout_path", "stderr_path"]),
    ("src.servicio.persistencia", "Persistencia", "__init__", False, ["db_path"]),
    ("src.servicio.persistencia", "Persistencia", "save_job", True, ["job"]),
    ("src.servicio.persistencia", "Persistencia", "load_job", True, ["job_id"]),
    ("src.servicio.persistencia", "Persistencia", "load_all", True, []),
    ("src.servicio.persistencia", "Persistencia", "find_by_client_request_id", True,
     ["client_request_id"]),
    ("src.servicio.bitacora", "Bitacora", "__init__", False, ["log_path"]),
    ("src.servicio.bitacora", "Bitacora", "log_event", False, ["job_id", "event", "detail"]),
    ("src.servicio.operacion", None, "load_config", False, []),
    ("src.servicio.operacion", None, "shutdown", True, ["job_manager"]),
    ("src.servicio.operacion", None, "health_summary", True, ["job_manager"]),
    ("src.servicio.operacion", None, "check_rate_limit", False, ["current_count", "max_allowed"]),
    ("src.cliente.cli", None, "_leer_configuracion_conexion", False, []),
    ("src.cliente.cli", None, "_enviar_solicitud", True, ["host", "port", "mensaje", "max_len"]),
    ("src.cliente.cli", None, "main", False, []),
]

CONSTANTES_PROTOCOLO = [
    "PROTOCOL_VERSION", "ERROR_INVALID_REQUEST", "ERROR_QUEUE_FULL",
    "ERROR_NOT_FOUND", "ERROR_VERSION_UNSUPPORTED", "ERROR_SERVICE_CLOSING",
    "ERROR_INTERNAL",
]

EXCEPCIONES = [
    ("src.comun.protocolo", "ProtocolError"),
    ("src.comun.protocolo", "MessageTooLargeError"),
    ("src.comun.protocolo", "InvalidMessageError"),
    ("src.servicio.gestion_trabajos.control", "ControlError"),
    ("src.servicio.gestion_trabajos.control", "InvalidRequestError"),
    ("src.servicio.gestion_trabajos.control", "QueueFullError"),
    ("src.servicio.gestion_trabajos.control", "ServiceClosingError"),
    ("src.servicio.persistencia", "DuplicateClientRequestError"),
]


def _nombre_corto(contrato):
    modulo, clase, funcion, *_ = contrato
    return f"{modulo.split('.')[-1]}.{clase + '.' if clase else ''}{funcion}"


@pytest.mark.parametrize("contrato", CONTRATOS, ids=_nombre_corto)
def test_funcion_cumple_contrato(contrato):
    modulo, clase, nombre, es_async, esperados = contrato
    mod = importlib.import_module(modulo)
    objeto = getattr(mod, clase) if clase else mod
    donde = f"{modulo}{'.' + clase if clase else ''}"

    assert hasattr(objeto, nombre), f"falta {nombre} en {donde}"
    funcion = getattr(objeto, nombre)
    assert callable(funcion), f"{nombre} existe en {donde} pero no es una funcion"

    tipo = "async def" if es_async else "def (sincrona)"
    assert inspect.iscoroutinefunction(funcion) == es_async, \
        f"{donde}.{nombre} debe ser {tipo} segun el contrato"

    reales = [p for p in inspect.signature(funcion).parameters if p != "self"]
    assert reales == esperados, \
        f"{donde}.{nombre} recibe {reales}; el contrato dice {esperados}"


@pytest.mark.parametrize("nombre", CONSTANTES_PROTOCOLO)
def test_constante_de_protocolo_existe(nombre):
    mod = importlib.import_module("src.comun.protocolo")
    assert hasattr(mod, nombre), f"falta la constante {nombre} en protocolo.py"


@pytest.mark.parametrize("modulo,nombre", EXCEPCIONES,
                         ids=[f"{m.split('.')[-1]}.{n}" for m, n in EXCEPCIONES])
def test_excepcion_definida(modulo, nombre):
    mod = importlib.import_module(modulo)
    assert hasattr(mod, nombre), f"falta la excepcion {nombre} en {modulo}"
    assert issubclass(getattr(mod, nombre), Exception), f"{nombre} no hereda de Exception"
