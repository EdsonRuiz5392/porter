"""
TC-016  Saturación: límite de clientes simultáneos ... RF-23, RNF-29
TC-024  Liberación de sockets con clientes lentos u ociosos ... RNF-08, RNF-33
(ADR-014: límites de conexiones y tiempos de espera)
"""
import asyncio
import socket
import struct
import time
import unittest

from jr_helpers import M, PruebaJobRunner, esperar_que, leer_mensaje, trama


class TC016LimiteDeClientes(PruebaJobRunner):

    def test_cliente_de_mas_recibe_too_many_clients(self):
        """RNF-29: al llegar al máximo de conexiones, la siguiente se rechaza de forma explícita."""
        s = self.servicio(MAX_CLIENTS=3, IDLE_TIMEOUT=30)
        self.assertTrue(s.esperar_sin_clientes())
        abiertos = []
        try:
            for _ in range(3):                          # ocupan los 3 lugares sin mandar nada
                sk = socket.create_connection(("127.0.0.1", s.port))
                abiertos.append(sk)
            time.sleep(0.3)
            r = s.pedir(M("health"))
            self.assertEqual((r.get("type"), r.get("code")), ("error", "TOO_MANY_CLIENTS"), r)
            self.assertTrue(r.get("message"))
            self.assertEqual(len(s.eventos("CLIENT_REJECTED")), 1, "El rechazo se registra (RF-23)")
        finally:
            for sk in abiertos:
                sk.close()
        # al liberarse los lugares vuelve a atender
        ok = esperar_que(lambda: s.pedir(M("health")).get("type") == "health_response", 5)
        self.assertTrue(ok, "Al cerrarse las conexiones se liberan los lugares")

    def test_health_reporta_clientes_conectados(self):
        s = self.servicio(MAX_CLIENTS=5)
        self.assertTrue(s.esperar_sin_clientes())
        sk = socket.create_connection(("127.0.0.1", s.port))
        try:
            time.sleep(0.3)
            h = s.health()
            self.assertEqual(h.get("max_clients"), 5, h)
            self.assertEqual(h.get("clients_connected"), 2, "El ocioso + la conexión de esta consulta")
        finally:
            sk.close()

    def test_muchos_clientes_simultaneos_dentro_del_limite(self):
        """Soporte para múltiples clientes: 20 a la vez, todos atendidos."""
        s = self.servicio(MAX_CLIENTS=32)

        async def _todos():
            async def uno(i):
                r, w = await asyncio.open_connection("127.0.0.1", s.port)
                try:
                    w.write(trama(M("submit", command="echo", args=[f"c{i}"]))); await w.drain()
                    a = await asyncio.wait_for(leer_mensaje(r), 10)
                    w.write(trama(M("status", job_id=a["job_id"]))); await w.drain()
                    b = await asyncio.wait_for(leer_mensaje(r), 10)
                    return a["type"], b["type"]
                finally:
                    w.close()
            return await asyncio.gather(*[uno(i) for i in range(20)])
        self.assertEqual(asyncio.run(_todos()), [("submit_response", "status_response")] * 20)


class TC024ClientesLentosYOciosos(PruebaJobRunner):

    def test_cliente_ocioso_se_desconecta_y_libera_su_lugar(self):
        s = self.servicio(MAX_CLIENTS=1, IDLE_TIMEOUT=1)
        self.assertTrue(s.esperar_sin_clientes())
        sk = socket.create_connection(("127.0.0.1", s.port))
        try:
            sk.settimeout(5)
            t0 = time.time()
            datos = sk.recv(100)                      # el servicio cierra: recv devuelve b""
            self.assertEqual(datos, b"", "El servicio debe cerrar la conexión ociosa")
            self.assertLess(time.time() - t0, 4)
        finally:
            sk.close()
        self.assertEqual(s.pedir(M("health")).get("type"), "health_response", "El lugar quedó libre")
        self.assertTrue(s.eventos("CLIENT_TIMEOUT"))

    def test_mensaje_a_medias_no_retiene_la_conexion(self):
        """Un cliente que manda el encabezado y nunca el cuerpo (slowloris) se corta con TIMEOUT."""
        s = self.servicio(MESSAGE_TIMEOUT=1, IDLE_TIMEOUT=30)

        async def _medio():
            r, w = await asyncio.open_connection("127.0.0.1", s.port)
            try:
                w.write(struct.pack("!I", 50) + b'{"version": 1'); await w.drain()
                return await asyncio.wait_for(leer_mensaje(r), 5)
            finally:
                w.close()
        t0 = time.time()
        r = asyncio.run(_medio())
        self.assertEqual((r.get("type"), r.get("code")), ("error", "TIMEOUT"), r)
        self.assertLess(time.time() - t0, 4)
        self.assertTrue(s.vivo())

    def test_descriptores_vuelven_a_la_base_tras_muchas_conexiones(self):
        """RNF-33: 200 conexiones (válidas, rechazadas y cortadas) no dejan sockets abiertos."""
        s = self.servicio(ALLOWED_NETWORKS="127.0.0.1", MAX_CLIENTS=50)
        s.health()
        base = s.descriptores()

        async def _carga():
            async def valida():
                r, w = await asyncio.open_connection("127.0.0.1", s.port)
                w.write(trama(M("list"))); await w.drain()
                await leer_mensaje(r); w.close()
            async def rechazada():
                r, w = await asyncio.open_connection("127.0.0.1", s.port, local_addr=("127.0.0.9", 0))
                try:
                    await asyncio.wait_for(leer_mensaje(r), 5)
                finally:
                    w.close()
            async def cortada():
                r, w = await asyncio.open_connection("127.0.0.1", s.port)
                w.write(struct.pack("!I", 10)); await w.drain(); w.close()
            for _ in range(5):
                await asyncio.gather(*([valida() for _ in range(15)] + [rechazada() for _ in range(15)]
                                       + [cortada() for _ in range(10)]))
        asyncio.run(_carga())
        ok = esperar_que(lambda: s.descriptores() <= base + 2, 10)
        self.assertTrue(ok, f"Descriptores: base {base}, ahora {s.descriptores()}")
        self.assertEqual(s.health().get("clients_connected"), 1)


if __name__ == "__main__":
    unittest.main()
