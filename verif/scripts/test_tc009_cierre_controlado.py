"""
TC-009  Cierre controlado ................ RF-15, RNF-25, RNF-30
(ADR-012: JOBRUNNER_SHUTDOWN_TIMEOUT, Ctrl+C, puerto ocupado)
"""
import os
import signal
import socket
import time
import unittest

from jr_helpers import PruebaJobRunner


class TC009CierreControlado(PruebaJobRunner):

    def test_durante_el_cierre_no_acepta_nuevos(self):
        s = self.servicio(MAX_CONCURRENCY=1)
        a = s.submit("sleep", "3")["job_id"]
        b = s.submit("echo", "en cola")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        s.senal(signal.SIGTERM)
        time.sleep(0.4)
        r = s.submit("echo", "tarde")
        self.assertEqual(r.get("code"), "SERVICE_CLOSING")
        self.assertFalse(s.health()["active"], "Las consultas siguen funcionando durante el cierre")
        termino, _, codigo = s.esperar_fin(15)
        self.assertTrue(termino)
        self.assertEqual(codigo, 0)
        self.assertEqual(s.db("select status from jobs where id=?", (a,))[0][0], "SUCCEEDED")
        self.assertEqual(s.db("select status from jobs where id=?", (b,))[0][0], "QUEUED",
                         "Los QUEUED se quedan para el siguiente arranque")
        self.assertTrue(s.eventos("REJECTED"))
        self.assertTrue(s.eventos("SHUTDOWN_STARTED") and s.eventos("SERVICE_STOPPED"))
        self.assertTrue(s.iniciar())
        self.assertEqual(s.esperar_estado(b, timeout=5)["status"], "SUCCEEDED")

    def test_cierre_con_tiempo_limite(self):
        s = self.servicio(MAX_CONCURRENCY=2, GRACE_SECONDS=2, SHUTDOWN_TIMEOUT=2)
        normal = s.submit("sleep", "61")["job_id"]
        terco = s.submit("bash", "-c", "trap '' TERM; sleep 62")["job_id"]
        s.esperar_estado(normal, ("RUNNING",)); s.esperar_estado(terco, ("RUNNING",))
        time.sleep(0.3)
        s.senal(signal.SIGTERM)
        termino, segundos, codigo = s.esperar_fin(20)
        self.assertTrue(termino, "El cierre debe terminar en tiempo acotado")
        self.assertLessEqual(segundos, 2 + 2 + 5 + 1, f"Tardó {segundos} s")
        self.assertEqual(codigo, 0)
        filas = dict((i, (st, ec)) for i, st, ec in s.db("select id,status,exit_code from jobs"))
        self.assertEqual(filas[normal], ("CANCELED", -15))
        self.assertEqual(filas[terco], ("CANCELED", -9))
        self.assertEqual(s.procesos(), [], "No deben quedar procesos (RNF-25, RNF-30)")
        self.assertEqual(len(s.eventos("CANCEL_REQUESTED")), 2)
        print(f"\n    TC-009: cierre con límite en {segundos} s (timeout=2, grace=2)")

    def test_ctrl_c_hace_el_mismo_cierre_controlado(self):
        """Regresión: antes Ctrl+C mataba a los trabajos (FAILED -2)."""
        s = self.servicio("ctrl_c", iniciar=False, SHUTDOWN_TIMEOUT=2)
        self.assertTrue(s.iniciar(nueva_sesion=True))
        a = s.submit("sleep", "63")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        os.killpg(s.pid, signal.SIGINT)              # lo que hace la terminal con Ctrl+C
        termino, segundos, codigo = s.esperar_fin(15)
        self.assertTrue(termino)
        self.assertEqual(codigo, 0)
        self.assertEqual(s.db("select status, exit_code from jobs")[0], ("CANCELED", -15))
        self.assertEqual(s.procesos(), [])

    def test_sigterm_con_servicio_ocioso(self):
        s = self.servicio()
        s.senal(signal.SIGTERM)
        termino, segundos, codigo = s.esperar_fin(5)
        self.assertTrue(termino)
        self.assertEqual(codigo, 0)

    def test_puerto_ocupado(self):
        """Regresión F14: antes quedaba vivo, sin escuchar y lanzando los trabajos recuperados."""
        s = self.servicio(MAX_CONCURRENCY=1)
        a = s.submit("sleep", "64")["job_id"]
        b = s.submit("sleep", "65")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        s.matar()
        for pid in s.procesos("sleep 64"):
            os.kill(pid, signal.SIGKILL)
        ocupante = socket.socket()
        ocupante.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ocupante.bind(("127.0.0.1", s.port)); ocupante.listen(1)
        try:
            s.iniciar(esperar=False)
            termino, segundos, codigo = s.esperar_fin(5)
        finally:
            ocupante.close()
        self.assertTrue(termino, "Con el puerto ocupado el servicio debe terminar")
        self.assertNotEqual(codigo, 0)
        self.assertIn("No se puede escuchar", s.salida())
        self.assertEqual(s.db("select status from jobs where id=?", (b,))[0][0], "QUEUED")
        self.assertEqual(s.procesos("sleep 65"), [], "No debe lanzar trabajos si no puede atender")


if __name__ == "__main__":
    unittest.main()
