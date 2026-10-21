"""
TC-012  Fragmentación y desconexión ...... RF-21, RF-22, RNF-14, RNF-24
TC-019  Desconexión durante solicitud .... RF-28, RF-22
TC-023  Compatibilidad de protocolo ...... RNF-32
"""
import asyncio
import json
import socket
import struct
import time
import unittest

from jr_helpers import M, PruebaJobRunner, leer_mensaje, trama


class TC012Protocolo(PruebaJobRunner):

    def test_mensaje_byte_a_byte_y_varias_solicitudes_por_conexion(self):
        s = self.servicio()

        async def _prueba():
            r, w = await asyncio.open_connection("127.0.0.1", s.port)
            try:
                for byte in trama(M("health")):
                    w.write(bytes([byte])); await w.drain()
                    await asyncio.sleep(0.002)
                primera = await leer_mensaje(r)
                w.write(trama(M("list"))); await w.drain()
                segunda = await leer_mensaje(r)
                w.write(trama(M("health")) + trama(M("list"))); await w.drain()   # dos pegados
                tercera, cuarta = await leer_mensaje(r), await leer_mensaje(r)
                return [x["type"] for x in (primera, segunda, tercera, cuarta)]
            finally:
                w.close()

        self.assertEqual(asyncio.run(_prueba()),
                         ["health_response", "list_response", "health_response", "list_response"])

    def test_mensajes_invalidos_reciben_error_y_no_tumban_el_servicio(self):
        """Regresión F15: antes se cortaba la conexión sin respuesta ni registro."""
        s = self.servicio()
        casos = {
            "longitud de 2 GB": struct.pack("!I", 2_000_000_000),
            "JSON inválido": struct.pack("!I", 11) + b"{no es json",
            "JSON que no es objeto": struct.pack("!I", 7) + b"[1,2,3]",
        }

        async def _enviar(datos):
            r, w = await asyncio.open_connection("127.0.0.1", s.port)
            try:
                w.write(datos); await w.drain()
                return await asyncio.wait_for(leer_mensaje(r), 3)
            finally:
                w.close()

        for nombre, datos in casos.items():
            with self.subTest(caso=nombre):
                resp = asyncio.run(_enviar(datos))
                self.assertEqual((resp.get("type"), resp.get("code")), ("error", "INVALID_REQUEST"), resp)
        self.assertEqual(len(s.eventos("PROTOCOL_ERROR")), 3)
        self.assertTrue(s.vivo())
        self.assertEqual(s.health().get("type"), "health_response")


class TC019Desconexion(PruebaJobRunner):

    def test_desconexion_tras_mensaje_completo_la_operacion_queda_aceptada(self):
        s = self.servicio()
        sk = socket.create_connection(("127.0.0.1", s.port))
        sk.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))   # RST al cerrar
        sk.sendall(trama(M("submit", command="echo", args=["sin_respuesta"])))
        sk.close()
        time.sleep(0.6)
        trabajos = s.listar()["jobs"]
        self.assertEqual(len(trabajos), 1, "La operación fue aceptada (D10)")
        self.assertNotIn("Traceback", s.salida())
        self.assertTrue(s.vivo())

    def test_desconexion_a_medio_mensaje_no_tiene_efecto(self):
        s = self.servicio()
        datos = trama(M("submit", command="echo", args=["a_medias"]))
        sk = socket.create_connection(("127.0.0.1", s.port))
        sk.sendall(datos[: len(datos) // 2]); sk.close()
        time.sleep(0.6)
        self.assertEqual(s.listar()["jobs"], [], "Sin mensaje completo, no se crea nada")
        self.assertTrue(s.vivo())

    def test_reintento_con_folio_recupera_el_id(self):
        """D10: si el cliente perdió la respuesta, reenviar con el mismo folio devuelve el mismo trabajo."""
        s = self.servicio()
        sk = socket.create_connection(("127.0.0.1", s.port))
        sk.sendall(trama(M("submit", command="echo", args=["x"], client_request_id="reintento-1")))
        sk.close()
        time.sleep(0.5)
        original = s.listar()["jobs"][0]["id"]
        r = s.submit("echo", "x", folio="reintento-1")
        self.assertEqual(r["job_id"], original)
        self.assertEqual(len(s.listar()["jobs"]), 1)


class TC023CompatibilidadProtocolo(PruebaJobRunner):

    def test_version_incompatible_se_rechaza_explicitamente(self):
        s = self.servicio()
        for version in (99, None, "1"):
            with self.subTest(version=version):
                msg = {"type": "list"}
                if version is not None:
                    msg["version"] = version
                r = s.pedir(msg)
                self.assertEqual((r.get("type"), r.get("code")), ("error", "VERSION_UNSUPPORTED"), r)
        self.assertEqual(s.pedir(M("list")).get("type"), "list_response")


if __name__ == "__main__":
    unittest.main()
