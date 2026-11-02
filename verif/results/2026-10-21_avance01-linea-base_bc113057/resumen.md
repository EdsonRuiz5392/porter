# Resultados de verificación — 2026-10-21_avance01-linea-base_bc113057

**Resultado global: FAIL** · 23 PASS · 32 FAIL · 2 ERROR · 0 SKIP · 123.8 s

## Versión
```
Commit: bc1130578e4ab561d6aa627025b39bd05f2c4177
Rama: main
Cambios sin commit en src/: no
```

## Entorno
```
Fecha (UTC): 2026-10-22T03:18:57.010155+00:00
Distribución: Kali GNU/Linux Rolling
Kernel: Linux 6.18.33.2-microsoft-standard-WSL2 (x86_64)
Python: 3.12.15 (/home/edson/porter/.venv/bin/python3)
SQLite: 3.53.1
CPUs: 12
Usuario: edson (uid 1000)
```

## Comando
```
python3 verif/scripts/run_verificacion.py --run-id 2026-10-21_avance01-linea-base_bc113057
```

## Por caso de prueba

| Caso | Descripción | Requisitos | Pruebas | Resultado |
|---|---|---|---|---|
| TC-001 | Enviar trabajo válido | RF-01, RF-02, RNF-14 | 4 | FAIL |
| TC-002 | Cola y límite de concurrencia | RF-03, RF-05, RNF-04, RNF-07 | 2 | PASS |
| TC-003 | Estados y tiempos | RF-06, RF-07 | 2 | PASS |
| TC-004 | Consultar y listar | RF-08, RF-09, RNF-05 | 3 | FAIL |
| TC-005 | Cancelar en cola y en ejecución | RF-10 | 3 | FAIL |
| TC-006 | Capturar stdout/stderr y código | RF-11, RF-07 | 6 | FAIL |
| TC-007 | Reinicio y recuperación | RF-12, RF-13, RNF-10, RNF-11, RNF-30, RNF-31 | 3 | FAIL |
| TC-008 | Aislamiento de fallo | RNF-08, RNF-09 | 1 | PASS |
| TC-009 | Cierre controlado | RF-15, RNF-25, RNF-30 | 5 | FAIL |
| TC-012 | Fragmentación y desconexión | RF-21, RF-22, RNF-14, RNF-24 | 2 | FAIL |
| TC-013 | Configuración y salud | RF-16, RF-24 | 3 | FAIL |
| TC-015 | Ayuda y códigos de salida del CLI | RF-17, RNF-21 | 2 | FAIL |
| TC-016 | Saturación de cola y rechazo explícito | RF-25, RNF-29 | 2 | FAIL |
| TC-017 | Cancelaciones concurrentes | RF-26, RNF-27 | 4 | FAIL |
| TC-018 | Solicitud duplicada | RF-27 | 5 | FAIL |
| TC-019 | Desconexión durante solicitud | RF-28, RF-22 | 3 | FAIL |
| TC-020 | Terminación inesperada del hijo | RF-29, RNF-30 | 2 | FAIL |
| TC-021 | Escalamiento de cancelación | RF-30 | 1 | PASS |
| TC-022 | Recuperación con más pendientes que lugares / interrupción | RNF-28, RNF-31 | 2 | FAIL |
| TC-023 | Compatibilidad de protocolo | RNF-32 | 1 | PASS |
| TC-024 | Liberación de recursos bajo carga | RNF-33 | 1 | PASS |

## Detalle de cada prueba

