# verif/scripts — Pruebas automatizadas de JobRunner

Pruebas de sistema que arrancan el **servicio real** y verifican los casos TC del plan de verificación. Cumplen RNF-20 ("ejecutables con un único comando documentado") y guardan la evidencia como piden los estándares del repositorio.

## Cómo ejecutarlas

Desde la **raíz del repositorio** (la carpeta que contiene `src/` y `verif/`):

```bash
python3 verif/scripts/run_verificacion.py
```

Eso es todo: no hay que instalar nada, porque las pruebas solo usan la biblioteca estándar de Python (`unittest`). Tarda alrededor de 1 minuto. Al terminar:

- imprime `Resultado global: PASS` o `FAIL` y sale con código 0 (todo PASS) o 1 (alguna falla);
- crea `verif/results/<fecha>_<versión>/` con la evidencia (ver abajo).

Opciones:

```bash
python3 verif/scripts/run_verificacion.py --filtro tc009         # solo los archivos test_*tc009*
python3 verif/scripts/run_verificacion.py --run-id demo-rt2      # nombre propio para la carpeta
```

Otras formas de correrlas, útiles mientras se programa, que **no** guardan evidencia:

```bash
python3 -m unittest discover -s verif/scripts -v
python3 -m pytest verif/scripts -v        # pytest también ejecuta pruebas unittest
```

**Requisitos:** Linux, Python 3.10 o superior y los comandos `bash`, `sleep`, `echo`, `cat` y `printf`. Las pruebas no necesitan root; ejecútenlas con un usuario normal, porque así también sirven de evidencia de RNF-03.

## Qué contiene cada archivo

| Archivo | Casos | Requisitos |
|---|---|---|
| `test_tc001_envio_y_validacion.py` | TC-001, TC-015 | RF-01, RF-02, RF-17, RNF-14, RNF-21 |
| `test_tc002_cola_y_concurrencia.py` | TC-002 | RF-03, RF-05, RNF-04, RNF-07 |
| `test_tc003_tc006_estados_tiempos_salidas.py` | TC-003, TC-006 | RF-06, RF-07, RF-11 |
| `test_tc004_tc013_consultas_y_salud.py` | TC-004, TC-013 | RF-08, RF-09, RF-16, RF-24, RNF-05, RNF-06 |
| `test_tc005_tc017_tc021_cancelacion.py` | TC-005, TC-017, TC-021 | RF-10, RF-26, RF-30, RNF-27 |
| `test_tc007_tc022_recuperacion.py` | TC-007, TC-022 | RF-12, RF-13, RNF-10, RNF-11, RNF-28, RNF-30, RNF-31 |
| `test_tc008_tc020_tc024_fallas_y_recursos.py` | TC-008, TC-020, TC-024 | RF-29, RNF-08, RNF-09, RNF-30, RNF-33 |
| `test_tc009_cierre_controlado.py` | TC-009 | RF-15, RNF-25, RNF-30 |
| `test_tc012_tc019_tc023_protocolo.py` | TC-012, TC-019, TC-023 | RF-21, RF-22, RF-28, RNF-14, RNF-24, RNF-32 |
| `test_tc016_tc018_saturacion_y_duplicados.py` | TC-016, TC-018 | RF-25, RF-27, RNF-29 |
| `jr_helpers.py` | — | Utilidades compartidas: arrancar el servicio, hablar el protocolo, limpiar |
| `run_verificacion.py` | — | Ejecuta todo y genera la evidencia |

**No cubiertos aquí** (requieren otro entorno o son inspección o documentación): TC-010 y TC-011 (operación remota y restricción de red, Hito 3), TC-014 (construcción desde un clon limpio) y TC-015 en su parte de usabilidad documental.

## Cómo funcionan (para la defensa)

- **Servicio real y aislado.** Cada prueba arranca `python3 -m src.servicio.main` con un puerto libre y su propia carpeta de datos, así que no interfiere con un servicio que tengan corriendo ni con otras pruebas.
- **Protocolo directo.** Las pruebas arman los mensajes ellas mismas (4 bytes de longitud + JSON) en vez de usar el CLI. Así pueden mandar mensajes inválidos, fragmentados o simultáneos. El CLI se prueba aparte, ejecutándolo como lo haría un usuario.
- **Limpieza segura.** Cada servicio de prueba lleva una variable de entorno única, `JR_PRUEBA_MARCA`, que heredan sus hijos y nietos. Al terminar cada prueba, aunque falle, se eliminan **solo** los procesos con esa marca. Con eso también se pueden contar los huérfanos sin confundirlos con procesos ajenos.
- **Pruebas de regresión.** Las que dicen "Regresión Fx" en su descripción reproducen una falla que existía en la versión anterior (ver `docs/incidents/` y los ADR 007 a 012). Si alguien reintroduce el error, esa prueba falla.

## Evidencia que genera (`verif/results/<run-id>/`)

| Archivo | Contenido |
|---|---|
| `resumen.md` | Resultado global, tabla por caso TC con sus requisitos, y detalle de cada prueba con duración y motivo de falla |
| `resultados.json` | Lo mismo en formato máquina |
| `salida_pruebas.txt` | Salida completa de la ejecución |
| `version.txt` | Commit de git (o SHA-256 de `src/` si no hay git) y si había cambios sin commit |
| `entorno.txt` | Distribución, kernel, Python, SQLite, CPUs y usuario |
| `configuracion.txt`, `comando.txt` | Configuración por defecto y el comando exacto usado |
| `servicios.tar.gz` | De cada servicio que levantó cada prueba: `data/jobrunner.log` (bitácora), `data/jobs.db`, `data/output/` y `servicio_salida.txt`. Se abre con `tar xzf servicios.tar.gz` (va comprimido porque son miles de archivos pequeños) |

Según los estándares del proyecto, los resultados **no deben editarse** para ocultar fallas. Si una corrida falla, se deja tal cual y se abre un Issue.
