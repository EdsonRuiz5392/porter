"""
TC-003  Estados y tiempos ................ RF-06, RF-07
TC-006  Capturar stdout/stderr y código ..... RF-11, RF-07
(incluye regresiones de la captura por bloques: ADR-010)
"""
import time
import unittest
from datetime import datetime

from jr_helpers import PruebaJobRunner


class TC003EstadosYTiempos(PruebaJobRunner):

    def test_ciclo_de_vida_y_tiempos(self):
        s = self.servicio()
        r = s.submit("sleep", "0.5")
        self.assertEqual(r["status"], "QUEUED")
        corriendo = s.esperar_estado(r["job_id"], ("RUNNING",), 5)
        self.assertIsNotNone(corriendo, "Debe pasar por RUNNING")
        self.assertIsInstance(corriendo["pid"], int)
        j = s.esperar_estado(r["job_id"])
        self.assertEqual((j["status"], j["exit_code"]), ("SUCCEEDED", 0))
        t_rec, t_ini, t_fin = (datetime.fromisoformat(j[k]) for k in ("submitted_at", "started_at", "finished_at"))
        self.assertLessEqual(t_rec, t_ini)
        self.assertLess(t_ini, t_fin)
        self.assertGreaterEqual((t_fin - t_ini).total_seconds(), 0.4)
        for evento in ("CREATED", "STARTED", "SUCCEEDED"):
            self.assertTrue(s.eventos(evento, r["job_id"]), f"Falta {evento} en la bitácora (RNF-22)")

    def test_codigo_distinto_de_cero_es_failed(self):
        s = self.servicio()
        j = s.esperar_estado(s.submit("bash", "-c", "exit 7")["job_id"])
        self.assertEqual((j["status"], j["exit_code"]), ("FAILED", 7))


class TC006SalidasSeparadas(PruebaJobRunner):

    def test_stdout_y_stderr_no_se_mezclan(self):
        s = self.servicio()
        r = s.submit("bash", "-c", "echo a_out; echo a_err >&2; echo b_out; exit 3")
        j = s.esperar_estado(r["job_id"])
        self.assertEqual((j["status"], j["exit_code"]), ("FAILED", 3))
        self.assertEqual(s.output(r["job_id"], "stdout")["content"], "a_out\nb_out\n")
        self.assertEqual(s.output(r["job_id"], "stderr")["content"], "a_err\n")

    def test_cli_output(self):
        s = self.servicio()
        r = s.submit("bash", "-c", "echo SALIDA; echo ERROR >&2")
        s.esperar_estado(r["job_id"])
        self.assertEqual(s.cli("output", r["job_id"]), (0, "SALIDA"))
        self.assertEqual(s.cli("output", r["job_id"], "stderr"), (0, "ERROR"))

    def test_linea_de_200000_caracteres(self):
        """Regresión F6: antes, una línea > 64 KiB dejaba el trabajo FAILED y el proceso vivo."""
        s = self.servicio()
        r = s.submit("python3", "-c", "import sys; sys.stdout.write('x'*200000)")
        j = s.esperar_estado(r["job_id"])
        self.assertEqual((j["status"], j["exit_code"]), ("SUCCEEDED", 0))
        self.assertEqual(len(s.output(r["job_id"])["content"]), 200_000)

    def test_salida_visible_mientras_corre(self):
        s = self.servicio()
        r = s.submit("bash", "-c", "echo primera; sleep 3; echo segunda")
        time.sleep(1.5)
        self.assertEqual(s.output(r["job_id"])["content"], "primera\n")
        s.esperar_estado(r["job_id"])
        self.assertEqual(s.output(r["job_id"])["content"], "primera\nsegunda\n")

    def test_bytes_que_no_son_texto(self):
        s = self.servicio()
        r = s.submit("printf", "\\377\\376hola")
        s.esperar_estado(r["job_id"])
        out = s.output(r["job_id"])
        self.assertEqual(out.get("type"), "output_response", out)
        self.assertTrue(out["content"].endswith("hola"))

    def test_trabajo_que_lee_stdin_no_se_cuelga(self):
        """Regresión F13: el trabajo recibe una entrada vacía (stdin=DEVNULL)."""
        s = self.servicio()
        j = s.esperar_estado(s.submit("cat")["job_id"], timeout=5)
        self.assertIsNotNone(j, "cat no debe quedarse esperando entrada")
        self.assertEqual(j["status"], "SUCCEEDED")


if __name__ == "__main__":
    unittest.main()
