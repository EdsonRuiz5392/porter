#!/usr/bin/env bash
# Script de verificacion de Porter (RNF-20: pruebas con un solo comando).
#
# Uso, desde la raiz del repositorio:
#     bash verif/scripts/run_verification.sh
#
# Ejecuta todas las pruebas automatizadas de verif/scripts/ con pytest y
# guarda la evidencia de la corrida en verif/results/<run-id>/ con commit,
# entorno, comando, salida completa y resumen PASS/FAIL (doc 04, "Evidencia
# y resultados"). El run-id es AAAAMMDD-HHMM-<commit corto>.
#
# Codigo de salida: 0 si todas las pruebas pasaron, 1 si alguna fallo,
# 2 si no pudo ejecutarse (falta pytest o no es un repositorio).
#
# Responsable: Edson (verificacion). No modifica ningun archivo de src/.
set -u

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$RAIZ" || exit 2

# Usa el entorno virtual del proyecto si existe; si no, el python del sistema.
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi

if ! $PY -m pytest --version >/dev/null 2>&1; then
    echo "pytest no esta instalado. Ejecuta:"
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r src/requirements.txt"
    exit 2
fi

COMMIT_CORTO=$(git rev-parse --short HEAD 2>/dev/null || echo sin-git)
RUN="$(date +%Y%m%d-%H%M)-$COMMIT_CORTO"
DIR="verif/results/$RUN"
mkdir -p "$DIR"
CMD="$PY -m pytest verif/scripts -v"

{
    echo "run-id: $RUN"
    echo "commit: $(git rev-parse HEAD 2>/dev/null)"
    echo "rama: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    if [ -z "$(git status --porcelain --untracked-files=no 2>/dev/null)" ]; then
        echo "arbol de trabajo: sin cambios respecto al commit"
    else
        echo "arbol de trabajo: CON cambios no confirmados (la corrida no es reproducible desde el commit)"
    fi
    echo "fecha: $(date -Iseconds)"
    echo "distribucion: $(lsb_release -ds 2>/dev/null || head -1 /etc/os-release)"
    echo "kernel: $(uname -r) ($(uname -m))"
    echo "python: $($PY --version 2>&1)"
    echo "pytest: $($PY -m pytest --version 2>&1)"
    echo "usuario: $(id -un) (uid $(id -u))"
    echo "comando: $CMD"
    echo "configuracion JOBRUNNER_*: $(env | grep '^JOBRUNNER_' | tr '\n' ' ')"
} > "$DIR/entorno.txt"

$CMD 2>&1 | tee "$DIR/resultados.txt"
CODIGO=${PIPESTATUS[0]}

if [ "$CODIGO" -eq 0 ]; then ESTADO=PASS; else ESTADO=FAIL; fi
{
    echo "estado: $ESTADO"
    echo "codigo de salida de pytest: $CODIGO"
    echo "resumen: $(tail -1 "$DIR/resultados.txt")"
} > "$DIR/resumen.txt"

echo
echo "== $ESTADO ==  evidencia guardada en $DIR"
cat "$DIR/resumen.txt"

[ "$CODIGO" -eq 0 ] && exit 0 || exit 1
