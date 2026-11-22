#!/usr/bin/env python3
"""
Genera con UN solo comando toda la evidencia del avance 3, para que nadie tenga
que lanzar corridas a mano:

    verif/results/antes_avance02/              código del avance 2 con las pruebas actuales
    verif/results/despues_avance03/            código actual (avance 3 corregido)
    verif/results/despues_avance03_corrida2/   segunda corrida completa del código actual
    verif/results/repeticiones_avance03/       las mismas pruebas muchas veces, con y sin carga
    verif/results/RESUMEN_avance03.md          tabla con todo lo anterior

Uso (desde la carpeta que contiene verif/ y, para el "después", src/):
    python3 verif/scripts/run_evidencia.py --solo-antes --antes /ruta/al/src_del_avance02
    python3 verif/scripts/run_evidencia.py --solo-despues          # otro día, desde el repositorio
    python3 verif/scripts/run_evidencia.py --antes /ruta/...       # las dos partes de una vez

--solo-antes   antes_avance02/ y las repeticiones del avance 2 con carga (~10-15 min).
--solo-despues despues_avance03/ (x2), las repeticiones del código actual y RESUMEN_avance03.md
               (~30-45 min). El resumen incluye el "antes" si su carpeta está en verif/results/.
--antes acepta la carpeta src/ del avance 2 o la carpeta que la contiene.
--prueba-rapida hace cada corrida una sola vez y lo guarda en verif/results/prueba_rapida/,
sin tocar las carpetas oficiales: sirve para comprobar que todo está bien puesto.

Por qué hay repeticiones: los Issues #58 y #59 eran intermitentes (a veces salían y a
veces no), así que una corrida que pasa no demuestra nada; diez seguidas sí. "Con carga"
satura la CPU a propósito para imitar una máquina lenta, que es donde aparecían.

Cada corrida es una llamada normal a run_verificacion.py, con su propia carpeta de
evidencia; este script solo las ordena y las resume. Los resultados no se editan.
Solo usa la biblioteca estándar.
"""

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from datetime import datetime
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS.parents[1]
RESULTS = REPO_ROOT / "verif" / "results"
RUNNER = "verif/scripts/run_verificacion.py"

# (filtro, veces). "" = la suite completa.
REPETICIONES_SIN_CARGA = [("tc022", 10), ("tc004", 3), ("tc008", 3), ("regresion_issues", 3),
                          ("tc009", 5), ("arranque_y_cliente", 3)]
REPETICIONES_CON_CARGA = [("tc022", 8), ("tc004", 3), ("tc008", 3)]
REPETICIONES_CON_CARGA_ANTES = [("tc022", 8)]       # para comparar: ahí nacieron #58 y #59
PRUEBA_A_PROPOSITO = "test_si_la_base_no_responde"   # provoca "database is locked" a propósito


# --------------------------------------------------------------------------- comprobaciones

def carpeta_src(ruta: str) -> Path:
    p = Path(ruta).expanduser().resolve()
    for candidato in (p, p / "src"):
        if (candidato / "servicio" / "main.py").exists():
            return candidato
    sys.exit(f"[-] En {p} no hay un src/ de JobRunner (falta servicio/main.py).")


def sistema_de_archivos(ruta: Path) -> str:
    """Tipo de sistema de archivos donde está `ruta` (ext4, 9p, drvfs, ...)."""
    mejor, tipo = "", "desconocido"
    try:
        for linea in Path("/proc/mounts").read_text().splitlines():
            partes = linea.split()
            punto = partes[1].replace("\\040", " ")
            if str(ruta).startswith(punto) and len(punto) > len(mejor):
                mejor, tipo = punto, partes[2]
    except OSError:
        pass
    return tipo


def comprobar_entorno(permitir_mnt: bool) -> None:
    es_wsl = "microsoft" in Path("/proc/version").read_text().lower() if Path("/proc/version").exists() else False
    tipo = sistema_de_archivos(REPO_ROOT)
    en_windows = str(REPO_ROOT).startswith("/mnt/") or tipo in ("9p", "drvfs", "v9fs")
    if es_wsl and en_windows and not permitir_mnt:
        sys.exit(
            f"[-] La carpeta {REPO_ROOT} está en el disco de Windows (sistema de archivos {tipo}).\n"
            "    Ahí SQLite y los procesos son lentos y poco confiables, y las pruebas fallan por eso.\n"
            "    Copia la carpeta al disco de Linux de WSL y corre desde ahí, por ejemplo:\n"
            "        mkdir -p ~/jr-evidencia && cp -r . ~/jr-evidencia/ && cd ~/jr-evidencia\n"
            "    (Para correr aquí de todos modos: --permitir-mnt.)")
    if os.getuid() == 0:
        print("[!] Estás como root. La evidencia sirve más con un usuario normal (RNF-03).")


