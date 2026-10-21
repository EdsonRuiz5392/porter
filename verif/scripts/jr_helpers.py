"""
Utilidades compartidas por las pruebas de verificación de JobRunner.

- Arrancan el servicio REAL (python3 -m src.servicio.main) como subproceso,
  cada uno con su propio puerto libre y su propio JOBRUNNER_DATA_DIR.
- Hablan el protocolo directamente (4 bytes '!I' + JSON), de forma
  independiente al CLI, para poder mandar también mensajes inválidos.
- Marcan cada servicio con una variable de entorno única (JR_PRUEBA_MARCA).
  Los procesos hijos y nietos la heredan, así que al terminar cada prueba se
  pueden encontrar y eliminar TODOS los procesos que creó, aunque hayan
  quedado huérfanos. Nunca se toca un proceso que no tenga la marca.

Sin dependencias externas: solo biblioteca estándar.
"""

import asyncio
import json
import os
import shutil
import signal
import socket
import sqlite3
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]       # carpeta que contiene src/ y verif/
TERMINALES = ("SUCCEEDED", "FAILED", "CANCELED")
PROTOCOL_VERSION = 1


# --------------------------------------------------------------------------- protocolo

def trama(msg: dict) -> bytes:
    cuerpo = json.dumps(msg).encode("utf-8")
    return struct.pack("!I", len(cuerpo)) + cuerpo


async def leer_mensaje(reader) -> dict:
    (n,) = struct.unpack("!I", await reader.readexactly(4))
    return json.loads(await reader.readexactly(n))


def M(tipo: str, **campos) -> dict:
    """Arma un mensaje con versión y tipo."""
    return {"version": PROTOCOL_VERSION, "type": tipo, **campos}


async def solicitud_async(port: int, msg: dict, timeout: float = 15) -> dict:
    r, w = await asyncio.open_connection("127.0.0.1", port)
    try:
        w.write(trama(msg))
        await w.drain()
        return await asyncio.wait_for(leer_mensaje(r), timeout)
    finally:
        w.close()


def solicitud(port: int, msg: dict, timeout: float = 15) -> dict:
    return asyncio.run(solicitud_async(port, msg, timeout))


def en_paralelo(port: int, mensajes: list[dict], timeout: float = 20) -> list[dict]:
    """Envía todos los mensajes al mismo tiempo, cada uno por su propia conexión."""
    async def _todas():
        return await asyncio.gather(*[solicitud_async(port, m, timeout) for m in mensajes])
    return asyncio.run(_todas())


def puerto_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def esperar_que(condicion, timeout: float, intervalo: float = 0.1):
    """Repite condicion() hasta que devuelva algo verdadero o se acabe el tiempo."""
    limite = time.time() + timeout
    while time.time() < limite:
        valor = condicion()
        if valor:
            return valor
        time.sleep(intervalo)
    return condicion()


# --------------------------------------------------------------------------- procesos

def _leer_proc(pid: str):
    try:
        with open(f"/proc/{pid}/environ", "rb") as f:
            env = f.read()
        with open(f"/proc/{pid}/cmdline", "rb") as f:
            cmd = f.read().replace(b"\0", b" ").decode(errors="replace").strip()
        with open(f"/proc/{pid}/stat") as f:
            resto = f.read().rsplit(")", 1)[1].split()
        return env, cmd, resto[0], int(resto[1])      # environ, cmdline, estado, ppid
    except OSError:
        return None


# --------------------------------------------------------------------------- servicio

