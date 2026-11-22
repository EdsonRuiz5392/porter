"""
TC-009  SIGTERM durante el arranque hace el cierre controlado ... RF-15, RNF-25
TC-015  El cliente espera más que el servicio y avisa al agotarse ... RF-17, RNF-21
(ADR-011 revisión 1 y ADR-018)

- SIGTERM al arrancar: antes, los manejadores de señales se instalaban después
  de abrir el puerto, y un SIGTERM en ese intervalo mataba el servicio con
  código -15, sin cierre controlado. La prueba ensancha el intervalo a propósito
  con 300 trabajos RUNNING que la recuperación tiene que revisar.
- Tiempo de espera del cliente: el servicio puede esperar hasta 15 s a la base
  por cada escritura (ADR-018), y un envío con --request-id hace dos accesos. Si
  el cliente se rinde antes, el usuario cree que falló, lo reenvía y el trabajo
  se ejecuta dos veces.
"""
import re
import signal
import socket
import sqlite3
import sys
import threading
import time
import unittest

from jr_helpers import REPO_ROOT, PruebaJobRunner

sys.path.insert(0, str(REPO_ROOT))


class TC009SenalDuranteElArranque(PruebaJobRunner):

    def test_sigterm_durante_el_arranque_hace_cierre_controlado(self):
        """Regresión: antes un SIGTERM justo al arrancar terminaba el servicio con -15."""
        s = self.servicio()                              # crea la base y la tabla
        s.detener()
        hace_rato = "2026-01-01T00:00:00+00:00"
        c = sqlite3.connect(s.data / "jobs.db")
        c.executemany("insert into jobs(id,command,args,status,submitted_at,started_at) values(?,?,?,?,?,?)",
                      [(f"lento-{i}", "sleep", "[]", "RUNNING", hace_rato, hace_rato) for i in range(300)])
        c.commit(); c.close()
        arranques = len(s.eventos("SERVICE_STARTED"))

        s.iniciar(esperar=False)
        empezo = False
        limite = time.time() + 20
        while time.time() < limite and s.vivo():
            if len(s.eventos("SERVICE_STARTED")) > arranques:
                empezo = True
                break
            time.sleep(0.01)
        self.assertTrue(empezo, f"El servicio no registró su arranque:\n{s.salida()}")
        s.senal(signal.SIGTERM)                          # en plena recuperación, antes de escuchar

        termino, segundos, codigo = s.esperar_fin(60)
        self.assertTrue(termino, "Debe terminar")
        self.assertEqual(codigo, 0, f"Cierre controlado, no muerte por la señal:\n{s.salida()}")
        self.assertTrue(s.eventos("SHUTDOWN_STARTED"), "Se hizo el cierre normal")
        self.assertEqual(len(s.eventos("INTERRUPTED")), 300, "La recuperación terminó antes de cerrar")


class TC015TiempoDeEsperaDelCliente(PruebaJobRunner):

    def test_el_cliente_espera_mas_que_el_servicio(self):
        """ADR-018: el cliente debe esperar al menos lo que suman dos esperas del servicio a la base."""
        from src.servicio import persistencia
        from src.cliente import cli
        espera_cliente = getattr(cli, "TIMEOUT_POR_DEFECTO", None)
        if espera_cliente is None:                       # versión anterior: el número estaba en el texto
            texto = (REPO_ROOT / "src" / "cliente" / "cli.py").read_text(encoding="utf-8")
            espera_cliente = float(re.search(r'"JOBRUNNER_TIMEOUT",\s*"(\d+)"', texto).group(1))
        espera_servicio = getattr(persistencia, "ESPERA_BASE_OCUPADA_S", 5.0)
        self.assertGreaterEqual(espera_cliente, 2 * espera_servicio,
                           f"El cliente espera {espera_cliente} s y el servicio hasta 2 × {espera_servicio} s")
        s = self.servicio(iniciar=False)
        _, ayuda = s.cli("--help")
        self.assertIn(f"JOBRUNNER_TIMEOUT o {espera_cliente:g}", ayuda, "La ayuda dice el valor real")

    def test_tiempo_agotado_avisa_que_pudo_haberse_aceptado(self):
        """Un servicio que acepta la conexión y no contesta: el CLI no debe dar a entender que falló."""
        s = self.servicio(iniciar=False)
        mudo = socket.socket()
        mudo.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mudo.bind(("127.0.0.1", s.port))
        mudo.listen(8)
        abiertas = []
        parar = threading.Event()

        def _aceptar():
            mudo.settimeout(0.2)
            while not parar.is_set():
                try:
                    abiertas.append(mudo.accept()[0])    # acepta y nunca responde
                except OSError:
                    pass
        hilo = threading.Thread(target=_aceptar, daemon=True)
        hilo.start()
        try:
            codigo, salida = s.cli("--timeout", "1", "submit", "--request-id", "folio-7", "echo", "hola")
            self.assertEqual(codigo, 1, salida)
            self.assertIn("no respondió", salida)
            self.assertIn("'list'", salida, f"Debe sugerir revisar con list:\n{salida}")
            self.assertIn("--request-id folio-7", salida, f"Debe sugerir reenviar con el mismo folio:\n{salida}")

            codigo, salida = s.cli("--timeout", "1", "submit", "echo", "hola")
            self.assertIn("'list'", salida, salida)
            self.assertNotIn("--request-id", salida, "Sin folio no hay folio que sugerir")

            codigo, salida = s.cli("--timeout", "1", "cancel", "abc-123")
            self.assertIn("status abc-123", salida, f"Debe sugerir revisar el estado:\n{salida}")
        finally:
            parar.set()
            hilo.join(2)
            for c in abiertas:
                c.close()
            mudo.close()


if __name__ == "__main__":
    unittest.main()
