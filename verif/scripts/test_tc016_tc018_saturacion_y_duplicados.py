"""
TC-016  Saturación de cola y rechazo explícito ... RF-25, RNF-29
TC-018  Solicitud duplicada ...................... RF-27
(ADR-007 y ADR-008)
"""
import unittest
from collections import Counter

from jr_helpers import M, PruebaJobRunner, en_paralelo


class TC016Saturacion(PruebaJobRunner):

    def test_rechazo_explicito_secuencial(self):
        s = self.servicio(MAX_CONCURRENCY=1, MAX_QUEUE=3)
        a = s.submit("sleep", "60")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        resultados = [s.submit("sleep", "60") for _ in range(5)]
        self.assertEqual([r.get("status") or r.get("code") for r in resultados],
                         ["QUEUED", "QUEUED", "QUEUED", "QUEUE_FULL", "QUEUE_FULL"])
        self.assertEqual(len(s.eventos("REJECTED")), 2, "Los rechazos se registran (RF-23)")
        self.assertEqual(s.health()["queued"], 3)

    def test_carrera_diez_envios_con_un_lugar(self):
        """Regresión F1: antes 9 INTERNAL_ERROR y 9 filas fantasma."""
        s = self.servicio(MAX_CONCURRENCY=1, MAX_QUEUE=3)
        a = s.submit("sleep", "60")["job_id"]
        s.esperar_estado(a, ("RUNNING",))
        s.submit("sleep", "60"); s.submit("sleep", "60")          # queda 1 lugar
        respuestas = en_paralelo(s.port, [M("submit", command="sleep", args=["60"])] * 10)
        conteo = Counter(r.get("status") or r.get("code") for r in respuestas)
        self.assertEqual(conteo, Counter({"QUEUE_FULL": 9, "QUEUED": 1}))
        filas = dict(s.db("select status, count(*) from jobs group by status"))
        self.assertEqual(filas, {"RUNNING": 1, "QUEUED": 3}, "Sin trabajos fantasma")
        self.assertEqual(s.health()["queued"], 3)


class TC018Duplicados(PruebaJobRunner):

    def test_a_reintento_mismo_folio_mismo_comando(self):
        s = self.servicio()
        r1 = s.submit("echo", "uno", folio="F1")
        s.esperar_estado(r1["job_id"])
        r2 = s.submit("echo", "uno", folio="F1")
        self.assertEqual(r2["job_id"], r1["job_id"])
        self.assertEqual(r2["status"], "SUCCEEDED", "Devuelve el original en cualquier estado")
        self.assertEqual(s.db("select count(*) from jobs")[0][0], 1)
        self.assertTrue(s.eventos("DUPLICATE"))

    def test_b_sin_folio_cada_envio_es_nuevo(self):
        s = self.servicio()
        ids = {s.submit("echo", "igual")["job_id"] for _ in range(3)}
        self.assertEqual(len(ids), 3)

    def test_c_mismo_folio_otro_comando_es_conflicto(self):
        """Regresión F8: antes el trabajo original desaparecía (INSERT OR REPLACE)."""
        s = self.servicio()
        r1 = s.submit("echo", "uno", folio="F1")
        s.esperar_estado(r1["job_id"])
        for comando, args in (("ls", []), ("echo", ["dos"])):
            with self.subTest(comando=comando, args=args):
                r = s.submit(comando, *args, folio="F1")
                self.assertEqual((r.get("type"), r.get("code")), ("error", "REQUEST_ID_CONFLICT"), r)
                self.assertIn("ya se usó con otro comando", r["message"])
        original = s.job(r1["job_id"])
        self.assertEqual((original["command"], original["args"], original["status"]),
                         ("echo", ["uno"], "SUCCEEDED"))

    def test_d_seis_envios_simultaneos_mismo_folio(self):
        s = self.servicio()
        respuestas = en_paralelo(s.port, [M("submit", command="sleep", args=["1"],
                                            client_request_id="F2")] * 6)
        self.assertEqual(len({r.get("job_id") for r in respuestas}), 1, respuestas)
        self.assertEqual(s.db("select count(*) from jobs where client_request_id='F2'")[0][0], 1)

    def test_cli_request_id(self):
        s = self.servicio()
        c1, o1 = s.cli("submit", "--request-id", "pedido-1", "echo", "hola")
        c2, o2 = s.cli("submit", "--request-id", "pedido-1", "echo", "hola")
        c3, o3 = s.cli("submit", "--request-id", "pedido-1", "ls")
        c4, _ = s.cli("submit", "--request-id")
        self.assertEqual((c1, c2, c3, c4), (0, 0, 1, 1))
        self.assertEqual(o1.split("ID: ")[1].split()[0], o2.split("ID: ")[1].split()[0])
        self.assertIn("REQUEST_ID_CONFLICT", o3)


if __name__ == "__main__":
    unittest.main()