class Servicio:
    """Un JobRunner real, con su propio puerto, carpeta de datos y marca."""

    def __init__(self, carpeta: Path, **config):
        self.carpeta = Path(carpeta)
        shutil.rmtree(self.carpeta, ignore_errors=True)
        self.carpeta.mkdir(parents=True)
        self.data = self.carpeta / "data"
        self.salida_path = self.carpeta / "servicio_salida.txt"
        self.port = puerto_libre()
        self.marca = uuid.uuid4().hex
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("JOBRUNNER_")}
        self.env.pop("PYTHONPATH", None)
        self.env.update(JOBRUNNER_PORT=str(self.port), JOBRUNNER_DATA_DIR=str(self.data),
                        JR_PRUEBA_MARCA=self.marca)
        self.configurar(**config)
        self.p = None

    def configurar(self, **config):
        for k, v in config.items():
            self.env["JOBRUNNER_" + k.upper()] = str(v)

    # ---- ciclo de vida
    def iniciar(self, nueva_sesion: bool = False, esperar: bool = True) -> bool:
        salida = open(self.salida_path, "a")
        self.p = subprocess.Popen(
            [sys.executable, "-m", "src.servicio.main"], cwd=REPO_ROOT, env=self.env,
            stdin=subprocess.DEVNULL, stdout=salida, stderr=subprocess.STDOUT,
            start_new_session=nueva_sesion,
        )
        salida.close()
        if not esperar:
            return True
        limite = time.time() + 10
        while time.time() < limite:
            if self.p.poll() is not None:
                return False
            try:
                socket.create_connection(("127.0.0.1", self.port), timeout=0.3).close()
                return True
            except OSError:
                time.sleep(0.1)
        return False

    @property
    def pid(self) -> int:
        return self.p.pid

    def vivo(self) -> bool:
        return self.p is not None and self.p.poll() is None

    def senal(self, sig):
        self.p.send_signal(sig)

    def esperar_fin(self, timeout: float):
        """Espera a que el servicio termine; devuelve (terminó, segundos, código)."""
        t0 = time.time()
        try:
            codigo = self.p.wait(timeout)
            return True, round(time.time() - t0, 2), codigo
        except subprocess.TimeoutExpired:
            return False, round(time.time() - t0, 2), None

    def matar(self):
        if self.vivo():
            self.p.kill()
            self.p.wait()

    def detener(self, timeout: float = 15):
        if self.vivo():
            self.p.send_signal(signal.SIGTERM)
            try:
                self.p.wait(timeout)
            except subprocess.TimeoutExpired:
                self.matar()

    def limpiar(self):
        """Mata el servicio y TODO proceso que lleve su marca (hijos, nietos, huérfanos)."""
        self.matar()
        for _ in range(3):
            pids = [pid for pid, _, _, _ in self.procesos_marcados(incluir_servicio=True)]
            if not pids:
                break
            for pid in pids:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            time.sleep(0.1)

    # ---- inspección
    def procesos_marcados(self, incluir_servicio: bool = False):
        marca = f"JR_PRUEBA_MARCA={self.marca}".encode()
        res = []
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            info = _leer_proc(d)
            if not info or marca not in info[0]:
                continue
            pid = int(d)
            if not incluir_servicio and self.p is not None and pid == self.p.pid:
                continue
            res.append((pid, info[2], info[1], info[3]))     # pid, estado, cmdline, ppid
        return res

    def procesos(self, comando: str | None = None) -> list[int]:
        """PIDs vivos (no zombis) creados por este servicio; opcionalmente con cmdline exacta."""
        return [pid for pid, est, cmd, _ in self.procesos_marcados()
                if est != "Z" and (comando is None or cmd == comando)]

    def zombis_hijos(self) -> int:
        n = 0
        for d in os.listdir("/proc"):
            if d.isdigit():
                info = _leer_proc(d)
                if info and info[3] == self.pid and info[2] == "Z":
                    n += 1
        return n

    def descriptores(self) -> int:
        return len(os.listdir(f"/proc/{self.pid}/fd"))

    def bitacora(self) -> list[str]:
        try:
            return (self.data / "jobrunner.log").read_text().splitlines()
        except FileNotFoundError:
            return []

    def eventos(self, evento: str, job_id: str | None = None) -> list[str]:
        return [l for l in self.bitacora()
                if f"| {evento} |" in l and (job_id is None or f"job={job_id}" in l)]

    def salida(self) -> str:
        try:
            return self.salida_path.read_text()
        except FileNotFoundError:
            return ""

    def db(self, sql: str, args=()):
        c = sqlite3.connect(self.data / "jobs.db")
        try:
            return c.execute(sql, args).fetchall()
        finally:
            c.close()

    # ---- operaciones del protocolo
    def pedir(self, msg: dict, timeout: float = 15) -> dict:
        return solicitud(self.port, msg, timeout)

    def submit(self, comando, *args, folio=None) -> dict:
        m = M("submit", command=comando, args=list(args))
        if folio is not None:
            m["client_request_id"] = folio
        return self.pedir(m)

    def status(self, job_id) -> dict:
        return self.pedir(M("status", job_id=job_id))

    def job(self, job_id) -> dict | None:
        r = self.status(job_id)
        return r.get("job") if r.get("type") == "status_response" else None

    def cancel(self, job_id) -> dict:
        return self.pedir(M("cancel", job_id=job_id))

    def output(self, job_id, stream="stdout") -> dict:
        return self.pedir(M("output", job_id=job_id, stream=stream))

    def health(self) -> dict:
        return self.pedir(M("health"))

    def listar(self, filtro=None) -> dict:
        m = M("list")
        if filtro is not None:
            m["status_filter"] = filtro
        return self.pedir(m)

    def esperar_estado(self, job_id, estados=TERMINALES, timeout: float = 20) -> dict | None:
        def _ok():
            j = self.job(job_id)
            return j if j and j["status"] in estados else None
        return esperar_que(_ok, timeout)

    def esperar_vacio(self, timeout: float = 60) -> bool:
        def _ok():
            h = self.health()
            return h.get("running") == 0 and h.get("queued") == 0
        return bool(esperar_que(_ok, timeout, 0.2))

    def cli(self, *args, timeout: float = 30):
        r = subprocess.run([sys.executable, "-m", "src.cliente.cli", *args], cwd=REPO_ROOT,
                           env=self.env, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()


# --------------------------------------------------------------------------- clase base

class PruebaJobRunner(unittest.TestCase):
    """
    Clase base: cada prueba crea sus servicios con self.servicio(...), y al
    terminar se limpian todos (incluso si la prueba falla).
    La evidencia (bitácora, base de datos y salida de cada servicio) se guarda
    en $JR_EVIDENCIA_DIR/servicios/<prueba>/ si la variable existe; si no, en
    una carpeta temporal que se borra al final.
    """

    def setUp(self):
        self._servicios: list[Servicio] = []
        base = os.environ.get("JR_EVIDENCIA_DIR")
        nombre = f"{type(self).__name__}.{self._testMethodName}"
        if base:
            self._carpeta = Path(base) / "servicios" / nombre
            self._temporal = False
        else:
            self._carpeta = Path(tempfile.mkdtemp(prefix="jr_"))
            self._temporal = True

    def tearDown(self):
        for s in self._servicios:
            s.limpiar()
        if self._temporal:
            shutil.rmtree(self._carpeta, ignore_errors=True)

    def servicio(self, nombre: str = "servicio", iniciar: bool = True, **config) -> Servicio:
        s = Servicio(self._carpeta / nombre, **config)
        self._servicios.append(s)
        if iniciar:
            self.assertTrue(s.iniciar(), f"El servicio no arrancó. Salida:\n{s.salida()}")
        return s
