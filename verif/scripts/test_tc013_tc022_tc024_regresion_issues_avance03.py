"""
TC-013  Salud coherente con la base (trabajos en tránsito) ... RF-24, RNF-31
TC-022  Esperar "cola vacía" con health no deja pendientes ... RNF-31
TC-024  El cupo se libera aunque la base esté ocupada ......... RF-29, RNF-06, RNF-33
(Issues "TC-022 intermitente" y "database is locked"; ADR-017 revisión 1 y ADR-018)

Las dos fallas eran intermitentes porque dependían de ventanas de milisegundos
que solo se abrían en una máquina lenta o cargada. Estas pruebas las ensanchan
a propósito para que fallen siempre con el código anterior:
- un launcher que tarda 2 s en crear el proceso (ventana "en tránsito");
- otra conexión que tiene la base bloqueada 7 s (más que los 5 s que
  sqlite3 espera por defecto);
- un tiempo de espera de SQLite de 0.5 s inyectado con sitecustomize, para que
  guardar el resultado final falle de verdad y se vea qué pasa con el cupo.

Alcance (ADR-018): no se prueba que el servicio aguante cualquier bloqueo de
la base. Se prueba que un bloqueo corto no marca FAILED a un trabajo válido y
que, si la base de verdad no responde, el servicio no pierde lugares de
ejecución y la recuperación del siguiente arranque deja el trabajo en un
estado final.
"""
import json
import sqlite3
import subprocess
import sys
import textwrap
import time
import unittest

from jr_helpers import REPO_ROOT, PruebaJobRunner

TRANSITO = textwrap.dedent("""
    import asyncio, json, os, sqlite3, sys
    sys.path.insert(0, sys.argv[1])
    from src.servicio import bitacora, operacion, persistencia
    from src.servicio.gestion_trabajos import cola, control, launcher

    class LauncherLento(launcher.Launcher):
        async def start(self, *a, **kw):
            await asyncio.sleep(2)                   # ensancha la ventana de arranque
            return await super().start(*a, **kw)

    async def main():
        data = sys.argv[2]
        os.makedirs(data + "/output", exist_ok=True)
        c = control.Control(cola=cola.Cola(10), launcher=LauncherLento(),
                            persistencia=persistencia.Persistencia(data + "/jobs.db"),
                            bitacora=bitacora.Bitacora(data + "/jobrunner.log"),
                            max_concurrency=1, grace_seconds=1, data_dir=data)
        j = await c.submit(command="true", args=[], client_request_id=None)
        await asyncio.sleep(0.5)
        h = await operacion.health_summary(c)
        base = sqlite3.connect(data + "/jobs.db").execute(
            "select status from jobs where id=?", (j.id,)).fetchone()[0]
        print(json.dumps({"running": h["running"], "queued": h["queued"],
                          "starting": h.get("starting"), "base": base}), flush=True)
        await asyncio.sleep(3)
    asyncio.run(main())
""")

TIMEOUT_FORZADO = textwrap.dedent("""
    import os, sqlite3
    _t = float(os.environ.get("JR_SQLITE_TIMEOUT", "0") or 0)
    if _t:
        _orig = sqlite3.connect
        def connect(*a, **kw):
            kw["timeout"] = _t
            return _orig(*a, **kw)
        sqlite3.connect = connect
""")


def _bloquear_base(ruta, segundos: float) -> None:
    """Otra conexión toma el candado de escritura y lo suelta después de `segundos`."""
    c = sqlite3.connect(ruta, isolation_level=None)
    try:
        c.execute("BEGIN IMMEDIATE")
        time.sleep(segundos)
        c.execute("COMMIT")
    finally:
        c.close()


class TC013SaludEnTransito(PruebaJobRunner):

    def test_health_cuenta_los_trabajos_en_transito(self):
        """Regresión Issue TC-022: con un QUEUED en la base, health no puede decir 0 en ejecución y 0 en cola."""
        s = self.servicio(iniciar=False)
        s.data.mkdir(parents=True, exist_ok=True)
        script = s.carpeta / "transito.py"
        script.write_text(TRANSITO)
        r = subprocess.run([sys.executable, str(script), str(REPO_ROOT), str(s.data)],
                           env=s.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        foto = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(foto["base"], "QUEUED", foto)
        self.assertEqual((foto["running"], foto["queued"]), (0, 1),
                         f"queued debe coincidir con lo que la base reporta como QUEUED: {foto}")
        self.assertEqual(foto["starting"], 1, f"starting dice cuántos están arrancando: {foto}")


class TC024BaseOcupada(PruebaJobRunner):

    def test_bloqueo_de_7s_no_marca_failed_un_trabajo_valido(self):
        """Regresión Issue database is locked: un bloqueo de 7 s ya no alcanza los 5 s de antes (ADR-018)."""
        s = self.servicio(MAX_CONCURRENCY=1)
        a = s.submit("sleep", "1")["job_id"]
        b = s.submit("echo", "siguiente")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        _bloquear_base(s.data / "jobs.db", 7)          # a termina en medio del bloqueo
        fin = s.esperar_estado(a, timeout=30)
        self.assertEqual((fin["status"], fin["exit_code"]), ("SUCCEEDED", 0), fin)
        self.assertEqual(s.esperar_estado(b, timeout=30)["status"], "SUCCEEDED", "El cupo debe liberarse")
        self.assertFalse([l for l in s.bitacora() if "database is locked" in l], s.bitacora())

    def test_si_la_base_no_responde_el_cupo_se_libera(self):
        """Regresión: antes el trabajo se quedaba 'en curso' para siempre y su lugar de ejecución se perdía."""
        s = self.servicio(iniciar=False, MAX_CONCURRENCY=1)
        (s.carpeta / "inyeccion").mkdir()
        (s.carpeta / "inyeccion" / "sitecustomize.py").write_text(TIMEOUT_FORZADO)
        s.env["PYTHONPATH"] = str(s.carpeta / "inyeccion")
        s.env["JR_SQLITE_TIMEOUT"] = "0.5"            # la base "no responde" a los 0.5 s
        self.assertTrue(s.iniciar(), s.salida())

        a = s.submit("sleep", "1")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        _bloquear_base(s.data / "jobs.db", 3)          # a termina y no puede guardar su resultado

        c = s.submit("echo", "despues")["job_id"]
        fin_c = s.esperar_estado(c, timeout=15) or s.job(c) or {}
        self.assertEqual(fin_c.get("status"), "SUCCEEDED",
                         f"Con MAX_CONCURRENCY=1, otro trabajo debe poder correr: {fin_c} {s.health()}")
        self.assertTrue(s.esperar_vacio(10), f"Sin lugares perdidos: {s.health()}")
        self.assertNotIn("Task exception was never retrieved", s.salida())
        self.assertTrue(s.eventos("PERSIST_ERROR", a), "El fallo al guardar queda en la bitácora")
        self.assertGreaterEqual(s.health()["recent_errors"], 1, "y cuenta como error reciente (ADR-017)")

        # Limitación aceptada (ADR-018): la fila de a quedó sin estado final.
        # El siguiente arranque la deja en un estado final (ADR-010).
        s.detener()
        self.assertTrue(s.iniciar(), s.salida())
        jj = s.job(a)
        self.assertEqual((jj["status"], jj["exit_code"]), ("FAILED", -1), jj)
        self.assertTrue(s.eventos("INTERRUPTED", a))


if __name__ == "__main__":
    unittest.main()
