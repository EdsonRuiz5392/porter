# Matriz de Trazabilidad — JobRunner (Hito 1)

Este documento mantiene la trazabilidad obligatoria entre los requisitos funcionales, los métodos de verificación, los casos de prueba asignados, los estados de ejecución y la evidencia asociada.

## Matriz de Requisitos del Sistema

| Req ID | Descripción Breve | Prioridad | Método | Caso(s) | Evidencia | Resultado | Defecto / Excepción |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RF-01** | Enviar trabajo e ID único | Alta | Prueba | TC-001 | Log de CLI + SQLite | Pendiente | — |
| **RF-02** | Validar solicitudes vacías o inválidas | Alta | Prueba | TC-001 | Mensaje de error útil | Pendiente | — |
| **RF-03** | Mantener cola sin capacidad inmediata | Alta | Prueba | TC-002 | Orden en cola | Pendiente | — |
| **RF-04** | Ejecutar en procesos separados | Alta | Prueba | TC-002 | PIDs independientes (`ps`) | Pendiente | — |
| **RF-05** | Respetar límite de concurrencia | Alta | Prueba | TC-002 | Concurrencia acotada | Pendiente | — |
| **RF-06** | Representar estados del ciclo de vida | Alta | Inspección | TC-003 | Estado en BD | Pendiente | — |
| **RF-07** | Registrar tiempos y códigos de salida | Alta | Prueba | TC-003, TC-006 | Metadatos completos | Pendiente | — |
| **RF-08** | Consultar estado y metadatos por ID | Alta | Prueba | TC-004 | Salida CLI `status` | Pendiente | — |
| **RF-09** | Listar trabajos registrados | Media | Prueba | TC-004 | Salida CLI `list` | Pendiente | — |
| **RF-10** | Solicitar cancelación en cola o ejecución | Alta | Prueba | TC-005 | Señal `SIGTERM` | Pendiente | — |
| **RF-11** | Capturar stdout y stderr | Alta | Prueba | TC-006 | Archivos de salida | Pendiente | — |
| **RF-12** | Conservar metadatos tras reinicio | Crítica | Prueba | TC-007 | Persistencia `porter.db` | Pendiente | — |
| **RF-13** | Recuperar historial al arrancar | Crítica | Prueba | TC-007 | Estado post-reinicio | Pendiente | — |
| **RNF-01**| Ejecución en Linux | Crítica | Análisis | TC-014 | Entorno Linux Mint | PASS | — |
| **RNF-02**| Construcción reproducible desde clon | Alta | Prueba | TC-014 | `README.md` / clon limpio | Pendiente | — |
| **RNF-03**| Operación sin privilegios de root | Alta | Análisis | TC-014 | Usuario estándar | PASS | — |
| **RNF-08**| Aislamiento ante fallos | Crítica | Prueba | TC-008 | Estabilidad del servicio | Pendiente | — |

## Casos de Prueba Asociados (TC-XXX)
* **TC-001:** Envío de un comando válido y rechazo de entradas vacías (RF-01, RF-02).
* **TC-002:** Verificación de cola y respeto al límite de concurrencia (RF-03, RF-04, RF-05).
* **TC-003:** Transición correcta de estados y registro de tiempos (RF-06, RF-07).
* **TC-004:** Consultas individuales por ID y listado general (RF-08, RF-09).
* **TC-010 / TC-011:** Infraestructura y pruebas preliminares del sistema base.
