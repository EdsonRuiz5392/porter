"""
TC-010  Flujo remoto completo en LAN/VPN .. RF-18, RF-19, RNF-26
TC-011  Restricción de red ............... RF-20, RNF-12, RNF-13
(ADR-013: acceso de red y lista de redes permitidas)

Cómo se simula "otro equipo" sin una segunda máquina: en Linux toda la red
127.0.0.0/8 es local, así que un cliente puede conectarse SALIENDO desde
127.0.0.3 o 127.0.0.9. Para el servicio esas son direcciones de origen
distintas de 127.0.0.1, igual que lo sería 192.168.43.23 en el hotspot o
10.8.0.2 en la VPN. La operación real entre dos equipos se demuestra aparte
(guía de demostración LAN); estas pruebas comprueban la lógica de forma
reproducible.
"""
import asyncio
import socket
import subprocess
import sys
import time
import unittest

from jr_helpers import REPO_ROOT, M, PruebaJobRunner, leer_mensaje, trama

REMOTO = "127.0.0.3"        # hace de "laptop autorizada"
INTRUSO = "127.0.0.9"       # hace de "equipo no autorizado"


def ip_lan():
    """Primera IPv4 que no sea de loopback, o None si el equipo no tiene red."""
    try:
        salida = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for ip in salida.split():
        if "." in ip and not ip.startswith("127."):
            return ip
    return None


