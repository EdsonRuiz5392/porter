"""
TC-007  Reinicio y recuperación .......... RF-12, RF-13, RNF-10, RNF-11, RNF-30, RNF-31
TC-022  Recuperación con más pendientes que lugares / interrupción ... RNF-28, RNF-31
(ADR-011)
"""
import os
import signal
import sqlite3
import subprocess
import time
import unittest
from datetime import datetime, timedelta, timezone

from jr_helpers import PruebaJobRunner, esperar_que


class TC007Recuperacion(PruebaJobRunner):

    def test_kill9_con_trabajos_corriendo_y_en_cola(self):
        s = self.servicio(MAX_CONCURRENCY=3)
        terminado = s.submit("echo", "antes")["job_id"]
        s.esperar_estado(terminado)
        antes = s.job(terminado)
        corriendo = [s.submit("sleep", "777")["job_id"] for _ in range(3)]
        en_cola = s.submit("sleep", "1")["job_id"]
        for j in corriendo:
            s.esperar_estado(j, ("RUNNING",))
        self.assertEqual(s.job(en_cola)["status"], "QUEUED")

        s.matar()                                   # caída no controlada
        self.assertEqual(len(s.procesos("sleep 777")), 3, "Tras la caída los 3 siguen vivos")
        self.assertTrue(s.iniciar())

        for j in corriendo:
            jj = s.job(j)
            self.assertEqual((jj["status"], jj["exit_code"]), ("FAILED", -1), jj)
        self.assertEqual(len(s.eventos("INTERRUPTED")), 3)
        self.assertEqual(s.job(terminado), antes, "Los terminados no se tocan (RF-12)")
        self.assertEqual(s.esperar_estado(en_cola, timeout=10)["status"], "SUCCEEDED", "El QUEUED se reanuda")
        self.assertEqual(s.procesos("sleep 777"), [], "No deben quedar huérfanos (RNF-30)")
        self.assertEqual(len(s.eventos("ORPHAN_KILLED")), 3)
        self.assertEqual(s.health()["running"], 0, "No reportar RUNNING lo que no controla (RNF-10)")

    def test_nieto_huerfano_con_lider_muerto(self):
        s = self.servicio(MAX_CONCURRENCY=1)
        a = s.submit("bash", "-c", "sleep 339; echo fin")["job_id"]
        j = s.esperar_estado(a, ("RUNNING",))
        time.sleep(0.3)
        s.matar()
        os.kill(j["pid"], signal.SIGKILL)          # muere también el líder: solo queda el nieto
        self.assertTrue(esperar_que(lambda: len(s.procesos("sleep 339")) == 1, 3))
        self.assertTrue(s.iniciar())
        self.assertTrue(esperar_que(lambda: s.procesos("sleep 339") == [], 3), "El nieto debe eliminarse")

    def test_pid_reutilizado_no_se_mata(self):
        """La base dice RUNNING con un PID que ahora pertenece a otro programa: no se toca."""
        s = self.servicio()
        s.detener()
        ajeno = subprocess.Popen(["sleep", "340"], start_new_session=True)   # sin la marca de la prueba
        try:
            hace_una_hora = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
            c = sqlite3.connect(s.data / "jobs.db")
            c.execute("insert into jobs(id,command,args,status,pid,submitted_at,started_at) "
                      "values(?,?,?,?,?,?,?)",
                      ("pid-reutilizado", "sleep", "[]", "RUNNING", ajeno.pid, hace_una_hora, hace_una_hora))
            c.commit(); c.close()
            self.assertTrue(s.iniciar())
            time.sleep(0.5)
            self.assertIsNone(ajeno.poll(), "El programa ajeno debe seguir vivo")
            self.assertEqual(s.job("pid-reutilizado")["status"], "FAILED")
            self.assertTrue(s.eventos("ORPHAN_SKIPPED", "pid-reutilizado"))
        finally:
            ajeno.kill(); ajeno.wait()


class TC022RecuperacionCapacidad(PruebaJobRunner):

    def test_bajar_max_queue_con_pendientes(self):
        """Regresión: antes el servicio no arrancaba (QueueFullError en recover_on_startup)."""
        s = self.servicio(MAX_CONCURRENCY=1, MAX_QUEUE=10)
        largo = s.submit("sleep", "338")["job_id"]
        s.esperar_estado(largo, ("RUNNING",))
        pendientes = [s.submit("sleep", "0.3")["job_id"] for _ in range(8)]
        s.matar()
        s.configurar(MAX_QUEUE=3)
        self.assertTrue(s.iniciar(), f"Debe arrancar aunque haya 8 pendientes y capacidad 3:\n{s.salida()}")
        self.assertTrue(s.eventos("RECOVERY_OVER_CAPACITY"))
        self.assertEqual(s.submit("echo", "nuevo").get("code"), "QUEUE_FULL",
                         "Mientras se excede la capacidad, no se aceptan nuevos")
        self.assertTrue(s.esperar_vacio(30))
        self.assertEqual({s.job(p)["status"] for p in pendientes}, {"SUCCEEDED"},
                         "Ningún trabajo aceptado se pierde (RF-25)")
        self.assertEqual(s.submit("echo", "despues").get("status"), "QUEUED")

    def test_base_integra_tras_kill9_durante_escrituras(self):
        """RNF-28: matar el servicio en plena actividad no deja la base inutilizable."""
        s = self.servicio(MAX_CONCURRENCY=5, MAX_QUEUE=500)
        for _ in range(3):
            for i in range(60):
                s.submit("echo", str(i))
            time.sleep(0.05)
            s.matar()                                # en medio de escrituras de estado
            self.assertTrue(s.iniciar(), s.salida())
            integridad = s.db("pragma integrity_check")[0][0]
            self.assertEqual(integridad, "ok")
            self.assertEqual(s.listar().get("type"), "list_response")
        self.assertTrue(s.esperar_vacio(60))
        estados = {e for (e,) in s.db("select distinct status from jobs")}
        self.assertTrue(estados <= {"SUCCEEDED", "FAILED"}, f"Sin estados imposibles: {estados}")
        self.assertEqual(s.db("select count(*) from jobs where status='RUNNING'")[0][0], 0)


if __name__ == "__main__":
    unittest.main()
