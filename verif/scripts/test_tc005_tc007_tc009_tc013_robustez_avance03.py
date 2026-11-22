"""
TC-005  Cancelación alcanza descendientes fuera del grupo ... RF-10, RNF-30
TC-007  Caída durante el arranque de un trabajo (INC-03) ..... RF-13, RF-27, RNF-30, RNF-31
TC-009  Cierre controlado con clientes conectados ............ RF-15, RNF-25
TC-013  Salud ampliada y registro de rechazos ................ RF-23, RF-24, RNF-22
(ADR-016: marca de entorno por trabajo; ADR-017: resumen de salud)
"""
import os
import signal
import socket
import subprocess
import sys
import textwrap
import time
import unittest

from jr_helpers import REPO_ROOT, M, PruebaJobRunner, esperar_que

# Simula una caída justo en la "ventana de arranque": el launcher real crea el
# proceso y, antes de que el servicio alcance a registrar el PID, el servicio
# muere (la prueba le manda SIGKILL a este script).
CAIDA_EN_ARRANQUE = textwrap.dedent("""
    import asyncio, os, sys
    sys.path.insert(0, sys.argv[1])
    from src.servicio import bitacora, persistencia
    from src.servicio.gestion_trabajos import cola, control, launcher

    class LauncherQueSeCuelga(launcher.Launcher):
        async def start(self, *a, **kw):
            proc = await super().start(*a, **kw)
            print("LANZADO", proc.pid, flush=True)
            await asyncio.Event().wait()        # nunca regresa: mark_running no llega

    async def main():
        data = sys.argv[2]
        os.makedirs(data + "/output", exist_ok=True)
        c = control.Control(cola=cola.Cola(10), launcher=LauncherQueSeCuelga(),
                            persistencia=persistencia.Persistencia(data + "/jobs.db"),
                            bitacora=bitacora.Bitacora(data + "/jobrunner.log"),
                            max_concurrency=1, grace_seconds=1, data_dir=data)
        await c.submit(command="bash", args=["-c", "echo x >> " + sys.argv[3] + "; sleep 341"],
                       client_request_id=None)
        await asyncio.Event().wait()
    asyncio.run(main())
""")


class TC005CancelacionDescendientes(PruebaJobRunner):

    def test_descendiente_con_setsid_tambien_se_termina(self):
        """Límite del ADR-008: un nieto que se sale del grupo con setsid sobrevivía a la cancelación."""
        s = self.servicio(GRACE_SECONDS=1)
        j = s.submit("bash", "-c", "setsid sleep 342 & sleep 343")["job_id"]
        s.esperar_estado(j, ("RUNNING",))
        self.assertTrue(esperar_que(lambda: s.procesos("sleep 342"), 3))
        s.cancel(j)
        self.assertEqual(s.esperar_estado(j)["status"], "CANCELED")
        self.assertTrue(esperar_que(lambda: s.procesos("sleep 342") == [], 5),
                        "El proceso que escapó de su grupo debe terminarse por su marca de trabajo")