| Caso | Prueba | Resultado | Segundos | Detalle |
|---|---|---|---|---|
| TC-001 | `TC001EnvioYValidacion.test_args_null_equivale_a_lista_vacia` | FAIL | 0.34 | AssertionError: 'FAILED' != 'SUCCEEDED' : {'id': '42a00d9c-0300-49ee-a817-cc50b4c5ba31', 'command': 'echo', 'args': None, 'status': 'FAILED', 'client_request_id': None, 'pid': None, 'submitted_at': '2026-10-22T03:16:53.391782+00:00', 'started_at': None, 'finished_at': '2026-10-22T03:16:53.408962+00: |
| TC-001 | `TC001EnvioYValidacion.test_comando_inexistente_termina_failed` | PASS | 0.38 |  |
| TC-001 | `TC001EnvioYValidacion.test_entradas_invalidas_se_rechazan_con_invalid_request` | FAIL | 0.29 | (caso='command=5'): AssertionError: 'INTERNAL_ERROR' != 'INVALID_REQUEST' : {'type': 'error', 'version': 1, 'code': 'INTERNAL_ERROR', 'message': "Error interno: 'int' object has no attribute 'strip'"} / (caso='args texto'): AssertionError: 'submit_response' != 'error' : {'type': 'submit_response', 'version': 1, 'ok': True, 'job_id': '6de6b703-8dce-4fb9-8463-619574e91aa4', 'status': 'QUEUED'} / (caso='args con números'): AssertionError: 'submit_response' != 'error' : {'type': 'submit_response', 'version': 1, 'ok': True, 'job_id': 'ba1dadc0-5443-4ecc-b10b-2a4f0806d281', 'status': 'QUEUED'} / (caso='comando de 100 KB'): AssertionError: 'submit_response' != 'error' : {'type': 'submit_response', 'version': 1, 'ok': True, 'job_id': '0398fbf6-22ef-4c78-a03f-68117f331e73', 'status': 'QUEUED'} / (caso='folio no texto'): AssertionError: 'submit_response' != 'error' : {'type': 'submit_response', 'version': 1, 'ok': True, 'job_id': 'eaf8e9c1-3217-482a-a363-e69697d6e3ae', 'status': 'QUEUED'} / (caso='status job_id lista'): AssertionError: 'INTERNAL_ERROR' != 'INVALID_REQUEST' : {'type': 'error', 'version': 1, 'code': 'INTERNAL_ERROR', 'message': "Error interno: Error binding parameter 1: type 'list' is not supported"} / (caso='cancel sin job_id'): AssertionError: 'NOT_FOUND' != 'INVALID_REQUEST' : {'type': 'error', 'version': 1, 'code': 'NOT_FOUND', 'message': 'Trabajo no encontrado.'} / (caso='list estado inexistente'): AssertionError: 'list_response' != 'error' : {'type': 'list_response', 'version': 1, 'jobs': []} / (caso='output stream inválido'): AssertionError: 'NOT_FOUND' != 'INVALID_REQUEST' : {'type': 'error', 'version': 1, 'code': 'NOT_FOUND', 'message': 'Trabajo no encontrado.'} / AssertionError: 4 != 0 : No debe crearse ningún trabajo |
| TC-001 | `TC001EnvioYValidacion.test_envio_valido_devuelve_id_unico` | PASS | 0.17 |  |
| TC-015 | `TC015AyudaYCodigosCLI.test_ayuda_y_codigos_de_salida` | FAIL | 0.3 | AssertionError: 'output' not found in 'Uso: python -m src.cliente.cli <comando> [argumentos]\nComandos disponibles:\n  submit <comando> [args...]   Enviar un nuevo trabajo\n  status <job_id>               Consultar estado de un trabajo\n  list                          Listar todos los trabajos\n  ca |
| TC-015 | `TC015AyudaYCodigosCLI.test_servicio_apagado_da_codigo_1_y_sugerencia` | FAIL | 0.1 | AssertionError: 'conexión' not found in "[-] error: comando desconocido 'health'. usa --help para ver la lista." |
| TC-002 | `TC002ColaYConcurrencia.test_fifo` | PASS | 1.53 |  |
| TC-002 | `TC002ColaYConcurrencia.test_ocho_trabajos_con_limite_tres` | PASS | 6.4 |  |
| TC-003 | `TC003EstadosYTiempos.test_ciclo_de_vida_y_tiempos` | PASS | 0.76 |  |
| TC-003 | `TC003EstadosYTiempos.test_codigo_distinto_de_cero_es_failed` | PASS | 0.36 |  |
| TC-006 | `TC006SalidasSeparadas.test_bytes_que_no_son_texto` | PASS | 0.34 |  |
| TC-006 | `TC006SalidasSeparadas.test_cli_output` | FAIL | 0.43 | AssertionError: Tuples differ: (1, "[-] Error: comando desconocido 'output'. Usa --help para ver la lista.") != (0, 'SALIDA') |
| TC-006 | `TC006SalidasSeparadas.test_linea_de_200000_caracteres` | FAIL | 0.34 | AssertionError: Tuples differ: ('FAILED', -1) != ('SUCCEEDED', 0) |
| TC-006 | `TC006SalidasSeparadas.test_salida_visible_mientras_corre` | PASS | 3.31 |  |
| TC-006 | `TC006SalidasSeparadas.test_stdout_y_stderr_no_se_mezclan` | PASS | 0.35 |  |
| TC-006 | `TC006SalidasSeparadas.test_trabajo_que_lee_stdin_no_se_cuelga` | PASS | 0.34 |  |
| TC-004 | `TC004Consultas.test_rnf05_consulta_en_menos_de_un_segundo_con_100_trabajos` | PASS | 2.37 |  |
| TC-004 | `TC004Consultas.test_rnf06_500_registros_sin_perdida_tras_reinicio` | FAIL | 11.54 | AssertionError: False is not true : Todos con estado y tiempos completos |
| TC-004 | `TC004Consultas.test_status_list_y_filtro` | FAIL | 0.49 | AssertionError: '3f00fd90-b92f-4c5b-8e21-9ef75edaebc9' unexpectedly found in "[*] Trabajos registrados:\n    ID: 3f00fd90-b92f-4c5b-8e21-9ef75edaebc9 / Comando: 'true' / Estado: SUCCEEDED / Exit code: 0\n    ID: 68377a18-7901-48a1-902b-65f1ab02a5f4 / Comando: 'false' / Estado: FAILED / Exit code: 1" |
| TC-013 | `TC013ConfiguracionYSalud.test_configuracion_invalida_no_arranca` | FAIL | 11.34 | (variable='MAX_CONCURRENCY', valor='0'): AssertionError: True is not false : MAX_CONCURRENCY=0 no debería permitir arrancar / (variable='MAX_CONCURRENCY', valor='-2'): AssertionError: True is not false : MAX_CONCURRENCY=-2 no debería permitir arrancar / (variable='MAX_CONCURRENCY', valor='abc'): AssertionError: 'Configuración inválida' not found in 'Traceback (most recent call last):\n  File "<frozen runpy>", line 198, in _run_module_as_main\n  File "<frozen runpy>", line 88, in _run_code\n  File "/home/edson/porter/src/servicio/main.py", line 70, in <module>\n    asyncio.run(arrancar())\n  / (variable='MAX_QUEUE', valor='0'): AssertionError: True is not false : MAX_QUEUE=0 no debería permitir arrancar / (variable='PORT', valor='99999'): AssertionError: 'Configuración inválida' not found in '' / (variable='GRACE_SECONDS', valor='-1'): AssertionError: True is not false : GRACE_SECONDS=-1 no debería permitir arrancar / (variable='SHUTDOWN_TIMEOUT', valor='x'): AssertionError: True is not false : SHUTDOWN_TIMEOUT=x no debería permitir arrancar |
| TC-013 | `TC013ConfiguracionYSalud.test_configuracion_se_registra_al_arrancar` | FAIL | 0.21 | AssertionError: [] is not true |
| TC-013 | `TC013ConfiguracionYSalud.test_health` | FAIL | 0.96 | AssertionError: 1 != 0 |
| TC-005 | `TC005Cancelacion.test_cancelar_alcanza_a_los_nietos` | FAIL | 6.88 | AssertionError: unexpectedly None : El trabajo debe terminar aunque tenga nietos |
| TC-005 | `TC005Cancelacion.test_cancelar_en_cola` | PASS | 0.47 |  |
| TC-005 | `TC005Cancelacion.test_cancelar_en_ejecucion` | FAIL | 0.46 | AssertionError: [] is not true |
| TC-017 | `TC017CancelacionesConcurrentes.test_cancelar_inmediatamente_despues_de_enviar` | FAIL | 0.71 | AssertionError: Items in the first set but not the second: |
| TC-017 | `TC017CancelacionesConcurrentes.test_caso_a_cancelacion_llega_primero` | ERROR | 6.76 | TypeError: 'NoneType' object is not subscriptable |
| TC-017 | `TC017CancelacionesConcurrentes.test_caso_b_termina_primero` | PASS | 0.24 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_cinco_cancelaciones_simultaneas` | PASS | 0.46 |  |
| TC-021 | `TC021Escalamiento.test_proceso_que_ignora_sigterm` | PASS | 2.75 |  |
| TC-007 | `TC007Recuperacion.test_kill9_con_trabajos_corriendo_y_en_cola` | FAIL | 1.8 | AssertionError: Lists differ: [3082, 3083, 3085] != [] |
| TC-007 | `TC007Recuperacion.test_nieto_huerfano_con_lider_muerto` | FAIL | 4.0 | AssertionError: False is not true : El nieto debe eliminarse |
| TC-007 | `TC007Recuperacion.test_pid_reutilizado_no_se_mata` | FAIL | 0.87 | AssertionError: [] is not true |
| TC-022 | `TC022RecuperacionCapacidad.test_bajar_max_queue_con_pendientes` | FAIL | 0.76 | AssertionError: False is not true : Debe arrancar aunque haya 8 pendientes y capacidad 3: |
| TC-022 | `TC022RecuperacionCapacidad.test_base_integra_tras_kill9_durante_escrituras` | PASS | 4.36 |  |
| TC-008 | `TC008Aislamiento.test_un_trabajo_que_falla_no_afecta_a_otros` | PASS | 2.33 |  |
| TC-020 | `TC020MuerteInesperada.test_falla_de_captura_no_deja_procesos_ni_descuadra_el_limite` | FAIL | 0.45 | AssertionError: Lists differ: [3328] != [] |
| TC-020 | `TC020MuerteInesperada.test_senal_externa_queda_failed_con_diagnostico` | FAIL | 0.93 | (senal='SIGKILL'): AssertionError: Tuples differ: ('CANCELED', -9) != ('FAILED', -9) / (senal='SIGTERM'): AssertionError: Tuples differ: ('CANCELED', -15) != ('FAILED', -15) / (senal='SIGSEGV'): AssertionError: [] is not true |
| TC-024 | `TC024RecursosBajoCarga.test_cuatro_lotes_de_90_sin_fugas` | PASS | 10.03 |  |
| TC-009 | `TC009CierreControlado.test_cierre_con_tiempo_limite` | FAIL | 20.77 | AssertionError: False is not true : El cierre debe terminar en tiempo acotado |
| TC-009 | `TC009CierreControlado.test_ctrl_c_hace_el_mismo_cierre_controlado` | FAIL | 0.93 | AssertionError: Tuples differ: ('FAILED', -2) != ('CANCELED', -15) |
| TC-009 | `TC009CierreControlado.test_durante_el_cierre_no_acepta_nuevos` | FAIL | 3.4 | AssertionError: [] is not true |
| TC-009 | `TC009CierreControlado.test_puerto_ocupado` | FAIL | 5.46 | AssertionError: False is not true : Con el puerto ocupado el servicio debe terminar |
| TC-009 | `TC009CierreControlado.test_sigterm_con_servicio_ocioso` | PASS | 0.26 |  |
| TC-012 | `TC012Protocolo.test_mensaje_byte_a_byte_y_varias_solicitudes_por_conexion` | PASS | 0.31 |  |
| TC-012 | `TC012Protocolo.test_mensajes_invalidos_reciben_error_y_no_tumban_el_servicio` | FAIL | 0.23 | (caso='longitud de 2 GB'): asyncio.exceptions.IncompleteReadError: 0 bytes read on a total of 4 expected bytes / (caso='JSON inválido'): asyncio.exceptions.IncompleteReadError: 0 bytes read on a total of 4 expected bytes / (caso='JSON que no es objeto'): asyncio.exceptions.IncompleteReadError: 0 bytes read on a total of 4 expected bytes / AssertionError: 0 != 3 |
| TC-019 | `TC019Desconexion.test_desconexion_a_medio_mensaje_no_tiene_efecto` | PASS | 0.71 |  |
| TC-019 | `TC019Desconexion.test_desconexion_tras_mensaje_completo_la_operacion_queda_aceptada` | FAIL | 0.81 | AssertionError: 'Traceback' unexpectedly found in 'Unhandled exception in client_connected_cb\ntransport: <_SelectorSocketTransport closed fd=8>\nTraceback (most recent call last):\n  File "/home/edson/porter/src/servicio/entrada.py", line 177, in _on_connect\n    await handle_client(reader, writer, |
| TC-019 | `TC019Desconexion.test_reintento_con_folio_recupera_el_id` | FAIL | 0.76 | AssertionError: '5ac24fac-5ea6-4934-9799-8059a26c95a6' != 'd03e5897-24aa-440b-9675-c411f32e02a9' |
| TC-023 | `TC023CompatibilidadProtocolo.test_version_incompatible_se_rechaza_explicitamente` | PASS | 0.21 |  |
| TC-016 | `TC016Saturacion.test_carrera_diez_envios_con_un_lugar` | FAIL | 0.66 | AssertionError: Counter({'INTERNAL_ERROR': 9, 'QUEUED': 1}) != Counter({'QUEUE_FULL': 9, 'QUEUED': 1}) |
| TC-016 | `TC016Saturacion.test_rechazo_explicito_secuencial` | FAIL | 0.51 | AssertionError: 0 != 2 : Los rechazos se registran (RF-23) |
| TC-018 | `TC018Duplicados.test_a_reintento_mismo_folio_mismo_comando` | FAIL | 0.37 | AssertionError: 'd8d04907-e062-4889-8e2f-8deddd2d430e' != 'e4ac534e-4d5d-4952-9e6c-ae8075e67b24' |
| TC-018 | `TC018Duplicados.test_b_sin_folio_cada_envio_es_nuevo` | PASS | 0.14 |  |
| TC-018 | `TC018Duplicados.test_c_mismo_folio_otro_comando_es_conflicto` | ERROR | 0.26 | (comando='ls', args=[]): AssertionError: Tuples differ: ('submit_response', None) != ('error', 'REQUEST_ID_CONFLICT') / (comando='echo', args=['dos']): AssertionError: Tuples differ: ('submit_response', None) != ('error', 'REQUEST_ID_CONFLICT') / TypeError: 'NoneType' object is not subscriptable |
| TC-018 | `TC018Duplicados.test_cli_request_id` | FAIL | 0.65 | AssertionError: Tuples differ: (0, 0, 0, 0) != (0, 0, 1, 1) |
| TC-018 | `TC018Duplicados.test_d_seis_envios_simultaneos_mismo_folio` | FAIL | 0.45 | AssertionError: 6 != 1 : [{'type': 'submit_response', 'version': 1, 'ok': True, 'job_id': '2c5a31da-57c5-4adf-9f33-6a1456397c93', 'status': 'QUEUED'}, {'type': 'submit_response', 'version': 1, 'ok': True, 'job_id': '2bb2f1e0-c69b-4f3b-926d-d181c32396b1', 'status': 'QUEUED'}, {'type': 'submit_respons |

## Archivos de esta carpeta

- `salida_pruebas.txt`: salida completa de la ejecución.
- `resultados.json`: los mismos resultados en formato máquina.
- `servicios.tar.gz`: por cada servicio que levantó cada prueba, su `data/jobrunner.log` (bitácora), `data/jobs.db` (base), `data/output/` (salidas) y `servicio_salida.txt` (lo que imprimió el servicio). Se abre con `tar xzf servicios.tar.gz`.
- `version.txt`, `entorno.txt`, `configuracion.txt`, `comando.txt`.
