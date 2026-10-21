"""
TC-005  Cancelar en cola y en ejecución .. RF-10
TC-017  Cancelaciones concurrentes ....... RF-26, RNF-27
TC-021  Escalamiento de cancelación ...... RF-30
(ADR-009: grupos de procesos, cancelación pendiente, caso A/B)
"""
import asyncio
import time
import unittest

from jr_helpers import M, PruebaJobRunner, en_paralelo, leer_mensaje, trama


class TC005Cancelacion(PruebaJobRunner):

    def test_cancelar_en_cola(self):
        s = self.servicio(MAX_CONCURRENCY=1)
        a = s.submit("sleep", "30")["job_id"]
        b = s.submit("sleep", "30")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        self.assertEqual(s.cancel(b).get("result"), "CANCELING")
        j = s.esperar_estado(b, timeout=3)
        self.assertEqual(j["status"], "CANCELED")
        self.assertIsNone(j["started_at"], "Nunca debió ejecutarse")

    def test_cancelar_en_ejecucion(self):
        s = self.servicio()
        a = s.submit("sleep", "30")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        t0 = time.time()
        self.assertEqual(s.cancel(a).get("result"), "CANCELING")
        j = s.esperar_estado(a, timeout=5)
        self.assertEqual((j["status"], j["exit_code"]), ("CANCELED", -15))
        self.assertLess(time.time() - t0, 3)
        self.assertEqual(s.procesos("sleep 30"), [])
        self.assertEqual(s.cancel(a).get("result"), "ALREADY_FINISHED")
        r = s.cancel("no-existe")
        self.assertEqual((r.get("type"), r.get("code")), ("error", "NOT_FOUND"))
        self.assertTrue(s.eventos("CANCEL_REQUESTED", a))

    def test_cancelar_alcanza_a_los_nietos(self):
        """Regresión F4: antes el nieto seguía vivo y el trabajo seguía RUNNING ocupando el cupo."""
        s = self.servicio(MAX_CONCURRENCY=1, GRACE_SECONDS=2)
        a = s.submit("bash", "-c", "sleep 41; echo x")["job_id"]
        b = s.submit("echo", "siguiente")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        time.sleep(0.3)
        s.cancel(a)
        j = s.esperar_estado(a, timeout=6)
        self.assertIsNotNone(j, "El trabajo debe terminar aunque tenga nietos")
        self.assertEqual(j["status"], "CANCELED")
        self.assertEqual(s.procesos("sleep 41"), [], "El nieto debe morir")
        self.assertEqual(s.esperar_estado(b, timeout=5)["status"], "SUCCEEDED", "El cupo debe liberarse")


class TC017CancelacionesConcurrentes(PruebaJobRunner):

    def test_cinco_cancelaciones_simultaneas(self):
        s = self.servicio()
        a = s.submit("sleep", "30")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        respuestas = en_paralelo(s.port, [M("cancel", job_id=a)] * 5)
        self.assertEqual([r.get("result") for r in respuestas], ["CANCELING"] * 5)
        j = s.esperar_estado(a, timeout=5)
        self.assertEqual(j["status"], "CANCELED")
        self.assertEqual(len(s.eventos("CANCELED", a)), 1, "Un único estado final")

    def test_cancelar_inmediatamente_despues_de_enviar(self):
        """Regresión F3: antes, 25 de 25 respondían ALREADY_FINISHED y el trabajo corría completo."""
        s = self.servicio(MAX_CONCURRENCY=50)

        async def _envio_y_cancelacion():
            r1, w1 = await asyncio.open_connection("127.0.0.1", s.port)
            r2, w2 = await asyncio.open_connection("127.0.0.1", s.port)
            try:
                w1.write(trama(M("submit", command="sleep", args=["2"]))); await w1.drain()
                job_id = (await leer_mensaje(r1))["job_id"]
                w2.write(trama(M("cancel", job_id=job_id))); await w2.drain()
                return job_id, (await leer_mensaje(r2)).get("result")
            finally:
                w1.close(); w2.close()

        resultados = [asyncio.run(_envio_y_cancelacion()) for _ in range(20)]
        self.assertEqual({res for _, res in resultados}, {"CANCELING"})
        finales = [s.esperar_estado(j, timeout=10)["status"] for j, _ in resultados]
        self.assertEqual(set(finales), {"CANCELED"}, finales)

    def test_caso_a_cancelacion_llega_primero(self):
        """El programa sale con 0 al recibir SIGTERM, pero se pidió cancelar: CANCELED."""
        s = self.servicio(GRACE_SECONDS=3)
        a = s.submit("bash", "-c", "trap 'exit 0' TERM; sleep 30 & wait")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        time.sleep(0.3)
        s.cancel(a)
        j = s.esperar_estado(a, timeout=6)
        self.assertEqual((j["status"], j["exit_code"]), ("CANCELED", 0))

    def test_caso_b_termina_primero(self):
        s = self.servicio()
        b = s.submit("echo", "rapido")["job_id"]
        s.esperar_estado(b)
        self.assertEqual(s.cancel(b).get("result"), "ALREADY_FINISHED")
        self.assertEqual(s.job(b)["status"], "SUCCEEDED")


class TC021Escalamiento(PruebaJobRunner):

    def test_proceso_que_ignora_sigterm(self):
        s = self.servicio(GRACE_SECONDS=2)
        a = s.submit("bash", "-c", "trap '' TERM; sleep 30")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        time.sleep(0.3)
        t0 = time.time()
        s.cancel(a)
        j = s.esperar_estado(a, timeout=10)
        dt = time.time() - t0
        self.assertEqual((j["status"], j["exit_code"]), ("CANCELED", -9))
        self.assertGreaterEqual(dt, 1.8, "Debe respetar el tiempo de gracia")
        self.assertLess(dt, 5, "Debe escalar poco después del tiempo de gracia")
        self.assertIn("Escalando a SIGKILL", s.salida())
        self.assertEqual(s.procesos(), [])
        print(f"\n    TC-021: escalamiento a SIGKILL en {dt:.2f} s (grace=2 s)")


if __name__ == "__main__":
    unittest.main()
