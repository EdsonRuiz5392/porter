# Resultados de verificación — 2026-11-02_avance02-final

**Resultado global: PASS** · 57 PASS · 0 FAIL · 0 ERROR · 0 SKIP · 85.0 s

## Versión
```
Commit: 3755ec6daec39bea315f1758708694ad68851c99
Rama: 48-ejecutar-las-pruebas-automatizadas-y-subir-la-evidencia
Cambios sin commit en src/: no
```

## Entorno
```
Fecha (UTC): 2026-11-02T20:46:49.595885+00:00
Distribución: Ubuntu 24.04.4 LTS
Kernel: Linux 6.8.0-147-generic (x86_64)
Python: 3.12.3 (/usr/bin/python3)
SQLite: 3.45.1
CPUs: 2
Usuario: ubuntu (uid 1000)
```

## Comando
```
python3 verif/scripts/run_verificacion.py --run-id 2026-11-02_avance02-final
```

## Por caso de prueba

| Caso | Descripción | Requisitos | Pruebas | Resultado |
|---|---|---|---|---|
| TC-001 | Enviar trabajo válido | RF-01, RF-02, RNF-14 | 4 | PASS |
| TC-002 | Cola y límite de concurrencia | RF-03, RF-05, RNF-04, RNF-07 | 2 | PASS |
| TC-003 | Estados y tiempos | RF-06, RF-07 | 2 | PASS |
| TC-004 | Consultar y listar | RF-08, RF-09, RNF-05 | 3 | PASS |
| TC-005 | Cancelar en cola y en ejecución | RF-10 | 3 | PASS |
| TC-006 | Capturar stdout/stderr y código | RF-11, RF-07 | 6 | PASS |
| TC-007 | Reinicio y recuperación | RF-12, RF-13, RNF-10, RNF-11, RNF-30, RNF-31 | 3 | PASS |
| TC-008 | Aislamiento de fallo | RNF-08, RNF-09 | 1 | PASS |
| TC-009 | Cierre controlado | RF-15, RNF-25, RNF-30 | 5 | PASS |
| TC-012 | Fragmentación y desconexión | RF-21, RF-22, RNF-14, RNF-24 | 2 | PASS |
| TC-013 | Configuración y salud | RF-16, RF-24 | 3 | PASS |
| TC-015 | Ayuda y códigos de salida del CLI | RF-17, RNF-21 | 2 | PASS |
| TC-016 | Saturación de cola y rechazo explícito | RF-25, RNF-29 | 2 | PASS |
| TC-017 | Cancelaciones concurrentes | RF-26, RNF-27 | 4 | PASS |
| TC-018 | Solicitud duplicada | RF-27 | 5 | PASS |
| TC-019 | Desconexión durante solicitud | RF-28, RF-22 | 3 | PASS |
| TC-020 | Terminación inesperada del hijo | RF-29, RNF-30 | 2 | PASS |
| TC-021 | Escalamiento de cancelación | RF-30 | 1 | PASS |
| TC-022 | Recuperación con más pendientes que lugares / interrupción | RNF-28, RNF-31 | 2 | PASS |
| TC-023 | Compatibilidad de protocolo | RNF-32 | 1 | PASS |
| TC-024 | Liberación de recursos bajo carga | RNF-33 | 1 | PASS |

## Detalle de cada prueba

