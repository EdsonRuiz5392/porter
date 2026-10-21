"""
TC-002  Cola y límite de concurrencia .... RF-03, RF-05, RNF-04, RNF-07
"""
import time
import unittest
from datetime import datetime

from jr_helpers import PruebaJobRunner


class TC002ColaYConcurrencia(PruebaJobRunner):

    def test_ocho_trabajos_con_limite_tres(self):
        s = self.servicio(MAX_CONCURRENCY=3)
        ids = [s.submit("sleep", "2")["job_id"] for _ in range(8)]

        max_running, max_hijos, muestras = 0, 0, []
        for _ in range(15):
            h = s.health()
            hijos = len(s.procesos("sleep 2"))
            max_running = max(max_running, h["running"])
            max_hijos = max(max_hijos, hijos)
            muestras.append((h["running"], h["queued"], hijos))
            time.sleep(0.2)

        trabajos = [s.esperar_estado(i, timeout=30) for i in ids]
        self.assertTrue(all(trabajos), "Todos deben terminar")
        self.assertEqual({j["status"] for j in trabajos}, {"SUCCEEDED"})

        # RNF-07: nunca más procesos que el límite; RNF-04: con límite 3 se sostienen 3.
        self.assertLessEqual(max_running, 3, muestras)
        self.assertLessEqual(max_hijos, 3, muestras)
        self.assertEqual(max_hijos, 3, f"Debe haber 3 simultáneos en algún momento: {muestras}")

        # Comprobación independiente con los tiempos guardados (RF-07).
        eventos = []
        for j in trabajos:
            eventos.append((datetime.fromisoformat(j["started_at"]), 1))
            eventos.append((datetime.fromisoformat(j["finished_at"]), -1))
        actual = maximo = 0
        for _, d in sorted(eventos, key=lambda e: (e[0], e[1])):
            actual += d
            maximo = max(maximo, actual)
        self.assertLessEqual(maximo, 3, "Solapamiento según tiempos guardados")

    def test_fifo(self):
        """RF-03: con límite 1, los trabajos arrancan en el orden en que llegaron."""
        s = self.servicio(MAX_CONCURRENCY=1)
        ids = [s.submit("sleep", "0.3")["job_id"] for _ in range(4)]
        trabajos = [s.esperar_estado(i, timeout=20) for i in ids]
        inicios = [j["started_at"] for j in trabajos]
        self.assertEqual(inicios, sorted(inicios), "Deben arrancar en orden FIFO")


if __name__ == "__main__":
    unittest.main()
