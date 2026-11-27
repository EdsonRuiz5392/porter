# Resultados de verificación — repeticiones_avance03/con_carga/avance02-tc022-04

**Resultado global: FAIL** · 4 PASS · 4 FAIL · 0 ERROR · 0 SKIP · 74.8 s

## Versión
```
Sin repositorio git: se identifica el código con el SHA-256 de todos los archivos de src/.
SHA-256 de src/: ca49101cfe482f9e75cc638996c72ebbeaa03e2c517c226c20a2c8708b1bcb07
Archivos: 18
```

## Entorno
```
Fecha (UTC): 2026-11-24T03:03:58.996863+00:00
Distribución: Kali GNU/Linux Rolling
Kernel: Linux 6.18.33.2-microsoft-standard-WSL2 (x86_64)
Python: 3.12.15 (/home/edson/porter/.venv/bin/python3)
SQLite: 3.53.1
CPUs: 12
Usuario: edson (uid 1000)
```

## Comando
```
python3 verif/scripts/run_verificacion.py --run-id repeticiones_avance03/con_carga/avance02-tc022-04 --filtro tc022
```

## Por caso de prueba

| Caso | Descripción | Requisitos | Pruebas | Resultado |
|---|---|---|---|---|
| TC-007 | Reinicio y recuperación | RF-12, RF-13, RNF-10, RNF-11, RNF-30, RNF-31, RF-27 | 3 | PASS |
| TC-013 | Configuración y salud | RF-16, RF-24, RF-23, RNF-22, RNF-31 | 1 | FAIL |
| TC-022 | Recuperación con más pendientes que lugares / interrupción | RNF-28, RNF-31 | 2 | FAIL |
| TC-024 | Liberación de recursos bajo carga | RNF-33, RF-29, RNF-06, RNF-08 | 2 | FAIL |

## Detalle de cada prueba

| Caso | Prueba | Resultado | Segundos | Detalle |
|---|---|---|---|---|
| TC-007 | `TC007Recuperacion.test_kill9_con_trabajos_corriendo_y_en_cola` | PASS | 3.01 |  |
| TC-007 | `TC007Recuperacion.test_nieto_huerfano_con_lider_muerto` | PASS | 1.51 |  |
| TC-007 | `TC007Recuperacion.test_pid_reutilizado_no_se_mata` | PASS | 2.33 |  |
| TC-022 | `TC022RecuperacionCapacidad.test_bajar_max_queue_con_pendientes` | PASS | 6.76 |  |
| TC-022 | `TC022RecuperacionCapacidad.test_base_integra_tras_kill9_durante_escrituras` | FAIL | 29.7 | AssertionError: False is not true : Sin estados imposibles: {'SUCCEEDED', 'QUEUED', 'FAILED', 'RUNNING'} |
| TC-013 | `TC013SaludEnTransito.test_health_cuenta_los_trabajos_en_transito` | FAIL | 4.09 | AssertionError: Tuples differ: (0, 0) != (0, 1) : queued debe coincidir con lo que la base reporta como QUEUED: {'running': 0, 'queued': 0, 'starting': None, 'base': 'QUEUED'} |
| TC-024 | `TC024BaseOcupada.test_bloqueo_de_7s_no_marca_failed_un_trabajo_valido` | FAIL | 8.29 | AssertionError: Tuples differ: ('FAILED', -1) != ('SUCCEEDED', 0) |
| TC-024 | `TC024BaseOcupada.test_si_la_base_no_responde_el_cupo_se_libera` | FAIL | 19.11 | AssertionError: 'QUEUED' != 'SUCCEEDED' : Con MAX_CONCURRENCY=1, otro trabajo debe poder correr: {'id': 'bc647958-49e8-44c9-9ced-de7ca1f76aa3', 'command': 'echo', 'args': ['despues'], 'status': 'QUEUED', 'client_request_id': None, 'pid': None, 'submitted_at': '2026-11-24T03:03:43.631792+00:00', 'sta |

## Archivos de esta carpeta

- `salida_pruebas.txt`: salida completa de la ejecución.
- `resultados.json`: los mismos resultados en formato máquina.
- `servicios.tar.gz`: por cada servicio que levantó cada prueba, su `data/jobrunner.log` (bitácora), `data/jobs.db` (base), `data/output/` (salidas) y `servicio_salida.txt` (lo que imprimió el servicio). Se abre con `tar xzf servicios.tar.gz`.
- `version.txt`, `entorno.txt`, `configuracion.txt`, `comando.txt`.
