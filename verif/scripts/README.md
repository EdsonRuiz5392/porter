# verif/scripts — Pruebas automatizadas de JobRunner

Pruebas de sistema que arrancan el **servicio real** y verifican los casos TC del plan de verificación. Cumplen RNF-20 ("ejecutables con un único comando documentado") y guardan la evidencia como piden los estándares del repositorio.

Este archivo describe **qué son** las pruebas y **qué evidencia generan**. Para **correrlas** paso a paso (también en WSL), ver [`GUIA_EJECUCION.md`](GUIA_EJECUCION.md). Los resultados no están aquí: salen de cada corrida, en `verif/results/`.

## Scripts para ejecutar

| Script | Qué hace |
|---|---|
| `run_verificacion.py` | **Una** corrida: prueba el `src/` que está junto a `verif/` y guarda su evidencia en `verif/results/<run-id>/` |
| `run_evidencia.py` | La evidencia completa del avance 3. Llama varias veces a `run_verificacion.py` en dos partes: `--solo-antes` (código del avance 2) y `--solo-despues` (código actual, dos corridas completas y las repeticiones), y escribe `RESUMEN_avance03.md` |
| `jr_helpers.py` | Utilidades compartidas por las pruebas: arrancar el servicio, hablar el protocolo, limpiar |

Solo usan la biblioteca estándar de Python (`unittest`); no hay que instalar nada. Requisitos: Linux, Python 3.10 o superior, los comandos `bash`, `sleep`, `echo`, `cat` y `printf`, y un usuario normal (sin root, para que sirvan también de evidencia de RNF-03).

Formas de correrlas que **no** guardan evidencia, útiles mientras se programa:

```bash
python3 -m unittest discover -s verif/scripts -v
python3 -m pytest verif/scripts -v        # pytest también ejecuta pruebas unittest
```

## Qué contiene cada archivo de pruebas

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
| **Avance 3** | | |
| `test_tc010_tc011_red_avance03.py` | TC-010, TC-011 | RF-18, RF-19, RF-20, RNF-12, RNF-13, RNF-26 |
| `test_tc016_tc024_limites_de_clientes_avance03.py` | TC-016, TC-024 | RF-23, RNF-08, RNF-29, RNF-33 |
| `test_tc006_salida_por_partes_avance03.py` | TC-006 | RF-11, RNF-14 |
| `test_tc005_tc007_tc009_tc013_robustez_avance03.py` | TC-005, TC-007, TC-009, TC-013 | RF-10, RF-13, RF-15, RF-23, RF-24, RF-27, RNF-22, RNF-25, RNF-30, RNF-31 |
| **Correcciones del avance 3** | | |
| `test_tc013_tc022_tc024_regresion_issues_avance03.py` | TC-013, TC-022, TC-024 | RF-24, RF-29, RNF-06, RNF-31, RNF-33 |
| `test_tc009_tc015_arranque_y_cliente_avance03.py` | TC-009, TC-015 | RF-15, RF-17, RNF-21, RNF-25 |

Los archivos `*_avance03.py` **amplían** casos que ya existían (TC-005, 006, 007, 009, 013, 015, 016, 022, 024) y cubren por primera vez TC-010 y TC-011. En `resumen.md` cada caso conserva la descripción original del plan y suma los requisitos nuevos.

Las mismas pruebas sirven contra cualquier versión de `src/`: con una versión anterior, las que fallan muestran lo que esa versión no tenía.

**No cubiertos aquí** (requieren otro entorno o son inspección o documentación): la operación **entre dos equipos reales** en el hotspot o la VPN (es la demostración de TC-010 y TC-011, con su evidencia propia en `verif/results/`), TC-014 (construcción desde un clon limpio) y TC-015 en su parte de usabilidad documental.

## Qué comprueban las regresiones de las correcciones del avance 3

Cada una provoca a propósito la situación del defecto, para que aparezca siempre si existe y no dependa de la suerte ni de la velocidad de la máquina.

| Prueba | Defecto (ADR) | Qué provoca | Qué comprueba |
|---|---|---|---|
| `test_health_cuenta_los_trabajos_en_transito` | #59 (ADR-017 rev. 1) | Un launcher que tarda 2 s en crear el proceso | Que `health` no diga 0 en ejecución y 0 en cola mientras la base tiene un QUEUED |
| `test_bloqueo_de_7s_no_marca_failed_un_trabajo_valido` | #58 (ADR-018) | Otra conexión bloquea la base 7 s mientras termina un trabajo | Que el trabajo termine `SUCCEEDED` y no `FAILED -1` |
| `test_si_la_base_no_responde_el_cupo_se_libera` | #58 (ADR-018) | SQLite espera solo 0.5 s (con un `sitecustomize.py` temporal en la carpeta de la prueba, no en `src/`) y la base se bloquea | Que el cupo se libere, que quede `PERSIST_ERROR` en `health` y que el siguiente arranque deje el trabajo en un estado final |
| `test_sigterm_durante_el_arranque_hace_cierre_controlado` | ADR-011 rev. 1 | 300 trabajos por recuperar y SIGTERM en cuanto aparece `SERVICE_STARTED` | Que el servicio haga el cierre controlado (código 0) y no muera por la señal |
| `test_el_cliente_espera_mas_que_el_servicio` | ADR-018 | — | Que la espera del cliente sea al menos dos esperas del servicio a la base, y que la ayuda diga el valor real |
| `test_tiempo_agotado_avisa_que_pudo_haberse_aceptado` | ADR-018 | Un servidor que acepta la conexión y nunca contesta | Que el CLI avise que el trabajo pudo haberse aceptado y sugiera `list` y el mismo folio |

