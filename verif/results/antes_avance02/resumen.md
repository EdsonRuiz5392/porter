# Resultados de verificación — antes_avance02

**Resultado global: FAIL** · 58 PASS · 25 FAIL · 8 ERROR · 0 SKIP · 294.9 s

## Versión
```
Sin repositorio git: se identifica el código con el SHA-256 de todos los archivos de src/.
SHA-256 de src/: ca49101cfe482f9e75cc638996c72ebbeaa03e2c517c226c20a2c8708b1bcb07
Archivos: 18
```

## Entorno
```
Fecha (UTC): 2026-11-24T02:59:01.747136+00:00
Distribución: Kali GNU/Linux Rolling
Kernel: Linux 6.18.33.2-microsoft-standard-WSL2 (x86_64)
Python: 3.12.15 (/home/edson/porter/.venv/bin/python3)
SQLite: 3.53.1
CPUs: 12
Usuario: edson (uid 1000)
```

## Comando
```
python3 verif/scripts/run_verificacion.py --run-id antes_avance02
```

## Por caso de prueba

| Caso | Descripción | Requisitos | Pruebas | Resultado |
|---|---|---|---|---|
| TC-001 | Enviar trabajo válido | RF-01, RF-02, RNF-14 | 4 | PASS |
| TC-002 | Cola y límite de concurrencia | RF-03, RF-05, RNF-04, RNF-07 | 2 | PASS |
| TC-003 | Estados y tiempos | RF-06, RF-07 | 2 | PASS |
| TC-004 | Consultar y listar | RF-08, RF-09, RNF-05 | 3 | FAIL |
| TC-005 | Cancelar en cola y en ejecución | RF-10, RNF-30 | 4 | FAIL |
| TC-006 | Capturar stdout/stderr y código | RF-11, RF-07, RNF-14 | 10 | FAIL |
| TC-007 | Reinicio y recuperación | RF-12, RF-13, RNF-10, RNF-11, RNF-30, RNF-31, RF-27 | 4 | FAIL |
| TC-008 | Aislamiento de fallo | RNF-08, RNF-09 | 1 | PASS |
| TC-009 | Cierre controlado | RF-15, RNF-25, RNF-30 | 7 | FAIL |
| TC-010 | Flujo remoto completo en LAN/VPN | RF-18, RF-19, RNF-26 | 5 | FAIL |
| TC-011 | Restricción de red | RF-20, RNF-12, RNF-13 | 6 | FAIL |
| TC-012 | Fragmentación y desconexión | RF-21, RF-22, RNF-14, RNF-24 | 2 | PASS |
| TC-013 | Configuración y salud | RF-16, RF-24, RF-23, RNF-22, RNF-31 | 8 | FAIL |
| TC-015 | Ayuda y códigos de salida del CLI | RF-17, RNF-21 | 4 | FAIL |
| TC-016 | Saturación de cola y rechazo explícito | RF-25, RNF-29, RF-23 | 5 | FAIL |
| TC-017 | Cancelaciones concurrentes | RF-26, RNF-27 | 4 | PASS |
| TC-018 | Solicitud duplicada | RF-27 | 5 | PASS |
| TC-019 | Desconexión durante solicitud | RF-28, RF-22 | 3 | PASS |
| TC-020 | Terminación inesperada del hijo | RF-29, RNF-30 | 2 | PASS |
| TC-021 | Escalamiento de cancelación | RF-30 | 1 | PASS |
| TC-022 | Recuperación con más pendientes que lugares / interrupción | RNF-28, RNF-31 | 2 | FAIL |
| TC-023 | Compatibilidad de protocolo | RNF-32 | 1 | PASS |
| TC-024 | Liberación de recursos bajo carga | RNF-33, RF-29, RNF-06, RNF-08 | 6 | FAIL |

## Detalle de cada prueba