def corridas_planeadas(antes: Path | None, rapida: bool, hacer_antes: bool,
                       hacer_despues: bool) -> list[tuple[str, Path, str, bool]]:
    """(run_id, src a probar, filtro, con_carga)."""
    base = "prueba_rapida/" if rapida else ""
    veces = (lambda n: 1) if rapida else (lambda n: n)
    rep = f"{base}repeticiones_avance03"
    actual = REPO_ROOT / "src"
    plan = []
    if hacer_antes:
        plan.append((f"{base}antes_avance02", antes, "", False))
        for filtro, n in REPETICIONES_CON_CARGA_ANTES:
            plan += [(f"{rep}/con_carga/avance02-{filtro}-{k:02d}", antes, filtro, True)
                     for k in range(1, veces(n) + 1)]
    if hacer_despues:
        plan.append((f"{base}despues_avance03", actual, "", False))
        if not rapida:
            plan.append((f"{base}despues_avance03_corrida2", actual, "", False))
        for filtro, n in REPETICIONES_SIN_CARGA:
            plan += [(f"{rep}/sin_carga/corregido-{filtro}-{k:02d}", actual, filtro, False)
                     for k in range(1, veces(n) + 1)]
        for filtro, n in REPETICIONES_CON_CARGA:
            plan += [(f"{rep}/con_carga/corregido-{filtro}-{k:02d}", actual, filtro, True)
                     for k in range(1, veces(n) + 1)]
    return plan


# --------------------------------------------------------------------------- ejecución

class Carga:
    """Satura la CPU con procesos que solo dan vueltas, para imitar una máquina lenta."""

    def __init__(self):
        self.procesos = []

    def encender(self):
        if self.procesos:
            return
        n = max(2, 3 * (os.cpu_count() or 1))
        self.procesos = [subprocess.Popen([sys.executable, "-c", "while True: pass"],
                                          stdin=subprocess.DEVNULL, start_new_session=True)
                         for _ in range(n)]

    def apagar(self):
        for p in self.procesos:
            p.kill()
        for p in self.procesos:
            p.wait()
        self.procesos = []


def preparar_antes(src_antes: Path, temporal: Path) -> Path:
    """Una carpeta aparte con el src del avance 2 y los scripts actuales."""
    ignorar = shutil.ignore_patterns("__pycache__")
    shutil.copytree(src_antes, temporal / "src", ignore=ignorar)
    shutil.copytree(SCRIPTS, temporal / "verif" / "scripts", ignore=ignorar)
    return temporal


def correr(raiz: Path, run_id: str, filtro: str) -> tuple[str, float]:
    comando = [sys.executable, RUNNER, "--run-id", run_id] + (["--filtro", filtro] if filtro else [])
    t0 = time.time()
    r = subprocess.run(comando, cwd=raiz, capture_output=True, text=True, timeout=1800)
    linea = next((l for l in r.stdout.splitlines() if l.startswith("Resultado global")),
                 f"SIN RESULTADO (código {r.returncode}): {r.stderr.strip()[-300:]}")
    return linea, time.time() - t0


# --------------------------------------------------------------------------- resumen

def leer(run: Path) -> dict:
    try:
        return json.loads((run / "resultados.json").read_text())
    except (OSError, ValueError):
        return {"resultado_global": "SIN RESULTADO", "totales": {}, "pruebas": []}


def lineas_bloqueo(run: Path) -> int:
    """'database is locked' en las bitácoras, sin contar la prueba que lo provoca a propósito."""
    n = 0
    try:
        with tarfile.open(run / "servicios.tar.gz") as tar:
            for m in tar.getmembers():
                if m.name.endswith("jobrunner.log") and PRUEBA_A_PROPOSITO not in m.name:
                    n += tar.extractfile(m).read().count(b"database is locked")
    except (OSError, tarfile.TarError):
        pass
    return n


def fecha_de_corrida(run: Path) -> str:
    """Fecha en que se hizo la corrida, según su entorno.txt (no cambia al copiar o clonar)."""
    linea = primera_linea(run / "entorno.txt", "Fecha")
    if ":" in linea:
        return linea.split(":", 1)[1].strip()[:10]
    try:
        with tarfile.open(run / "servicios.tar.gz") as tar:
            primero = next((m for m in tar.getmembers() if m.isfile()), None)
            if primero:
                return time.strftime("%Y-%m-%d", time.localtime(primero.mtime))
    except (OSError, tarfile.TarError):
        pass
    return "?"


def primera_linea(archivo: Path, empieza: str) -> str:
    try:
        return next((l for l in archivo.read_text().splitlines() if l.startswith(empieza)), "")
    except OSError:
        return ""