## Cómo funcionan 

- **Servicio real y aislado.** Cada prueba arranca `python3 -m src.servicio.main` con un puerto libre y su propia carpeta de datos, así que no interfiere con un servicio que tengan corriendo ni con otras pruebas.
- **Arranque confirmado.** `iniciar()` da por arrancado el servicio cuando el servicio *nuevo* ya registró `SERVICE_STARTED` en su bitácora y el puerto acepta conexiones. No basta con que el puerto acepte: justo después de un `kill -9`, un hijo que el servicio anterior estaba creando (entre `fork` y `exec`) puede conservar unos milisegundos una copia del socket de escucha, y la prueba se conectaría a esa copia antes de que el servicio nuevo escuche.
- **Protocolo directo.** Las pruebas arman los mensajes ellas mismas (4 bytes de longitud + JSON) en vez de usar el CLI. Así pueden mandar mensajes inválidos, fragmentados o simultáneos. El CLI se prueba aparte, ejecutándolo como lo haría un usuario.
- **"Otro equipo" sin red (TC-010 y TC-011).** En Linux toda la red `127.0.0.0/8` es local, así que una prueba puede conectarse *saliendo* desde `127.0.0.3` (hace de laptop autorizada) o desde `127.0.0.9` (hace de equipo no autorizado). Para el servicio son direcciones de origen distintas de `127.0.0.1`, igual que lo serían `192.168.43.23` en el hotspot o `10.8.0.2` en la VPN. Si el equipo tiene una IP de red local, una prueba más escucha en esa IP y se conecta por ella; si no la tiene, esa prueba sale como SKIP.
- **Limpieza segura.** Cada servicio de prueba lleva una variable de entorno única, `JR_PRUEBA_MARCA`, que heredan sus hijos y nietos. Al terminar cada prueba, aunque falle, se eliminan **solo** los procesos con esa marca. Con eso también se pueden contar los huérfanos sin confundirlos con procesos ajenos.
- **Pruebas de regresión.** Las que dicen "Regresión Fx" en su descripción reproducen una falla de una versión anterior (ver `docs/incidents/` y los ADR 007 a 012). Las que dicen "Regresión Issue" reproducen los Issues #58 y #59 (ADR-017 revisión 1 y ADR-018). Si alguien reintroduce el error, esa prueba falla.
- **Repeticiones y carga (`run_evidencia.py`).** Los Issues #58 y #59 eran intermitentes, así que una sola corrida que pasa no demuestra nada: se repiten TC-022, TC-004, TC-008, TC-009 y las regresiones. "Con carga" lanza 3 procesos por CPU que solo dan vueltas, para imitar una máquina lenta, y se apagan al terminar aunque algo falle.

## Evidencia que genera

**Cada corrida** de `run_verificacion.py` crea `verif/results/<run-id>/`:

| Archivo | Contenido |
|---|---|
| `resumen.md` | Resultado global, tabla por caso TC con sus requisitos, y detalle de cada prueba con duración y motivo de falla |
| `resultados.json` | Lo mismo en formato máquina |
| `salida_pruebas.txt` | Salida completa de la ejecución |
| `version.txt` | Commit de git, o SHA-256 de `src/` si no hay git, y si había cambios sin commit |
| `entorno.txt` | Fecha, distribución, kernel, Python, SQLite, CPUs y usuario |
| `configuracion.txt`, `comando.txt` | Configuración por defecto y el comando exacto usado |
| `servicios.tar.gz` | De cada servicio que levantó cada prueba: `data/jobrunner.log` (bitácora), `data/jobs.db`, `data/output/` y `servicio_salida.txt`. Se abre con `tar xzf servicios.tar.gz` |

**`run_evidencia.py`** crea, en `verif/results/`:

| Parte | Carpetas y archivos |
|---|---|
| `--solo-antes` | `antes_avance02/` y `repeticiones_avance03/con_carga/avance02-tc022-*` |
| `--solo-despues` | `despues_avance03/`, `despues_avance03_corrida2/`, `repeticiones_avance03/sin_carga/`, `repeticiones_avance03/con_carga/corregido-*`, `repeticiones_avance03/README.md` y `RESUMEN_avance03.md` |

`RESUMEN_avance03.md` se arma con lo que haya en `verif/results/`, así que incluye el "antes" aunque se haya corrido otro día. No sobrescribe evidencia: si alguna carpeta que va a crear ya existe, se detiene.

Según los estándares del proyecto, los resultados **no deben editarse** para ocultar fallas. Si una corrida falla, se deja tal cual y se abre un Issue.
