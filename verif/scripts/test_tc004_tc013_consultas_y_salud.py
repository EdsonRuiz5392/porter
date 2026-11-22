"""
TC-004  Consultar y listar ............... RF-08, RF-09, RNF-05
TC-013  Configuración y salud ............ RF-16, RF-24
RNF-06  500 registros sin pérdida de metadatos
"""
import asyncio
import time
import unittest

from jr_helpers import M, PruebaJobRunner, solicitud_async


class TC004Consultas(PruebaJobRunner):

    def test_status_list_y_filtro(self):
        s = self.servicio()
        ok = s.submit("true")["job_id"]
        mal = s.submit("false")["job_id"]
        s.esperar_estado(ok), s.esperar_estado(mal)

        j = s.job(ok)
        for campo in ("id", "command", "args", "status", "pid", "submitted_at",
                      "started_at", "finished_at", "exit_code", "client_request_id"):
            self.assertIn(campo, j)

        self.assertEqual(len(s.listar()["jobs"]), 2)
        self.assertEqual([x["id"] for x in s.listar("SUCCEEDED")["jobs"]], [ok])
        self.assertEqual([x["id"] for x in s.listar("FAILED")["jobs"]], [mal])
        r = s.status("no-existe")
        self.assertEqual((r.get("type"), r.get("code")), ("error", "NOT_FOUND"))

        codigo, texto = s.cli("list", "--status", "failed")
        self.assertEqual(codigo, 0)
        self.assertIn(mal, texto)
        self.assertNotIn(ok, texto)
        codigo, texto = s.cli("status", ok)
        self.assertEqual(codigo, 0)
        for palabra in ("PID", "Inicio", "Fin", "Exit code"):
            self.assertIn(palabra, texto)

    def test_rnf05_consulta_en_menos_de_un_segundo_con_100_trabajos(self):
        s = self.servicio(MAX_CONCURRENCY=10, MAX_QUEUE=200)
        ids = [s.submit("true")["job_id"] for _ in range(100)]
        self.assertTrue(s.esperar_vacio(60))
        t0 = time.time(); s.status(ids[50]); t_status = time.time() - t0
        t0 = time.time(); n = len(s.listar()["jobs"]); t_list = time.time() - t0
        self.assertEqual(n, 100)
        self.assertLess(t_status, 1.0, f"status tardó {t_status:.3f} s")
        self.assertLess(t_list, 1.0, f"list tardó {t_list:.3f} s")
        print(f"\n    RNF-05: status {t_status*1000:.1f} ms, list(100) {t_list*1000:.1f} ms")

    def test_rnf06_500_registros_sin_perdida_tras_reinicio(self):
        s = self.servicio(MAX_CONCURRENCY=10, MAX_QUEUE=600)

        async def _enviar_500():
            out = []
            for lote in range(10):
                out += await asyncio.gather(*[
                    solicitud_async(s.port, M("submit", command="echo", args=[f"{lote}-{i}"]))
                    for i in range(50)])
            return out

        respuestas = asyncio.run(_enviar_500())
        self.assertEqual(sum(r.get("type") == "submit_response" for r in respuestas), 500)
        self.assertTrue(s.esperar_vacio(120))
        s.detener()
        self.assertTrue(s.iniciar())
        filas = s.db("select status, submitted_at, started_at, finished_at, exit_code from jobs")
        self.assertEqual(len(filas), 500)
        self.assertTrue(all(f[0] == "SUCCEEDED" and all(v is not None for v in f[1:]) for f in filas),
                        "Todos con estado y tiempos completos")
        self.assertEqual(len(s.listar()["jobs"]), 500)


class TC013ConfiguracionYSalud(PruebaJobRunner):

    def test_health(self):
        s = self.servicio(MAX_CONCURRENCY=1)
        s.submit("sleep", "3"); s.submit("sleep", "3"); s.submit("false")
        time.sleep(0.5)
        h = s.health()
        self.assertEqual((h["active"], h["running"], h["queued"]), (True, 1, 2), h)
        codigo, texto = s.cli("health")
        self.assertEqual(codigo, 0)
        self.assertIn("activo", texto)

    def test_configuracion_invalida_no_arranca(self):
        casos = {"MAX_CONCURRENCY": ["0", "-2", "abc"], "MAX_QUEUE": ["0"], "PORT": ["99999"],
                 "GRACE_SECONDS": ["-1"], "SHUTDOWN_TIMEOUT": ["x"]}
        for var, valores in casos.items():
            for valor in valores:
                with self.subTest(variable=var, valor=valor):
                    s = self.servicio(f"cfg_{var}_{valor}", iniciar=False)
                    s.env["JOBRUNNER_" + var] = valor
                    self.assertFalse(s.iniciar(), f"{var}={valor} no debería permitir arrancar")
                    self.assertNotEqual(s.p.returncode, 0)
                    self.assertIn("Configuración inválida", s.salida())
                    self.assertIn(var, s.salida())

    def test_configuracion_se_registra_al_arrancar(self):
        s = self.servicio(MAX_CONCURRENCY=2, MAX_QUEUE=7)
        inicio = s.eventos("SERVICE_STARTED")
        self.assertTrue(inicio)
        self.assertIn("concurrencia=2", inicio[0])
        self.assertIn("cola=7", inicio[0])


if __name__ == "__main__":
    unittest.main()
