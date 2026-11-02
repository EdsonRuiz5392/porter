# Hitos y registro de riesgos

**Última actualización:** 2 de noviembre de 2026.

## Hitos

| Hito | Contenido | Estado |
|---|---|---|
| Hito 0 | Inicio y línea base: estructura, roles e issues | Cerrado |
| Hito 1 (Avance 01) | Núcleo local: cola, subprocesos y captura de stdout y stderr | Cerrado |
| Hito 2 (Avance 02) | Concurrencia, límites, cancelación, persistencia y recuperación | En revisión |
| Hito 3 | Operación remota privada en LAN o VPN y restricción de acceso | Pendiente |
| Hito 4 | Candidato de entrega, automatización y pruebas cruzadas | Pendiente |
| Hito 5 | Aceptación final y defensa individual | Pendiente |

## Registro de riesgos

| ID | Riesgo | Impacto | Estado | Responsable | Mitigación |
|---|---|---|---|---|---|
| R-01 | Carreras al actualizar el estado con solicitudes concurrentes (RF-26, RNF-27) | Alto | Mitigado | Dylan | Candado de admisión (ADR-006) y un único escritor del estado final (ADR-008). TC-016 y TC-017 |
| R-02 | Corrupción de la base ante cierres inesperados (RNF-28) | Crítico | Mitigado | Ángel | SQLite en modo WAL con transacciones y recuperación al arrancar (ADR-003, ADR-010). TC-022 |
| R-03 | Exposición en interfaces públicas (RNF-12, RNF-13) | Crítico | Abierto, Hito 3 | Juan | Por defecto escucha en `127.0.0.1`. `allowed_networks` todavía no se aplica (RF-20) |
| R-04 | Procesos huérfanos tras una caída (RNF-30) | Crítico | Mitigado | Marcos | Grupo de procesos por trabajo y limpieza con verificación de identidad al arrancar (ADR-008, ADR-010). TC-007 |
| R-05 | Cierre que no termina (RF-15) | Alto | Mitigado | Ángel | `JOBRUNNER_SHUTDOWN_TIMEOUT` y escalamiento (ADR-011). TC-009 |
| R-06 | `database is locked` bajo carga convierte un trabajo válido en `FAILED -1` y hace fallar las pruebas de RNF-06 y RNF-33 | Alto | **Abierto** (#58) | Ángel | Reproducir bajo carga, confirmar la causa y agregar una prueba de regresión. No se observó en Ubuntu 24.04 |
| R-07 | `health` no cuenta los trabajos en tránsito y puede reportar 0 y 0; provoca una falla intermitente de TC-022 | Medio | **Abierto** (#59) | Ángel | El trabajo no se pierde: termina poco después. Hay que decidir si `health` cuenta los trabajos en tránsito o si la prueba espera a que terminen |
| R-08 | Un proceso que se sale de su grupo (`setsid`) queda sin control | Medio | Aceptado | Marcos | Límite documentado (ADR-008). Las alternativas requieren privilegios o complejidad fuera de alcance |
| R-09 | `output` de varios MB excede `MAX_MESSAGE_BYTES` | Bajo | Aceptado | Dylan | Límite documentado (ADR-009). Mejora futura: paginar o truncar |
| R-10 | El disco se llena porque no hay borrado automático | Bajo | Aceptado | Ángel | Limpieza manual documentada (ADR-012) |
| R-11 | Procesos del equipo: PR mezclados sin todas las aprobaciones y commits directos a `main` | Alto | **Abierto** | Todos | Aplicar el flujo del profesor en todos los PR: 4 aprobaciones visibles antes del merge y nada directo a `main` |
| R-12 | Defensa individual: cada integrante debe poder explicar los archivos que subió | Alto | **Abierto** | Todos | Ensayo con los casos TC de cada área y lectura de su módulo antes de la revisión |
| R-13 | Documentación que se atrasa respecto al código | Medio | Mitigado | Edson | Actualización del Avance 02. Revisar la documentación en cada PR que cambie un contrato |
| D-01 | Dependencia de una red privada para probar el cliente remoto | Medio | Abierto, Hito 3 | Juan | Interfaces virtuales o VPN local para las pruebas |