def escribir_resumen(base: str) -> Path:
    """Resume lo que haya en disco: así incluye el 'antes' aunque se haya corrido otro día."""
    raiz = RESULTS / base
    principales = [raiz / n for n in ("antes_avance02", "despues_avance03", "despues_avance03_corrida2")
                   if (raiz / n).exists()]
    grupos: dict[tuple, list] = {}
    for carga in ("sin_carga", "con_carga"):
        carpeta = raiz / "repeticiones_avance03" / carga
        for run in sorted(carpeta.iterdir()) if carpeta.exists() else []:
            codigo, _, resto = run.name.partition("-")
            filtro = resto.rsplit("-", 1)[0]
            nombre = "avance 2" if codigo == "avance02" else "avance 3 corregido"
            grupos.setdefault((filtro, nombre, carga == "con_carga"), []).append(run)

    md = ["# Resumen de la evidencia del avance 3", "",
          f"Generado por `run_evidencia.py` el {datetime.now():%Y-%m-%d %H:%M} por el usuario "
          f"`{getpass.getuser()}`. La fecha y el entorno de cada corrida están en su `resumen.md` y "
          "su `entorno.txt`.", ""]
    md += ["## Corridas completas", "", "| Carpeta | Código | Fecha | Resultado |", "|---|---|---|---|"]
    for d in principales:
        version = (primera_linea(d / "version.txt", "Commit:") or
                   primera_linea(d / "version.txt", "SHA-256 de src/:")).split(":", 1)[-1].strip()[:12]
        fecha = fecha_de_corrida(d)
        r = leer(d)
        tot = r.get("totales", {})
        md.append(f"| `{d.name}` | `{version}…` | {fecha} | **{r.get('resultado_global')}**: "
                  f"{tot.get('PASS', 0)} PASS, {tot.get('FAIL', 0)} FAIL, {tot.get('ERROR', 0)} ERROR, "
                  f"{tot.get('SKIP', 0)} SKIP |")
    md += ["", "Con el código del avance 2 es normal que fallen las pruebas del avance 3: son lo que "
           "esa versión no tenía. Con el código actual deben pasar todas.", ""]

    rep = ["## Repeticiones", "",
           "| Grupo (`--filtro`) | Código | Carga | Corridas PASS | `database is locked`* |",
           "|---|---|---|---|---|"]
    detalle = []
    for (filtro, codigo, carga), runs in sorted(grupos.items(), key=lambda g: (g[0][1] == "avance 2", g[0][2])):
        datos = [leer(r) for r in runs]
        ok = sum(d.get("resultado_global") == "PASS" for d in datos)
        bloqueo = sum(lineas_bloqueo(r) for r in runs)
        rep.append(f"| `{filtro}` | {codigo} | {'**con carga**' if carga else 'sin carga'} | "
                   f"{ok} de {len(runs)} | {bloqueo} |")
        fallas: dict[str, dict] = {}
        for d in datos:
            for p in d.get("pruebas", []):
                if p["resultado"] != "PASS":
                    c = fallas.setdefault(p["id"].split(".", 1)[-1], {})
                    c[p["resultado"]] = c.get(p["resultado"], 0) + 1
        if fallas:
            detalle += [f"**`{filtro}`, {codigo}, {'con' if carga else 'sin'} carga** (pruebas que no "
                        f"pasaron, en {len(runs)} corrida{'s' if len(runs) != 1 else ''}):", ""]
            detalle += [f"- `{n}`: " + ", ".join(f"{v} {k}" for k, v in c.items())
                        for n, c in sorted(fallas.items())]
            detalle.append("")
    rep += ["", f"\\* Sin contar `{PRUEBA_A_PROPOSITO}…`, que provoca el error a propósito y debe "
            "registrar una sola línea `PERSIST_ERROR … database is locked`.", "",
            "Con el avance 2 y `--filtro tc022` nunca da PASS, porque ese filtro incluye las "
            "regresiones de #58 y #59, que fallan siempre con ese código. Lo que importa ahí son las "
            "pruebas propias de TC-022 (`test_bajar_max_queue_con_pendientes` y "
            "`test_base_integra_tras_kill9_durante_escrituras`), que fallan solo algunas veces: "
            "ese es el Issue #59.", ""]
    if detalle:
        rep += ["### Pruebas que no pasaron", ""] + detalle
    md += rep

    resumen = raiz / "RESUMEN_avance03.md"
    resumen.parent.mkdir(parents=True, exist_ok=True)
    resumen.write_text("\n".join(md) + "\n", encoding="utf-8")
    carpeta_rep = raiz / "repeticiones_avance03"
    if carpeta_rep.exists():
        (carpeta_rep / "README.md").write_text(
            "# Repeticiones del avance 3\n\nCada subcarpeta es una corrida de `run_verificacion.py "
            "--filtro <grupo>`. `sin_carga/` es la máquina normal; `con_carga/` satura la CPU con "
            "3 procesos por CPU para imitar una máquina lenta. `corregido-*` es el código actual y "
            "`avance02-*` el del avance 2, para comparar.\n\n" + "\n".join(rep) + "\n", encoding="utf-8")
    return resumen