class TC010FlujoRemoto(PruebaJobRunner):

    def test_flujo_completo_desde_otra_direccion_autorizada(self):
        """RF-18: enviar, consultar, listar, recuperar salida, cancelar y salud desde 'otro equipo'."""
        s = self.servicio(ALLOWED_NETWORKS=f"127.0.0.1,{REMOTO}/32")
        r = s.pedir(M("submit", command="echo", args=["hola remoto"]), origen=REMOTO)
        self.assertEqual(r.get("type"), "submit_response", r)
        rapido = r["job_id"]
        self.assertEqual(s.esperar_estado(rapido)["status"], "SUCCEEDED")

        st = s.pedir(M("status", job_id=rapido), origen=REMOTO)
        self.assertEqual(st["job"]["status"], "SUCCEEDED", st)
        ls = s.pedir(M("list"), origen=REMOTO)
        self.assertIn(rapido, [j["id"] for j in ls["jobs"]])
        out = s.pedir(M("output", job_id=rapido, stream="stdout"), origen=REMOTO)
        self.assertEqual(out.get("content"), "hola remoto\n", out)

        largo = s.pedir(M("submit", command="sleep", args=["301"]), origen=REMOTO)["job_id"]
        s.esperar_estado(largo, ("RUNNING",))
        c = s.pedir(M("cancel", job_id=largo), origen=REMOTO)
        self.assertEqual(c.get("result"), "CANCELING", c)
        self.assertEqual(s.esperar_estado(largo)["status"], "CANCELED")

        h = s.pedir(M("health"), origen=REMOTO)
        self.assertEqual(h.get("type"), "health_response", h)
        self.assertEqual(s.eventos("ACCESS_DENIED"), [], "Nada de esto debe rechazarse")

    def test_misma_semantica_local_y_remota(self):
        """RF-19: la misma solicitud da la misma forma de respuesta desde local y desde remoto."""
        s = self.servicio(ALLOWED_NETWORKS=f"127.0.0.1,{REMOTO}")
        local = s.pedir(M("submit", command="true", args=[]))
        remota = s.pedir(M("submit", command="true", args=[]), origen=REMOTO)
        self.assertEqual(set(local), set(remota))
        self.assertEqual((local["type"], local["status"]), (remota["type"], remota["status"]))
        for msg in (M("status", job_id="no-existe"), M("bogus")):
            with self.subTest(tipo=msg["type"]):
                a, b = s.pedir(msg), s.pedir(msg, origen=REMOTO)
                self.assertEqual((a.get("type"), a.get("code")), (b.get("type"), b.get("code")))

    def test_cli_con_host_y_puerto_explicitos(self):
        """El cliente remoto se apunta a otro equipo con --host/--port (o JOBRUNNER_HOST/PORT)."""
        s = self.servicio()
        env_sin_puerto = dict(s.env)
        env_sin_puerto.pop("JOBRUNNER_PORT")
        r = subprocess.run([sys.executable, "-m", "src.cliente.cli", "--host", "127.0.0.1",
                            "--port", str(s.port), "health"],
                           cwd=REPO_ROOT, env=env_sin_puerto, capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Servicio activo", r.stdout)

    def test_escucha_en_varias_direcciones(self):
        """JOBRUNNER_HOST acepta una lista: p. ej. localhost + la IP del hotspot o de la VPN."""
        s = self.servicio(HOST="127.0.0.1,127.0.0.4", ALLOWED_NETWORKS="127.0.0.0/8")
        for destino in ("127.0.0.1", "127.0.0.4"):
            with self.subTest(destino=destino):
                async def _pedir():
                    r, w = await asyncio.open_connection(destino, s.port)
                    try:
                        w.write(trama(M("health"))); await w.drain()
                        return await asyncio.wait_for(leer_mensaje(r), 5)
                    finally:
                        w.close()
                self.assertEqual(asyncio.run(_pedir()).get("type"), "health_response")

    @unittest.skipUnless(ip_lan(), "El equipo no tiene una IPv4 de red local")
    def test_escucha_en_la_ip_de_la_red_local(self):
        """Como en el hotspot: el servicio escucha en la IP de la LAN y se conecta por ella."""
        ip = ip_lan()
        s = self.servicio(HOST=f"127.0.0.1,{ip}", ALLOWED_NETWORKS=f"127.0.0.1,{ip}/32")
        async def _pedir():
            r, w = await asyncio.open_connection(ip, s.port)
            try:
                w.write(trama(M("health"))); await w.drain()
                return await asyncio.wait_for(leer_mensaje(r), 5)
            finally:
                w.close()
        self.assertEqual(asyncio.run(_pedir()).get("type"), "health_response")


class TC011RestriccionDeRed(PruebaJobRunner):

    def test_direccion_no_autorizada_se_rechaza_y_se_registra(self):
        """RF-20 / RNF-13: un origen fuera de la lista recibe ACCESS_DENIED y no crea nada."""
        s = self.servicio(ALLOWED_NETWORKS=f"127.0.0.1,{REMOTO}")
        r = s.pedir(M("submit", command="echo", args=["no debo correr"]), origen=INTRUSO)
        self.assertEqual((r.get("type"), r.get("code")), ("error", "ACCESS_DENIED"), r)
        self.assertNotIn("127.0.0.1", r.get("message", ""), "El rechazo no debe revelar la configuración")
        time.sleep(0.3)
        self.assertEqual(s.db("select count(*) from jobs")[0][0], 0, "El intruso no creó ningún trabajo")
        denegados = s.eventos("ACCESS_DENIED")
        self.assertEqual(len(denegados), 1, denegados)
        self.assertIn(INTRUSO, denegados[0], "La bitácora registra la dirección rechazada")
        self.assertTrue(s.vivo())
        self.assertEqual(s.pedir(M("health"), origen=REMOTO).get("type"), "health_response",
                         "Los autorizados siguen funcionando")

    def test_rechazo_sin_enviar_nada(self):
        """Un escaneo de puertos (conectar y no mandar nada) también se rechaza y se registra."""
        s = self.servicio(ALLOWED_NETWORKS="127.0.0.1")

        async def _conectar():
            r, w = await asyncio.open_connection("127.0.0.1", s.port, local_addr=(INTRUSO, 0))
            try:
                return await asyncio.wait_for(leer_mensaje(r), 5)
            finally:
                w.close()
        self.assertEqual(asyncio.run(_conectar()).get("code"), "ACCESS_DENIED")
        self.assertEqual(len(s.eventos("ACCESS_DENIED")), 1)

    def test_redes_en_notacion_cidr(self):
        s = self.servicio(ALLOWED_NETWORKS="127.0.0.0/30")      # .0 a .3
        casos = {"127.0.0.1": "health_response", "127.0.0.2": "health_response",
                 "127.0.0.3": "health_response", "127.0.0.5": "error", "127.0.0.200": "error"}
        for origen, esperado in casos.items():
            with self.subTest(origen=origen):
                self.assertEqual(s.pedir(M("health"), origen=origen).get("type"), esperado)
        self.assertEqual(len(s.eventos("ACCESS_DENIED")), 2)

    def test_por_defecto_solo_localhost(self):
        """RNF-12: sin configurar nada escucha solo en 127.0.0.1 y solo acepta localhost."""
        s = self.servicio()
        with open("/proc/net/tcp") as f:
            escuchando = [l.split()[1] for l in f.readlines()[1:] if l.split()[3] == "0A"]
        propios = [d for d in escuchando if int(d.split(":")[1], 16) == s.port]
        self.assertEqual(propios, ["0100007F:%04X" % s.port], "Solo debe escuchar en 127.0.0.1")
        self.assertEqual(s.pedir(M("health")).get("type"), "health_response")
        self.assertEqual(s.pedir(M("health"), origen=INTRUSO).get("code"), "ACCESS_DENIED",
                         "Ni siquiera otra dirección de loopback entra si no está en la lista")

    def test_configuracion_de_red_invalida_no_arranca(self):
        """RNF-13 / RNF-21: listas mal escritas o redes públicas se rechazan al arrancar, con motivo."""
        casos = {
            "prefijo imposible": dict(ALLOWED_NETWORKS="10.0.0.0/33"),
            "texto que no es red": dict(ALLOWED_NETWORKS="127.0.0.1,mi-casa"),
            "todo internet": dict(ALLOWED_NETWORKS="0.0.0.0/0"),
            "red pública": dict(ALLOWED_NETWORKS="8.8.8.0/24"),
            "lista vacía": dict(ALLOWED_NETWORKS=" , "),
            "escuchar en IP pública": dict(HOST="8.8.8.8"),
            "host que no es IP": dict(HOST="servidor-casa"),
        }
        for nombre, config in casos.items():
            with self.subTest(caso=nombre):
                s = self.servicio(nombre.replace(" ", "_"), iniciar=False, **config)
                s.iniciar(esperar=False)
                termino, _, codigo = s.esperar_fin(10)
                self.assertTrue(termino, "Con configuración de red inválida no debe quedarse corriendo")
                self.assertNotEqual(codigo, 0)
                self.assertIn("Configuración inválida", s.salida())

    def test_escuchar_en_todas_las_interfaces_queda_advertido(self):
        """0.0.0.0 se permite (la lista de redes sigue protegiendo), pero se registra como advertencia."""
        s = self.servicio(HOST="0.0.0.0", ALLOWED_NETWORKS="127.0.0.1")
        self.assertTrue(s.eventos("BIND_ALL_INTERFACES"), s.bitacora())
        self.assertEqual(s.pedir(M("health"), origen=INTRUSO).get("code"), "ACCESS_DENIED")


if __name__ == "__main__":
    unittest.main()