| Caso | Prueba | Resultado | Segundos | Detalle |
|---|---|---|---|---|
| TC-001 | `TC001EnvioYValidacion.test_args_null_equivale_a_lista_vacia` | PASS | 0.34 |  |
| TC-001 | `TC001EnvioYValidacion.test_comando_inexistente_termina_failed` | PASS | 0.33 |  |
| TC-001 | `TC001EnvioYValidacion.test_entradas_invalidas_se_rechazan_con_invalid_request` | PASS | 0.24 |  |
| TC-001 | `TC001EnvioYValidacion.test_envio_valido_devuelve_id_unico` | PASS | 0.27 |  |
| TC-015 | `TC015AyudaYCodigosCLI.test_ayuda_y_codigos_de_salida` | PASS | 0.89 |  |
| TC-015 | `TC015AyudaYCodigosCLI.test_servicio_apagado_da_codigo_1_y_sugerencia` | PASS | 0.11 |  |
| TC-002 | `TC002ColaYConcurrencia.test_fifo` | PASS | 1.59 |  |
| TC-002 | `TC002ColaYConcurrencia.test_ocho_trabajos_con_limite_tres` | PASS | 6.32 |  |
| TC-003 | `TC003EstadosYTiempos.test_ciclo_de_vida_y_tiempos` | PASS | 0.74 |  |
| TC-003 | `TC003EstadosYTiempos.test_codigo_distinto_de_cero_es_failed` | PASS | 0.33 |  |
| TC-006 | `TC006SalidasSeparadas.test_bytes_que_no_son_texto` | PASS | 0.33 |  |
| TC-006 | `TC006SalidasSeparadas.test_cli_output` | PASS | 0.56 |  |
| TC-006 | `TC006SalidasSeparadas.test_linea_de_200000_caracteres` | PASS | 0.23 |  |
| TC-006 | `TC006SalidasSeparadas.test_salida_visible_mientras_corre` | PASS | 3.29 |  |
| TC-006 | `TC006SalidasSeparadas.test_stdout_y_stderr_no_se_mezclan` | PASS | 0.35 |  |
| TC-006 | `TC006SalidasSeparadas.test_trabajo_que_lee_stdin_no_se_cuelga` | PASS | 0.34 |  |
| TC-004 | `TC004Consultas.test_rnf05_consulta_en_menos_de_un_segundo_con_100_trabajos` | PASS | 2.49 |  |
| TC-004 | `TC004Consultas.test_rnf06_500_registros_sin_perdida_tras_reinicio` | PASS | 10.26 |  |
| TC-004 | `TC004Consultas.test_status_list_y_filtro` | PASS | 0.55 |  |
| TC-013 | `TC013ConfiguracionYSalud.test_configuracion_invalida_no_arranca` | PASS | 1.22 |  |
| TC-013 | `TC013ConfiguracionYSalud.test_configuracion_se_registra_al_arrancar` | PASS | 0.21 |  |
| TC-013 | `TC013ConfiguracionYSalud.test_health` | PASS | 0.98 |  |
| TC-005 | `TC005Cancelacion.test_cancelar_alcanza_a_los_nietos` | PASS | 0.77 |  |
| TC-005 | `TC005Cancelacion.test_cancelar_en_cola` | PASS | 0.45 |  |
| TC-005 | `TC005Cancelacion.test_cancelar_en_ejecucion` | PASS | 0.44 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_cancelar_inmediatamente_despues_de_enviar` | PASS | 0.76 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_caso_a_cancelacion_llega_primero` | PASS | 0.76 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_caso_b_termina_primero` | PASS | 0.34 |  |
| TC-017 | `TC017CancelacionesConcurrentes.test_cinco_cancelaciones_simultaneas` | PASS | 0.45 |  |
| TC-021 | `TC021Escalamiento.test_proceso_que_ignora_sigterm` | PASS | 2.76 |  |
| TC-007 | `TC007Recuperacion.test_kill9_con_trabajos_corriendo_y_en_cola` | PASS | 1.79 |  |
| TC-007 | `TC007Recuperacion.test_nieto_huerfano_con_lider_muerto` | PASS | 0.84 |  |
| TC-007 | `TC007Recuperacion.test_pid_reutilizado_no_se_mata` | PASS | 0.97 |  |
| TC-022 | `TC022RecuperacionCapacidad.test_bajar_max_queue_con_pendientes` | PASS | 3.22 |  |
| TC-022 | `TC022RecuperacionCapacidad.test_base_integra_tras_kill9_durante_escrituras` | PASS | 5.12 |  |
| TC-008 | `TC008Aislamiento.test_un_trabajo_que_falla_no_afecta_a_otros` | PASS | 2.36 |  |
| TC-020 | `TC020MuerteInesperada.test_falla_de_captura_no_deja_procesos_ni_descuadra_el_limite` | PASS | 1.96 |  |
| TC-020 | `TC020MuerteInesperada.test_senal_externa_queda_failed_con_diagnostico` | PASS | 2.19 |  |
| TC-024 | `TC024RecursosBajoCarga.test_cuatro_lotes_de_90_sin_fugas` | PASS | 10.25 |  |
| TC-009 | `TC009CierreControlado.test_cierre_con_tiempo_limite` | PASS | 4.86 |  |
| TC-009 | `TC009CierreControlado.test_ctrl_c_hace_el_mismo_cierre_controlado` | PASS | 2.52 |  |
| TC-009 | `TC009CierreControlado.test_durante_el_cierre_no_acepta_nuevos` | PASS | 3.6 |  |
| TC-009 | `TC009CierreControlado.test_puerto_ocupado` | PASS | 0.47 |  |
| TC-009 | `TC009CierreControlado.test_sigterm_con_servicio_ocioso` | PASS | 0.27 |  |
| TC-012 | `TC012Protocolo.test_mensaje_byte_a_byte_y_varias_solicitudes_por_conexion` | PASS | 0.31 |  |
| TC-012 | `TC012Protocolo.test_mensajes_invalidos_reciben_error_y_no_tumban_el_servicio` | PASS | 0.21 |  |
| TC-019 | `TC019Desconexion.test_desconexion_a_medio_mensaje_no_tiene_efecto` | PASS | 0.81 |  |
| TC-019 | `TC019Desconexion.test_desconexion_tras_mensaje_completo_la_operacion_queda_aceptada` | PASS | 0.81 |  |
| TC-019 | `TC019Desconexion.test_reintento_con_folio_recupera_el_id` | PASS | 0.72 |  |
| TC-023 | `TC023CompatibilidadProtocolo.test_version_incompatible_se_rechaza_explicitamente` | PASS | 0.21 |  |
| TC-016 | `TC016Saturacion.test_carrera_diez_envios_con_un_lugar` | PASS | 0.47 |  |
| TC-016 | `TC016Saturacion.test_rechazo_explicito_secuencial` | PASS | 0.48 |  |
| TC-018 | `TC018Duplicados.test_a_reintento_mismo_folio_mismo_comando` | PASS | 0.33 |  |
| TC-018 | `TC018Duplicados.test_b_sin_folio_cada_envio_es_nuevo` | PASS | 0.23 |  |
| TC-018 | `TC018Duplicados.test_c_mismo_folio_otro_comando_es_conflicto` | PASS | 0.35 |  |
| TC-018 | `TC018Duplicados.test_cli_request_id` | PASS | 0.62 |  |
| TC-018 | `TC018Duplicados.test_d_seis_envios_simultaneos_mismo_folio` | PASS | 0.34 |  |

## Archivos de esta carpeta

- `salida_pruebas.txt`: salida completa de la ejecución.
- `resultados.json`: los mismos resultados en formato máquina.
- `servicios.tar.gz`: por cada servicio que levantó cada prueba, su `data/jobrunner.log` (bitácora), `data/jobs.db` (base), `data/output/` (salidas) y `servicio_salida.txt` (lo que imprimió el servicio). Se abre con `tar xzf servicios.tar.gz`.
- `version.txt`, `entorno.txt`, `configuracion.txt`, `comando.txt`.
