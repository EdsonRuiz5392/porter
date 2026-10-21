#!/usr/bin/env python3
"""
Ejecuta TODAS las pruebas de verificación con un solo comando (RNF-20) y guarda
la evidencia de la ejecución en verif/results/<run-id>/, como piden los
estándares del repositorio: versión, entorno, configuración, comando,
resultados, bitácoras y resumen PASS/FAIL.

Uso (desde la raíz del repositorio, la carpeta que contiene src/ y verif/):
    python3 verif/scripts/run_verificacion.py
    python3 verif/scripts/run_verificacion.py --filtro tc009      # solo un grupo
    python3 verif/scripts/run_verificacion.py --run-id mi-corrida

Solo usa la biblioteca estándar. Las pruebas también se pueden correr con:
    python3 -m unittest discover -s verif/scripts -v
    python3 -m pytest verif/scripts -v            (si pytest está instalado)
pero esas dos formas NO guardan evidencia en verif/results/.

Los resultados no deben editarse a mano para ocultar fallas.
"""

import argparse
import getpass
import hashlib
import io
import json
import os
import platform
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
import traceback
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parents[1]
RESULTS = REPO_ROOT / "verif" / "results"


# --------------------------------------------------------------------------- datos de la corrida

def version_del_codigo() -> tuple[str, str]:
    """(texto descriptivo, etiqueta corta) con el commit o, si no hay git, un hash del código."""
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                                text=True, check=True).stdout.strip()
        sucio = subprocess.run(["git", "status", "--porcelain", "--", "src"], cwd=REPO_ROOT,
                               capture_output=True, text=True).stdout.strip()
        rama = subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=REPO_ROOT,
                              capture_output=True, text=True).stdout.strip()
        texto = f"Commit: {commit}\nRama: {rama}\nCambios sin commit en src/: {'SÍ' if sucio else 'no'}\n"
        if sucio:
            texto += sucio + "\n"
        return texto, commit[:8] + ("-sucio" if sucio else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        h = hashlib.sha256()
        archivos = sorted(p for p in (REPO_ROOT / "src").rglob("*")
                          if p.is_file() and "__pycache__" not in p.parts)
        for p in archivos:
            h.update(str(p.relative_to(REPO_ROOT)).encode())
            h.update(p.read_bytes())
        texto = ("Sin repositorio git: se identifica el código con el SHA-256 de todos los archivos de src/.\n"
                 f"SHA-256 de src/: {h.hexdigest()}\nArchivos: {len(archivos)}\n")
        return texto, "sin-git-" + h.hexdigest()[:8]


def entorno() -> str:
    distro = "desconocida"
    try:
        for linea in Path("/etc/os-release").read_text().splitlines():
            if linea.startswith("PRETTY_NAME="):
                distro = linea.split("=", 1)[1].strip('"')
    except OSError:
        pass
    usuario = getpass.getuser()
    lineas = [
        f"Fecha (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"Distribución: {distro}",
        f"Kernel: {platform.system()} {platform.release()} ({platform.machine()})",
        f"Python: {sys.version.split()[0]} ({sys.executable})",
        f"SQLite: {sqlite3.sqlite_version}",
        f"CPUs: {os.cpu_count()}",
        f"Usuario: {usuario} (uid {os.getuid()})",
    ]
    if os.getuid() == 0:
        lineas.append("AVISO: esta corrida se hizo como root; para evidenciar RNF-03 hay que repetirla "
                      "con un usuario normal.")
    return "\n".join(lineas) + "\n"


def casos_documentados() -> dict[str, tuple[str, str]]:
    """Lee el encabezado de cada archivo de prueba: 'TC-0XX  Descripción ..... RF-..'."""
    casos = {}
    patron = re.compile(r"^(TC-\d{3}|RNF-\d{2})\s+(.+?)\s*\.{2,}\s*(.+)$")
    for archivo in sorted(SCRIPTS.glob("test_*.py")):
        texto = archivo.read_text(encoding="utf-8")
        doc = texto.split('"""')[1] if texto.startswith('"""') else ""
        for linea in doc.splitlines():
            m = patron.match(linea.strip())
            if m:
                casos[m.group(1)] = (m.group(2), m.group(3))
    return casos


# --------------------------------------------------------------------------- registro de resultados

class Tee(io.TextIOBase):
    def __init__(self, *destinos):
        self.destinos = destinos

    def write(self, s):
        for d in self.destinos:
            if not d.closed:
                d.write(s)
                d.flush()
        return len(s)

    def flush(self):
        for d in self.destinos:
            if not d.closed:
                d.flush()


class Resultado(unittest.TextTestResult):
    """Además de imprimir, guarda resultado, duración y detalle de cada prueba."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.registros: dict[str, dict] = {}
        self._inicio: dict[str, float] = {}

    def _reg(self, test, estado=None, detalle=None):
        tid = test.id()
        r = self.registros.setdefault(tid, {"id": tid, "resultado": "PASS", "detalle": "", "segundos": 0.0})
        if estado and not (r["resultado"] in ("FAIL", "ERROR") and estado == "PASS"):
            r["resultado"] = estado
        if detalle:
            r["detalle"] = (r["detalle"] + " | " if r["detalle"] else "") + detalle
        return r

    def _resumir(self, err, test):
        """Primera línea del error (p. ej. 'AssertionError: ...') más el mensaje propio de la prueba."""
        lineas = self._exc_info_to_string(err, test).strip().splitlines()
        if not lineas:
            return ""
        principal = next((l for l in lineas if re.match(r"^[\w.]*(Error|Exception)\b", l)), lineas[-1])
        extra = lineas[-1].strip()
        if extra.startswith(":") and extra not in principal:
            principal += " " + extra
        return principal[:300]

    def startTest(self, test):
        self._inicio[test.id()] = time.time()
        self._reg(test)
        super().startTest(test)

    def stopTest(self, test):
        self._reg(test)["segundos"] = round(time.time() - self._inicio.get(test.id(), time.time()), 2)
        super().stopTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._reg(test, "PASS")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._reg(test, "FAIL", self._resumir(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._reg(test, "ERROR", self._resumir(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._reg(test, "SKIP", reason)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            estado = "FAIL" if issubclass(err[0], test.failureException) else "ERROR"
            self._reg(test, estado, f"{subtest._subDescription()}: {self._resumir(err, test)}")


# --------------------------------------------------------------------------- principal

def main() -> int:
    ap = argparse.ArgumentParser(description="Ejecuta la verificación de JobRunner y guarda la evidencia.")
    ap.add_argument("--filtro", default="", help="parte del nombre del archivo de prueba, ej. tc009")
    ap.add_argument("--run-id", default="", help="nombre de la carpeta de resultados")
    args = ap.parse_args()

    if not (REPO_ROOT / "src" / "servicio" / "main.py").exists():
        print(f"[-] No se encontró src/ en {REPO_ROOT}. Ejecuta desde la raíz del repositorio.")
        return 2

    version_texto, version_corta = version_del_codigo()
    run_id = args.run_id or f"{datetime.now():%Y-%m-%d_%H%M%S}_{version_corta}"
    salida = RESULTS / run_id
    salida.mkdir(parents=True, exist_ok=False)
    os.environ["JR_EVIDENCIA_DIR"] = str(salida)

    comando = " ".join([Path(sys.executable).name, *[a if " " not in a else repr(a) for a in sys.argv]])
    (salida / "version.txt").write_text(version_texto)
    (salida / "entorno.txt").write_text(entorno())
    (salida / "comando.txt").write_text(f"{comando}\n(ejecutado en {REPO_ROOT})\n")
    ejemplo = REPO_ROOT / "src" / ".env.example"
    (salida / "configuracion.txt").write_text(
        "Cada prueba arranca su propio servicio con un puerto libre, una carpeta de datos propia y la\n"
        "configuración que indica la prueba (ver servicios/<prueba>/). Valores por defecto del proyecto:\n\n"
        + (ejemplo.read_text() if ejemplo.exists() else "(sin src/.env.example)\n"))

    sys.path.insert(0, str(SCRIPTS))
    patron = f"test_*{args.filtro}*.py" if args.filtro else "test_*.py"
    suite = unittest.defaultTestLoader.discover(str(SCRIPTS), pattern=patron, top_level_dir=str(SCRIPTS))

    log = open(salida / "salida_pruebas.txt", "w", encoding="utf-8")
    tee = Tee(sys.__stdout__, log)
    stdout_original, sys.stdout = sys.stdout, tee
    print(f"Run ID: {run_id}\nEvidencia en: {salida}\n")
    t0 = time.time()
    try:
        runner = unittest.TextTestRunner(stream=tee, verbosity=2, resultclass=Resultado)
        resultado = runner.run(suite)
    except Exception:
        traceback.print_exc()
        return 2
    finally:
        sys.stdout = stdout_original
        log.close()
    duracion = round(time.time() - t0, 1)

    registros = sorted(resultado.registros.values(), key=lambda r: r["id"])
    for r in registros:
        m = re.search(r"\.TC(\d{3})", r["id"])
        r["caso"] = f"TC-{m.group(1)}" if m else "—"
    totales = {k: sum(r["resultado"] == k for r in registros) for k in ("PASS", "FAIL", "ERROR", "SKIP")}
    global_ok = totales["FAIL"] == 0 and totales["ERROR"] == 0 and registros

    (salida / "resultados.json").write_text(json.dumps(
        {"run_id": run_id, "duracion_s": duracion, "totales": totales,
         "resultado_global": "PASS" if global_ok else "FAIL", "pruebas": registros},
        indent=2, ensure_ascii=False))

    # ---- resumen legible
    casos = casos_documentados()
    por_caso: dict[str, list] = {}
    for r in registros:
        por_caso.setdefault(r["caso"], []).append(r)
    md = [f"# Resultados de verificación — {run_id}", "",
          f"**Resultado global: {'PASS' if global_ok else 'FAIL'}** · "
          f"{totales['PASS']} PASS · {totales['FAIL']} FAIL · {totales['ERROR']} ERROR · "
          f"{totales['SKIP']} SKIP · {duracion} s", "",
          "## Versión", "```", version_texto.strip(), "```", "",
          "## Entorno", "```", entorno().strip(), "```", "",
          "## Comando", "```", comando, "```", "",
          "## Por caso de prueba", "",
          "| Caso | Descripción | Requisitos | Pruebas | Resultado |", "|---|---|---|---|---|"]
    for caso in sorted(por_caso):
        lista = por_caso[caso]
        desc, reqs = casos.get(caso, ("", ""))
        ok = all(r["resultado"] == "PASS" for r in lista)
        md.append(f"| {caso} | {desc} | {reqs} | {len(lista)} | {'PASS' if ok else 'FAIL'} |")
    md += ["", "## Detalle de cada prueba", "",
           "| Caso | Prueba | Resultado | Segundos | Detalle |", "|---|---|---|---|---|"]
    for r in registros:
        nombre = r["id"].split(".", 1)[1] if "." in r["id"] else r["id"]
        detalle = r["detalle"].replace("|", "/") if r["detalle"] else ""
        md.append(f"| {r['caso']} | `{nombre}` | {r['resultado']} | {r['segundos']} | {detalle} |")
    md += ["", "## Archivos de esta carpeta", "",
           "- `salida_pruebas.txt`: salida completa de la ejecución.",
           "- `resultados.json`: los mismos resultados en formato máquina.",
           "- `servicios.tar.gz`: por cada servicio que levantó cada prueba, su `data/jobrunner.log` "
           "(bitácora), `data/jobs.db` (base), `data/output/` (salidas) y `servicio_salida.txt` "
           "(lo que imprimió el servicio). Se abre con `tar xzf servicios.tar.gz`.",
           "- `version.txt`, `entorno.txt`, `configuracion.txt`, `comando.txt`."]
    (salida / "resumen.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    # Las pruebas de carga generan miles de archivos pequeños; se empaquetan en uno
    # solo para no ensuciar el repositorio (estándares: sin resultados voluminosos).
    servicios = salida / "servicios"
    if servicios.exists():
        with tarfile.open(salida / "servicios.tar.gz", "w:gz") as tar:
            tar.add(servicios, arcname="servicios")
        shutil.rmtree(servicios)

    print(f"\nResultado global: {'PASS' if global_ok else 'FAIL'}  {totales}  ({duracion} s)")
    print(f"Evidencia: {salida}")
    return 0 if global_ok else 1


if __name__ == "__main__":
    sys.exit(main())
