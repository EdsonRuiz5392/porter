"""
TC-008  Aislamiento de fallo ............. RNF-08, RNF-09
TC-020  Terminación inesperada del hijo .. RF-29, RNF-30
TC-024  Liberación de recursos bajo carga .. RNF-33
"""
import asyncio
import os
import shutil
import signal
import time
import unittest

from jr_helpers import M, PruebaJobRunner, solicitud_async


class TC008Aislamiento(PruebaJobRunner):

    def test_un_trabajo_que_falla_no_afecta_a_otros(self):
        s = self.servicio(MAX_CONCURRENCY=3)
        largo = s.submit("sleep", "2")["job_id"]
        s.esperar_estado(largo, ("RUNNING",))
        malo = s.submit("bash", "-c", "kill -SEGV $$")["job_id"]
        roto = s.submit("programa_que_no_existe")["job_id"]
        self.assertEqual(s.esperar_estado(malo)["status"], "FAILED")
        self.assertEqual(s.esperar_estado(roto)["status"], "FAILED")
        self.assertEqual(s.esperar_estado(largo, timeout=10)["status"], "SUCCEEDED")
        self.assertTrue(s.vivo())


class TC020MuerteInesperada(PruebaJobRunner):

    def test_senal_externa_queda_failed_con_diagnostico(self):
        """Regresión F11: antes kill -9 externo quedaba CANCELED."""
        s = self.servicio(MAX_CONCURRENCY=3)
        for nombre, sig in (("SIGKILL", signal.SIGKILL), ("SIGTERM", signal.SIGTERM),
                            ("SIGSEGV", signal.SIGSEGV)):
            with self.subTest(senal=nombre):
                j = s.submit("sleep", "31")["job_id"]
                pid = s.esperar_estado(j, ("RUNNING",))["pid"]
                os.kill(pid, sig)
                fin = s.esperar_estado(j, timeout=6)
                self.assertEqual((fin["status"], fin["exit_code"]), ("FAILED", -int(sig)))
                self.assertTrue(s.eventos("KILLED_BY_SIGNAL", j))
        self.assertEqual(s.health()["running"], 0, "Se liberan los cupos")

    def test_falla_de_captura_no_deja_procesos_ni_descuadra_el_limite(self):
        """Regresión F6: el proceso se termina y la reserva de cupo se libera una sola vez."""
        s = self.servicio(MAX_CONCURRENCY=1)
        salida = s.data / "output"
        shutil.rmtree(salida); salida.write_text("")             # provoca el error al abrir la salida
        a = s.submit("sleep", "341")["job_id"]
        fin = s.esperar_estado(a, timeout=10)
        self.assertEqual((fin["status"], fin["exit_code"]), ("FAILED", -1))
        self.assertEqual(s.procesos("sleep 341"), [], "El proceso no debe quedar vivo")
        salida.unlink(); salida.mkdir()
        s.submit("sleep", "342"); s.submit("sleep", "343")
        time.sleep(1.5)
        self.assertEqual(len(s.procesos("sleep 342")) + len(s.procesos("sleep 343")), 1,
                         "Con límite 1 solo debe correr uno")
        h = s.health()
        self.assertEqual((h["running"], h["queued"]), (1, 1))


class TC024RecursosBajoCarga(PruebaJobRunner):

    def test_cuatro_lotes_de_90_sin_fugas(self):
        s = self.servicio(MAX_CONCURRENCY=3, MAX_QUEUE=200)

        async def _lote(n):
            return await asyncio.gather(*[
                solicitud_async(s.port, M("submit", command="echo", args=[f"{n}-{i}"])) for i in range(90)])

        descriptores = []
        for n in range(4):
            respuestas = asyncio.run(_lote(n))
            self.assertTrue(all(r.get("status") == "QUEUED" for r in respuestas))
            self.assertTrue(s.esperar_vacio(60))
            time.sleep(0.5)
            descriptores.append(s.descriptores())
        estados = dict(s.db("select status, count(*) from jobs group by status"))
        self.assertEqual(estados, {"SUCCEEDED": 360})
        self.assertEqual(s.zombis_hijos(), 0, "Sin procesos zombi")
        self.assertEqual(s.procesos(), [], "Sin procesos hijos vivos")
        self.assertLessEqual(max(descriptores) - min(descriptores), 1,
                             f"Los descriptores no deben crecer entre lotes: {descriptores}")
        print(f"\n    TC-024: descriptores abiertos tras cada lote de 90: {descriptores}")


if __name__ == "__main__":
    unittest.main()