| Caso | Prueba | Resultado | Segundos | Detalle |
|---|---|---|---|---|
| TC-001 | `TC001EnvioYValidacion.test_args_null_equivale_a_lista_vacia` | PASS | 0.48 |  |
| TC-001 | `TC001EnvioYValidacion.test_comando_inexistente_termina_failed` | PASS | 0.45 |  |
| TC-001 | `TC001EnvioYValidacion.test_entradas_invalidas_se_rechazan_con_invalid_request` | PASS | 0.22 |  |
| TC-001 | `TC001EnvioYValidacion.test_envio_valido_devuelve_id_unico` | PASS | 0.47 |  |
| TC-015 | `TC015AyudaYCodigosCLI.test_ayuda_y_codigos_de_salida` | PASS | 0.81 |  |
| TC-015 | `TC015AyudaYCodigosCLI.test_servicio_apagado_da_codigo_1_y_sugerencia` | PASS | 0.09 |  |
| TC-002 | `TC002ColaYConcurrencia.test_fifo` | PASS | 1.69 |  |
| TC-002 | `TC002ColaYConcurrencia.test_ocho_trabajos_con_limite_tres` | PASS | 6.49 |  |
| TC-003 | `TC003EstadosYTiempos.test_ciclo_de_vida_y_tiempos` | PASS | 0.87 |  |
| TC-003 | `TC003EstadosYTiempos.test_codigo_distinto_de_cero_es_failed` | PASS | 0.36 |  |
| TC-006 | `TC006SalidasSeparadas.test_bytes_que_no_son_texto` | PASS | 0.89 |  |
| TC-006 | `TC006SalidasSeparadas.test_cli_output` | PASS | 1.22 |  |
| TC-006 | `TC006SalidasSeparadas.test_linea_de_200000_caracteres` | PASS | 0.36 |  |
| TC-006 | `TC006SalidasSeparadas.test_salida_visible_mientras_corre` | PASS | 3.31 |  |
| TC-006 | `TC006SalidasSeparadas.test_stdout_y_stderr_no_se_mezclan` | PASS | 0.37 |  |
| TC-006 | `TC006SalidasSeparadas.test_trabajo_que_lee_stdin_no_se_cuelga` | PASS | 0.45 |  |
| TC-004 | `TC004Consultas.test_rnf05_consulta_en_menos_de_un_segundo_con_100_trabajos` | PASS | 8.22 |  |
| TC-004 | `TC004Consultas.test_rnf06_500_registros_sin_perdida_tras_reinicio` | FAIL | 35.54 | AssertionError: False is not true : Todos con estado y tiempos completos |
| TC-004 | `TC004Consultas.test_status_list_y_filtro` | PASS | 0.58 |  |
| TC-013 | `TC013ConfiguracionYSalud.test_configuracion_invalida_no_arranca` | PASS | 0.82 |  |
| TC-013 | `TC013ConfiguracionYSalud.test_configuracion_se_registra_al_arrancar` | PASS | 0.21 |  |
| TC-013 | `TC013ConfiguracionYSalud.test_health` | PASS | 1.02 |  |
| TC-005 | `TC005CancelacionDescendientes.test_descendiente_con_setsid_tambien_se_termina` | ERROR | 20.49 | TypeError: 'NoneType' object is not subscriptable |
| TC-007 | `TC007CaidaEnArranque.test_caida_durante_el_arranque_no_ejecuta_el_trabajo_dos_veces` | FAIL | 2.01 | AssertionError: 2 != 1 : El trabajo NO debe ejecutarse dos veces |
| TC-009 | `TC009CierreConClientes.test_cierre_no_espera_a_clientes_ociosos` | FAIL | 8.51 | AssertionError: False is not true : El cierre no debe quedarse esperando al cliente |
| TC-013 | `TC013SaludAmpliada.test_bitacora_registra_el_origen_de_cada_envio` | FAIL | 0.24 | AssertionError: '127.0.0.3' not found in '2026-11-24T02:55:42.981027+00:00 / job=003736e1-e6f0-4606-8ebb-747516b21224 / CREATED / Comando: true' |
| TC-013 | `TC013SaludAmpliada.test_errores_recientes_vencen_con_la_ventana` | ERROR | 0.35 | KeyError: 'last_errors' |
| TC-013 | `TC013SaludAmpliada.test_health_trae_configuracion_y_tiempo_activo` | FAIL | 0.21 | AssertionError: 'uptime_s' not found in {'type': 'health_response', 'version': 1, 'active': True, 'running': 0, 'queued': 0, 'recent_errors': 0} : {'type': 'health_response', 'version': 1, 'active': True, 'running': 0, 'queued': 0, 'recent_errors': 0} |
| TC-013 | `TC013SaludAmpliada.test_rechazos_por_validacion_se_registran` | FAIL | 0.21 | AssertionError: 0 != 2 : ['2026-11-24T02:55:43.722047+00:00 / job=- / SERVICE_STARTED / 127.0.0.1:32999 concurrencia=3 cola=100 grace=5.0s cierre=30.0s'] |
| TC-005 | `TC005Cancelacion.test_cancelar_alcanza_a_los_nietos` | PASS | 0.9 |  |
| TC-005 | `TC005Cancelacion.test_cancelar_en_cola` | PASS | 0.53 |  |
| TC-005 | `TC005Cancelacion.test_cancelar_en_ejecucion` | PASS | 0.48 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_cancelar_inmediatamente_despues_de_enviar` | PASS | 1.68 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_caso_a_cancelacion_llega_primero` | PASS | 0.77 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_caso_b_termina_primero` | PASS | 0.35 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_cinco_cancelaciones_simultaneas` | PASS | 0.46 |  |
| TC-021 | `TC021Escalamiento.test_proceso_que_ignora_sigterm` | PASS | 2.74 |  |
| TC-006 | `TC006SalidaGrande.test_cli_output_descarga_todas_las_partes` | FAIL | 0.54 | AssertionError: 1 != 0 : [-] Respuesta inválida del servicio: El mensaje anuncia 3600126 bytes, el máximo permitido es 1048576. |
| TC-006 | `TC006SalidaGrande.test_compatibilidad_sin_offset_salida_chica` | ERROR | 0.36 | KeyError: 'eof' |
| TC-006 | `TC006SalidaGrande.test_limite_pequeno_y_parametros_invalidos` | ERROR | 0.36 | KeyError: 'next_offset' |
| TC-006 | `TC006SalidaGrande.test_salida_de_3_mb_se_recupera_completa_por_protocolo` | FAIL | 0.45 | AssertionError: None != 0 |
| TC-007 | `TC007Recuperacion.test_kill9_con_trabajos_corriendo_y_en_cola` | PASS | 2.73 |  |
| TC-007 | `TC007Recuperacion.test_nieto_huerfano_con_lider_muerto` | PASS | 0.86 |  |
| TC-007 | `TC007Recuperacion.test_pid_reutilizado_no_se_mata` | PASS | 0.98 |  |
| TC-022 | `TC022RecuperacionCapacidad.test_bajar_max_queue_con_pendientes` | PASS | 3.78 |  |
| TC-022 | `TC022RecuperacionCapacidad.test_base_integra_tras_kill9_durante_escrituras` | FAIL | 13.26 | AssertionError: False is not true : Sin estados imposibles: {'QUEUED', 'FAILED', 'SUCCEEDED'} |
| TC-008 | `TC008Aislamiento.test_un_trabajo_que_falla_no_afecta_a_otros` | PASS | 2.36 |  |
| TC-020 | `TC020MuerteInesperada.test_falla_de_captura_no_deja_procesos_ni_descuadra_el_limite` | PASS | 2.04 |  |
| TC-020 | `TC020MuerteInesperada.test_senal_externa_queda_failed_con_diagnostico` | PASS | 0.95 |  |
| TC-024 | `TC024RecursosBajoCarga.test_cuatro_lotes_de_90_sin_fugas` | PASS | 25.18 |  |
| TC-009 | `TC009CierreControlado.test_cierre_con_tiempo_limite` | PASS | 4.92 |  |
| TC-009 | `TC009CierreControlado.test_ctrl_c_hace_el_mismo_cierre_controlado` | PASS | 2.46 |  |
| TC-009 | `TC009CierreControlado.test_durante_el_cierre_no_acepta_nuevos` | PASS | 3.6 |  |
| TC-009 | `TC009CierreControlado.test_puerto_ocupado` | PASS | 0.44 |  |
| TC-009 | `TC009CierreControlado.test_sigterm_con_servicio_ocioso` | PASS | 0.22 |  |
| TC-009 | `TC009SenalDuranteElArranque.test_sigterm_durante_el_arranque_hace_cierre_controlado` | FAIL | 0.31 | AssertionError: -15 != 0 : Cierre controlado, no muerte por la señal: |
| TC-015 | `TC015TiempoDeEsperaDelCliente.test_el_cliente_espera_mas_que_el_servicio` | ERROR | 0.0 | AttributeError: 'NoneType' object has no attribute 'group' |
| TC-015 | `TC015TiempoDeEsperaDelCliente.test_tiempo_agotado_avisa_que_pudo_haberse_aceptado` | FAIL | 0.2 | AssertionError: 'no respondió' not found in "[-] Error: comando desconocido '--timeout'. Usa --help para ver la lista." |
| TC-010 | `TC010FlujoRemoto.test_cli_con_host_y_puerto_explicitos` | FAIL | 0.26 | AssertionError: 1 != 0 : [-] Error: comando desconocido '--host'. Usa --help para ver la lista. |
| TC-010 | `TC010FlujoRemoto.test_escucha_en_la_ip_de_la_red_local` | FAIL | 0.1 | AssertionError: False is not true : El servicio no arrancó. Salida: |
| TC-010 | `TC010FlujoRemoto.test_escucha_en_varias_direcciones` | FAIL | 0.1 | AssertionError: False is not true : El servicio no arrancó. Salida: |
| TC-010 | `TC010FlujoRemoto.test_flujo_completo_desde_otra_direccion_autorizada` | PASS | 0.59 |  |
| TC-010 | `TC010FlujoRemoto.test_misma_semantica_local_y_remota` | PASS | 0.27 |  |
| TC-011 | `TC011RestriccionDeRed.test_configuracion_de_red_invalida_no_arranca` | FAIL | 50.15 | (caso='prefijo imposible'): AssertionError: False is not true : Con configuración de red inválida no debe quedarse corriendo / (caso='texto que no es red'): AssertionError: False is not true : Con configuración de red inválida no debe quedarse corriendo / (caso='todo internet'): AssertionError: False is not true : Con configuración de red inválida no debe quedarse corriendo / (caso='red pública'): AssertionError: False is not true : Con configuración de red inválida no debe quedarse corriendo / (caso='lista vacía'): AssertionError: False is not true : Con configuración de red inválida no debe quedarse corriendo / (caso='escuchar en IP pública'): AssertionError: 'Configuración inválida' not found in "[-] No se puede escuchar en 8.8.8.8:41069: Cannot assign requested address (while attempting to bind on address ('8.8.8.8', 41069)). ¿Hay otro servicio usando ese puerto? Cambia JOBRUNNER_PORT o detén el otro proceso.\n" / (caso='host que no es IP'): AssertionError: 'Configuración inválida' not found in "[-] No se puede escuchar en servidor-casa:53739: Name or service not known (while attempting to bind on address ('servidor-casa', 53739)). ¿Hay otro servicio usando ese puerto? Cambia JOBRUNNER_PORT o detén el otro proceso.\n" |
| TC-011 | `TC011RestriccionDeRed.test_direccion_no_autorizada_se_rechaza_y_se_registra` | FAIL | 0.24 | AssertionError: Tuples differ: ('submit_response', None) != ('error', 'ACCESS_DENIED') |
| TC-011 | `TC011RestriccionDeRed.test_escuchar_en_todas_las_interfaces_queda_advertido` | FAIL | 0.2 | AssertionError: [] is not true : ['2026-11-24T02:57:49.490945+00:00 / job=- / SERVICE_STARTED / 0.0.0.0:45091 concurrencia=3 cola=100 grace=5.0s cierre=30.0s'] |
| TC-011 | `TC011RestriccionDeRed.test_por_defecto_solo_localhost` | FAIL | 0.21 | AssertionError: None != 'ACCESS_DENIED' : Ni siquiera otra dirección de loopback entra si no está en la lista |
| TC-011 | `TC011RestriccionDeRed.test_rechazo_sin_enviar_nada` | ERROR | 5.23 | asyncio.exceptions.CancelledError |
| TC-011 | `TC011RestriccionDeRed.test_redes_en_notacion_cidr` | FAIL | 0.21 | (origen='127.0.0.5'): AssertionError: 'health_response' != 'error' / (origen='127.0.0.200'): AssertionError: 'health_response' != 'error' / AssertionError: 0 != 2 |
| TC-012 | `TC012Protocolo.test_mensaje_byte_a_byte_y_varias_solicitudes_por_conexion` | PASS | 0.29 |  |
| TC-012 | `TC012Protocolo.test_mensajes_invalidos_reciben_error_y_no_tumban_el_servicio` | PASS | 0.31 |  |
| TC-019 | `TC019Desconexion.test_desconexion_a_medio_mensaje_no_tiene_efecto` | PASS | 0.8 |  |
| TC-019 | `TC019Desconexion.test_desconexion_tras_mensaje_completo_la_operacion_queda_aceptada` | PASS | 0.81 |  |
| TC-019 | `TC019Desconexion.test_reintento_con_folio_recupera_el_id` | PASS | 0.71 |  |
| TC-023 | `TC023CompatibilidadProtocolo.test_version_incompatible_se_rechaza_explicitamente` | PASS | 0.31 |  |
| TC-013 | `TC013SaludEnTransito.test_health_cuenta_los_trabajos_en_transito` | FAIL | 3.77 | AssertionError: Tuples differ: (0, 0) != (0, 1) : queued debe coincidir con lo que la base reporta como QUEUED: {'running': 0, 'queued': 0, 'starting': None, 'base': 'QUEUED'} |
| TC-024 | `TC024BaseOcupada.test_bloqueo_de_7s_no_marca_failed_un_trabajo_valido` | FAIL | 7.58 | AssertionError: Tuples differ: ('FAILED', -1) != ('SUCCEEDED', 0) |
| TC-024 | `TC024BaseOcupada.test_si_la_base_no_responde_el_cupo_se_libera` | FAIL | 18.58 | AssertionError: 'QUEUED' != 'SUCCEEDED' : Con MAX_CONCURRENCY=1, otro trabajo debe poder correr: {'id': '35cdab75-dd13-4f5b-91b7-4756046df90f', 'command': 'echo', 'args': ['despues'], 'status': 'QUEUED', 'client_request_id': None, 'pid': None, 'submitted_at': '2026-11-24T02:58:13.264501+00:00', 'sta |
| TC-016 | `TC016Saturacion.test_carrera_diez_envios_con_un_lugar` | PASS | 0.8 |  |
| TC-016 | `TC016Saturacion.test_rechazo_explicito_secuencial` | PASS | 1.13 |  |
| TC-018 | `TC018Duplicados.test_a_reintento_mismo_folio_mismo_comando` | PASS | 0.76 |  |
| TC-018 | `TC018Duplicados.test_b_sin_folio_cada_envio_es_nuevo` | PASS | 0.58 |  |
| TC-018 | `TC018Duplicados.test_c_mismo_folio_otro_comando_es_conflicto` | PASS | 0.5 |  |
| TC-018 | `TC018Duplicados.test_cli_request_id` | PASS | 0.56 |  |
| TC-018 | `TC018Duplicados.test_d_seis_envios_simultaneos_mismo_folio` | PASS | 0.54 |  |
| TC-016 | `TC016LimiteDeClientes.test_cliente_de_mas_recibe_too_many_clients` | FAIL | 5.57 | AssertionError: False is not true |
| TC-016 | `TC016LimiteDeClientes.test_health_reporta_clientes_conectados` | FAIL | 5.58 | AssertionError: False is not true |
| TC-016 | `TC016LimiteDeClientes.test_muchos_clientes_simultaneos_dentro_del_limite` | PASS | 1.34 |  |
| TC-024 | `TC024ClientesLentosYOciosos.test_cliente_ocioso_se_desconecta_y_libera_su_lugar` | FAIL | 5.58 | AssertionError: False is not true |
| TC-024 | `TC024ClientesLentosYOciosos.test_descriptores_vuelven_a_la_base_tras_muchas_conexiones` | ERROR | 5.21 | asyncio.exceptions.CancelledError |
| TC-024 | `TC024ClientesLentosYOciosos.test_mensaje_a_medias_no_retiene_la_conexion` | ERROR | 5.21 | asyncio.exceptions.CancelledError |

## Archivos de esta carpeta

- `salida_pruebas.txt`: salida completa de la ejecución.
- `resultados.json`: los mismos resultados en formato máquina.
- `servicios.tar.gz`: por cada servicio que levantó cada prueba, su `data/jobrunner.log` (bitácora), `data/jobs.db` (base), `data/output/` (salidas) y `servicio_salida.txt` (lo que imprimió el servicio). Se abre con `tar xzf servicios.tar.gz`.
- `version.txt`, `entorno.txt`, `configuracion.txt`, `comando.txt`.
