"""
TC-001  Enviar trabajo válido ............ RF-01, RF-02, RNF-14
TC-015  Ayuda y códigos de salida del CLI .. RF-17, RNF-21
"""
import unittest

from jr_helpers import M, PruebaJobRunner, puerto_libre, Servicio


class TC001EnvioYValidacion(PruebaJobRunner):

    def test_envio_valido_devuelve_id_unico(self):
        """RF-01: cada envío válido devuelve un ID distinto y estado QUEUED."""
        s = self.servicio()
        respuestas = [s.submit("echo", f"n{i}") for i in range(5)]
        for r in respuestas:
            self.assertEqual(r.get("type"), "submit_response", r)
            self.assertEqual(r.get("status"), "QUEUED", r)
        self.assertEqual(len({r["job_id"] for r in respuestas}), 5, "Los IDs deben ser únicos")

    def test_entradas_invalidas_se_rechazan_con_invalid_request(self):
        """RF-02 / RNF-14: tipos y tamaños inválidos -> INVALID_REQUEST con mensaje (sin INTERNAL_ERROR)."""
        s = self.servicio()
        casos = {
            "comando vacío": M("submit", command="", args=[]),
            "comando solo espacios": M("submit", command="   ", args=[]),
            "comando ausente": M("submit", args=[]),
            "command=5": M("submit", command=5, args=[]),
            "args texto": M("submit", command="echo", args="abc"),
            "args con números": M("submit", command="echo", args=[1, 2]),
            "comando de 100 KB": M("submit", command="x" * 100_000, args=[]),
            "folio no texto": M("submit", command="echo", args=[], client_request_id=7),
            "status job_id lista": M("status", job_id=[1]),
            "cancel sin job_id": M("cancel"),
            "list estado inexistente": M("list", status_filter="BOGUS"),
            "output stream inválido": M("output", job_id="x", stream="foo"),
            "tipo desconocido": M("bogus"),
        }
        for nombre, msg in casos.items():
            with self.subTest(caso=nombre):
                r = s.pedir(msg)
                self.assertEqual(r.get("type"), "error", r)
                self.assertEqual(r.get("code"), "INVALID_REQUEST", r)
                self.assertTrue(r.get("message"), "El error debe traer un mensaje útil")
        self.assertTrue(s.vivo(), "Ninguna entrada inválida debe tumbar el servicio (RNF-08)")
        self.assertEqual(s.db("select count(*) from jobs")[0][0], 0, "No debe crearse ningún trabajo")

    def test_args_null_equivale_a_lista_vacia(self):
        s = self.servicio()
        r = s.pedir(M("submit", command="echo", args=None))
        self.assertEqual(r.get("type"), "submit_response", r)
        j = s.esperar_estado(r["job_id"])
        self.assertEqual(j["status"], "SUCCEEDED", j)

    def test_comando_inexistente_termina_failed(self):
        """Un programa que no existe nunca llega a RUNNING y queda FAILED con diagnóstico."""
        s = self.servicio()
        r = s.submit("programa_que_no_existe_xyz")
        j = s.esperar_estado(r["job_id"])
        self.assertEqual((j["status"], j["exit_code"]), ("FAILED", -1), j)
        self.assertIsNone(j["started_at"], j)
        self.assertTrue(s.eventos("ERROR", r["job_id"]), "Debe registrarse el error en la bitácora")


class TC015AyudaYCodigosCLI(PruebaJobRunner):

    def test_ayuda_y_codigos_de_salida(self):
        s = self.servicio()
        codigo, texto = s.cli("--help")
        self.assertEqual(codigo, 0)
        for palabra in ("submit", "status", "list", "cancel", "output", "health", "--request-id"):
            self.assertIn(palabra, texto)
        self.assertEqual(s.cli()[0], 0, "Sin argumentos muestra la ayuda")
        self.assertEqual(s.cli("submit")[0], 1, "submit sin comando es error")
        self.assertEqual(s.cli("status")[0], 1, "status sin ID es error")
        self.assertEqual(s.cli("comando_raro")[0], 1, "comando desconocido es error")
        codigo, texto = s.cli("status", "no-existe")
        self.assertEqual(codigo, 1)
        self.assertIn("NOT_FOUND", texto)

    def test_servicio_apagado_da_codigo_1_y_sugerencia(self):
        s = Servicio(self._carpeta / "apagado")      # nunca se inicia
        s.env["JOBRUNNER_PORT"] = str(puerto_libre())
        codigo, texto = s.cli("health")
        self.assertEqual(codigo, 1)
        self.assertIn("conexión", texto.lower())


if __name__ == "__main__":
    unittest.main()
