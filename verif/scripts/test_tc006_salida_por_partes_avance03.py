"""
TC-006  Recuperar salidas de cualquier tamaño (por partes) ... RF-11, RNF-14
(ADR-015: recuperación de la salida por partes; corrige el defecto 2 del volumen 2)
"""
import hashlib
import unittest

from jr_helpers import M, PruebaJobRunner

GENERADOR = ("import sys\n"
             "linea = ''.join(chr(0x41 + i % 26) for i in range(99)) + 'ñ€\\n'\n"
             "for i in range(30000):\n"
             "    sys.stdout.write(f'{i:06d} ' + linea)\n")          # ~3.2 MB con UTF-8 de 2 y 3 bytes


class TC006SalidaGrande(PruebaJobRunner):

    def _trabajo_grande(self, s):
        j = s.submit("python3", "-c", GENERADOR)["job_id"]
        self.assertEqual(s.esperar_estado(j, timeout=60)["status"], "SUCCEEDED")
        archivo = s.data / "output" / f"{j}.stdout.log"
        return j, archivo.read_bytes()

    def test_salida_de_3_mb_se_recupera_completa_por_protocolo(self):
        s = self.servicio()
        j, original = self._trabajo_grande(s)
        self.assertGreater(len(original), 3_000_000)
        partes, offset, vueltas = [], 0, 0
        while True:
            r = s.pedir(M("output", job_id=j, stream="stdout", offset=offset))
            self.assertEqual(r.get("type"), "output_response", r)
            self.assertEqual(r.get("offset"), offset)
            self.assertEqual(r.get("total_size"), len(original))
            partes.append(r["content"])
            offset = r["next_offset"]
            vueltas += 1
            if r["eof"]:
                break
            self.assertLess(vueltas, 200, "Debe avanzar en cada parte")
        self.assertGreater(vueltas, 1, "Con 3 MB debe llegar en varias partes")
        reconstruido = "".join(partes).encode("utf-8")
        self.assertEqual(hashlib.sha256(reconstruido).hexdigest(), hashlib.sha256(original).hexdigest(),
                         "Las partes deben cortar en límites de carácter UTF-8, sin perder ni repetir bytes")

    def test_cli_output_descarga_todas_las_partes(self):
        s = self.servicio()
        j, original = self._trabajo_grande(s)
        codigo, texto = s.cli("output", j, timeout=60)
        self.assertEqual(codigo, 0, texto[-300:])
        self.assertEqual(texto.encode("utf-8"), original.rstrip(b"\n"))

    def test_limite_pequeno_y_parametros_invalidos(self):
        s = self.servicio()
        j = s.submit("printf", "abcdefghij")["job_id"]
        s.esperar_estado(j)
        r = s.pedir(M("output", job_id=j, offset=2, limit=3))
        self.assertEqual((r["content"], r["next_offset"], r["eof"]), ("cde", 5, False), r)
        r = s.pedir(M("output", job_id=j, offset=8, limit=100))
        self.assertEqual((r["content"], r["eof"]), ("ij", True), r)
        r = s.pedir(M("output", job_id=j, offset=50))
        self.assertEqual((r["content"], r["eof"]), ("", True), "Más allá del final: vacío y eof")
        for nombre, campos in {"offset negativo": dict(offset=-1), "offset texto": dict(offset="0"),
                               "limit cero": dict(limit=0), "limit booleano": dict(limit=True)}.items():
            with self.subTest(caso=nombre):
                r = s.pedir(M("output", job_id=j, **campos))
                self.assertEqual((r.get("type"), r.get("code")), ("error", "INVALID_REQUEST"), r)

    def test_compatibilidad_sin_offset_salida_chica(self):
        """Un cliente que no conoce offset/limit sigue recibiendo la salida completa si es chica."""
        s = self.servicio()
        j = s.submit("echo", "hola")["job_id"]
        s.esperar_estado(j)
        r = s.output(j)
        self.assertEqual((r["content"], r["eof"]), ("hola\n", True), r)


if __name__ == "__main__":
    unittest.main()