# --------------------------------------------------------------------------- principal

def main() -> int:
    ap = argparse.ArgumentParser(description="Genera la evidencia del avance 3.")
    ap.add_argument("--antes", help="src/ del avance 2 (o la carpeta que lo contiene)")
    parte = ap.add_mutually_exclusive_group()
    parte.add_argument("--solo-antes", action="store_true",
                       help="solo el avance 2: antes_avance02 y sus repeticiones con carga")
    parte.add_argument("--solo-despues", action="store_true",
                       help="solo el código actual: despues_avance03 (x2), repeticiones y RESUMEN")
    ap.add_argument("--prueba-rapida", action="store_true", help="una vez cada cosa, en results/prueba_rapida/")
    ap.add_argument("--permitir-mnt", action="store_true", help="correr aunque la carpeta esté en /mnt (WSL)")
    args = ap.parse_args()

    hacer_antes, hacer_despues = not args.solo_despues, not args.solo_antes
    if not (REPO_ROOT / "src" / "servicio" / "main.py").exists() and hacer_despues:
        sys.exit(f"[-] No se encontró src/ en {REPO_ROOT}. Pon src/ junto a verif/ y corre desde ahí.")
    antes = None
    if hacer_antes:
        if not args.antes:
            sys.exit("[-] Falta --antes con la carpeta del src/ del avance 2.")
        antes = carpeta_src(args.antes)
        if (REPO_ROOT / "src").exists() and antes == (REPO_ROOT / "src").resolve() and hacer_despues:
            sys.exit("[-] --antes apunta al mismo src/ que se va a probar como 'después'.")
    comprobar_entorno(args.permitir_mnt)

    base = "prueba_rapida/" if args.prueba_rapida else ""
    plan = corridas_planeadas(antes, args.prueba_rapida, hacer_antes, hacer_despues)
    existentes = [RESULTS / p[0] for p in plan if (RESULTS / p[0]).exists()]
    if hacer_despues and (RESULTS / base / "RESUMEN_avance03.md").exists():
        existentes.append(RESULTS / base / "RESUMEN_avance03.md")
    if existentes:
        sys.exit("[-] Ya existen estas carpetas o archivos y la evidencia no se sobrescribe:\n    "
                 + "\n    ".join(str(e) for e in existentes) + "\n    Muévelos o bórralos y vuelve a correr.")

    que = "antes y después" if hacer_antes and hacer_despues else ("solo antes" if hacer_antes else "solo después")
    minutos = {"antes y después": "40 a 60", "solo antes": "10 a 15", "solo después": "30 a 45"}[que]
    print(f"JobRunner: evidencia del avance 3, {que}{' (prueba rápida)' if args.prueba_rapida else ''}")
    if hacer_despues:
        print(f"  después (código actual): {REPO_ROOT / 'src'}")
    if hacer_antes:
        print(f"  antes (avance 2):        {antes}")
    print(f"  resultados en:           {RESULTS / base if base else RESULTS}")
    print(f"  {len(plan)} corridas; tarda {'unos 10' if args.prueba_rapida else minutos} min. "
          "No uses la computadora para otra cosa pesada mientras tanto.\n")

    t0 = time.time()
    carga = Carga()
    temporal = Path(tempfile.mkdtemp(prefix="jr-antes-"))
    try:
        raiz_antes = preparar_antes(antes, temporal) if antes else None
        for i, (run_id, src, filtro, con_carga) in enumerate(plan, 1):
            carga.encender() if con_carga else carga.apagar()
            raiz = raiz_antes if src == antes else REPO_ROOT
            linea, seg = correr(raiz, run_id, filtro)
            if raiz is raiz_antes:                     # su evidencia se trae a este results/
                destino = RESULTS / run_id
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(raiz_antes / "verif" / "results" / run_id), destino)
            resultado = re.sub(r"\s*\([\d.]+ s\)$", "", linea.removeprefix("Resultado global: "))
            print(f"[{i:2d}/{len(plan)}] {run_id.removeprefix(base):60s} {resultado}  ({seg:.0f} s)", flush=True)
    finally:
        carga.apagar()
        shutil.rmtree(temporal, ignore_errors=True)

    print(f"\nListo en {(time.time() - t0) / 60:.0f} min. Evidencia en {RESULTS / base if base else RESULTS}")
    if hacer_despues:
        print(f"Resumen: {escribir_resumen(base)}")
        print("Revisa ese archivo y el resumen.md de cada carpeta antes de subirlos.")
    else:
        print("Sube antes_avance02/ y repeticiones_avance03/ al repositorio. Cuando corras --solo-despues "
              "desde el repositorio, el resumen las va a incluir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