class TC007CaidaEnArranque(PruebaJobRunner):

    def test_caida_durante_el_arranque_no_ejecuta_el_trabajo_dos_veces(self):
        """Regresión INC-03: antes la base decía QUEUED, se relanzaba y quedaba un huérfano invisible."""
        s = self.servicio(iniciar=False)
        s.data.mkdir(parents=True, exist_ok=True)
        marcas = s.carpeta / "ejecuciones.txt"
        script = s.carpeta / "caida_en_arranque.py"
        script.write_text(CAIDA_EN_ARRANQUE)
        caido = subprocess.Popen([sys.executable, str(script), str(REPO_ROOT), str(s.data), str(marcas)],
                                 env=s.env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        try:
            self.assertTrue(esperar_que(lambda: marcas.exists() and marcas.read_text().count("x") == 1, 10),
                            "El trabajo debió arrancar una vez")
            caido.kill(); caido.wait()                       # la caída
        finally:
            if caido.poll() is None:
                caido.kill(); caido.wait()
        self.assertTrue(s.procesos("sleep 341"), "Tras la caída el proceso del trabajo sigue vivo")

        self.assertTrue(s.iniciar(), s.salida())               # reinicio con el servicio real
        time.sleep(1.5)
        self.assertEqual(marcas.read_text().count("x"), 1, "El trabajo NO debe ejecutarse dos veces")
        self.assertTrue(esperar_que(lambda: s.procesos("sleep 341") == [], 3), "Sin huérfanos (RNF-30)")
        (job_id, estado), = s.db("select id, status from jobs")
        self.assertEqual(estado, "FAILED", "Se marca interrumpido, como un RUNNING (ADR-010)")
        self.assertTrue(s.eventos("INTERRUPTED", job_id))
        self.assertTrue(s.eventos("ORPHAN_KILLED", job_id))


class TC009CierreConClientes(PruebaJobRunner):

    def test_cierre_no_espera_a_clientes_ociosos(self):
        """RNF-25: un cliente conectado sin hacer nada no retrasa el cierre, y su socket se cierra."""
        s = self.servicio(IDLE_TIMEOUT=300, SHUTDOWN_TIMEOUT=0)
        sk = socket.create_connection(("127.0.0.1", s.port))
        try:
            time.sleep(0.3)
            s.senal(signal.SIGTERM)
            termino, segundos, codigo = s.esperar_fin(8)
            self.assertTrue(termino, "El cierre no debe quedarse esperando al cliente")
            self.assertEqual(codigo, 0)
            sk.settimeout(3)
            self.assertEqual(sk.recv(100), b"", "El servicio cerró la conexión del cliente")
        finally:
            sk.close()


class TC013SaludAmpliada(PruebaJobRunner):

    def test_health_trae_configuracion_y_tiempo_activo(self):
        s = self.servicio(MAX_CONCURRENCY=2, MAX_QUEUE=7)
        h = s.health()
        for campo in ("active", "running", "queued", "recent_errors", "uptime_s", "max_concurrency",
                      "max_queue", "clients_connected", "max_clients", "error_window_s",
                      "last_errors", "protocol_version"):
            self.assertIn(campo, h, h)
        self.assertEqual((h["max_concurrency"], h["max_queue"], h["protocol_version"]), (2, 7, 1))
        codigo, texto = s.cli("health")
        self.assertEqual(codigo, 0)
        self.assertIn("activo", texto)

    def test_errores_recientes_vencen_con_la_ventana(self):
        """Defecto 10 del vol. 2: 'recientes' significa dentro de una ventana, no desde el arranque."""
        s = self.servicio(ERROR_WINDOW=2)
        j = s.submit("false")["job_id"]
        s.esperar_estado(j)
        h = s.health()
        self.assertEqual(h["recent_errors"], 1, h)
        self.assertEqual(h["last_errors"][-1]["job_id"], j)
        self.assertTrue(esperar_que(lambda: s.health()["recent_errors"] == 0, 5),
                        "Pasada la ventana el error deja de ser reciente")

    def test_rechazos_por_validacion_se_registran(self):
        """Defecto 3 del vol. 2 (RF-23): los rechazos por validación también quedan en la bitácora."""
        s = self.servicio()
        s.pedir(M("submit", command="", args=[]))
        s.pedir(M("submit", command="x" * 100_000, args=[]))
        rechazos = [l for l in s.eventos("REJECTED") if "INVALID_REQUEST" in l]
        self.assertEqual(len(rechazos), 2, s.bitacora())
        self.assertNotIn("x" * 200, "\n".join(rechazos), "La bitácora no copia entradas enormes")

    def test_bitacora_registra_el_origen_de_cada_envio(self):
        """RNF-22: correlacionar solicitud y trabajo, incluida la dirección del cliente."""
        s = self.servicio(ALLOWED_NETWORKS="127.0.0.1,127.0.0.3")
        j = s.pedir(M("submit", command="true", args=[]), origen="127.0.0.3")["job_id"]
        creados = s.eventos("CREATED", j)
        self.assertEqual(len(creados), 1)
        self.assertIn("127.0.0.3", creados[0])


if __name__ == "__main__":
    unittest.main()
