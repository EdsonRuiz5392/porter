# Cronograma y actividad del proyecto — Porter

Registro de lo que ha ocurrido en el proyecto: juntas, commits, pull requests e issues, en orden de fecha. Complementa a `schedule-and-risks.md` (hitos y riesgos) y a las minutas de [`minutas/`](minutas/).

**Última actualización:** 1 de octubre de 2026 · **Fuente:** historial de Git de `main` e información de GitHub (PR e issues). Las fechas son hora local (UTC−6).

## Fechas clave

| Fecha | Evento |
|---|---|
| 11 de septiembre de 2026 | Entrega del Avance 00: formación de equipo y repositorio |
| 16 de septiembre | Junta 1 |
| 21 de septiembre | Junta 2 |
| 28 de septiembre | Junta 3 |
| 1 de octubre | Junta 4 |
| 5 de octubre | El repositorio debe estar público (24 horas antes de la presentación) |
| **6 de octubre** | **Technical Review 1 — Avance 01 (núcleo local), presencial** |
| 8 de octubre | Fin de la ventana pública del Avance 01 (48 horas después) |

## Juntas

| # | Fecha | Tema | Minuta |
|---|---|---|---|
| 1 | Miércoles 16 de septiembre | Roles del equipo y cierre del Avance 00 | [minuta](minutas/2026-09-16-junta-1.md) |
| 2 | Lunes 21 de septiembre | Pruebas, contexto de las IA de cada integrante, roles y próximos eventos | [minuta](minutas/2026-09-21-junta-2.md) |
| 3 | Lunes 28 de septiembre | Roles por módulo, issues, documentación y pruebas con scripts | [minuta](minutas/2026-09-28-junta-3.md) |
| 4 | Jueves 1 de octubre | Actualización de documentación, últimos detalles y presentación | [minuta](minutas/2026-10-01-junta-4.md) |

## Línea de tiempo

### Semana del 31 de agosto al 6 de septiembre — arranque

| Fecha | Qué pasó | Quién | Referencia |
|---|---|---|---|
| 6 sep | Primera versión del repositorio: estructura de carpetas, README y matriz de roles | Dylan | `caa0822`, `faf8d3c` |
| 6 sep | Se abren los issues #1 a #7 (arranque, documentación, ADR, verificación y Avance 1) | Dylan | #1–#7 |

### Semana del 7 al 13 de septiembre — Avance 00

| Fecha | Qué pasó | Quién | Referencia |
|---|---|---|---|
| 7 sep | Corrección del correo institucional en la matriz de roles | Ángel | `af1f83d` |
| 7 sep | Plantilla de issues y `.gitattributes` (en rama propia) | Edson | `e0f3d44` |
| 8 sep | Actualización del estado del proyecto en el README | Juan | `2240076` |
| 10 sep | Actualización del README | Marcos | `6196bdb` |
| 11 sep | **Entrega del Avance 00** | Equipo | — |

### Semana del 14 al 20 de septiembre — primera versión del CLI

| Fecha | Qué pasó | Quién | Referencia |
|---|---|---|---|
| 15 sep | Datos de Marcos corregidos en el README y la matriz de roles; se abre el issue #8 | Dylan | `6dcd3c0`, #8 |
| 15 sep | ADR de lenguaje: Python 3 | Dylan | `7294381` |
| 15 sep | Estructura base del intérprete de comandos | Dylan | `614eae6` |
| 15 sep | Se cierran los issues #1 a #5 y #7 | Dylan | — |
| **16 sep** | **Junta 1** | Equipo | [minuta](minutas/2026-09-16-junta-1.md) |
| 16 sep | Se mezcla el PR #9: plantilla de issues y `.gitattributes` | Edson; mezcla Dylan | PR #9 |
| 16 sep | Prototipo de CLI con `subprocess` y SQLite | Dylan | `56db2c2` |
| 16 sep | Se cierra el issue #8 | Marcos | #8 |
| 19 sep | Registro de uso de IA y primera matriz de trazabilidad | Dylan | `fb10125`, `0d9fb8b` |
| 20 sep | ADR de comunicación (IPC y delimitación de mensajes) | Juan | PR #10 |

### Semana del 21 al 27 de septiembre — arquitectura modular

| Fecha | Qué pasó | Quién | Referencia |
|---|---|---|---|
| **21 sep** | **Junta 2:** se presenta el diagrama de arquitectura del servicio | Equipo | [minuta](minutas/2026-09-21-junta-2.md) |
| 21 sep | Se mezcla el PR #11: plan de verificación; se cierra el issue #6 | Edson; aprueba Dylan | PR #11 |
| 25 sep | Matriz de roles alineada con la arquitectura (módulos, RF y RNF por integrante) | Ángel | `40a7548` |
| 25 sep | Decisiones de arquitectura: concurrencia, IPC, persistencia, protocolo y semántica de cola | Ángel | `106ae92` |
| 27 sep | Roles de proceso (autor, revisor, líder de verificación, responsable de producto) | Ángel | `45dfd62` |
| 27 sep | Se mezcla el PR #12: esqueleto modular de `src/`, contratos de interfaz y guía técnica | Ángel; aprueba Dylan | PR #12 |

### Semana del 28 de septiembre al 4 de octubre — implementación e integración

| Fecha | Qué pasó | Quién | Referencia |
|---|---|---|---|
| **28 sep** | **Junta 3** | Equipo | [minuta](minutas/2026-09-28-junta-3.md) |
| 28 sep | Implementación de `cli.py`, `control.py` y `cola.py` | Dylan | `d374c20` |
| 28 sep | Documento de alcance del Avance 1, función por función | Ángel | `516c7ff` |
| 29 sep | Primera versión de `launcher.py` y ajuste de nombres a la interfaz | Marcos | `2cedea0`, `ca1a56b` |
| 29 sep | Prueba de contratos de interfaz con evidencia (`verif/results/20260929-1508-2cedea0`) | Edson; aprueban Ángel y Dylan | #13, PR #14 |
| 29 sep | Se abre el defecto #15: `launcher` no cumple el contrato | Edson → Marcos | #15 |
| 29 sep | Matriz de trazabilidad completa (64 requisitos); producto resuelve 4 decisiones | Edson; aprueba Ángel | #16, PR #17 |
| 29 sep | Nueve casos de prueba del Avance 01 | Edson | #18, PR #19 |
| 29 sep | Script de verificación con un solo comando | Edson; aprueba Dylan | #20, PR #21 |
| 29 sep | Issues #22 y #23 del núcleo (CLI, cola y control); PR #24 | Dylan | #22, #23, PR #24 |
| 30 sep | Protocolo TCP con delimitación de mensajes y entrada de clientes | Juan | PR #25 |
| 30 sep | Cola de trabajos | Dylan | PR #26 |
| 30 sep | `launcher` pasa a `asyncio` (`start`, `cancel`, `stream_output`) | Marcos | `d84ec9f` |
| 30 sep | `cola.py` con métodos síncronos, según el contrato | Dylan | `517fd11` |
| **1 oct** | **Junta 4:** demostración de persistencia y bitácora; preparación de la presentación | Equipo | [minuta](minutas/2026-10-01-junta-4.md) |
| 1 oct | Se mezcla el PR #27: ajustes de sincronía y contratos en cola y control | Dylan; mezcla Marcos | PR #27, #23 |
| 1 oct | Se cierra el defecto #15 del `launcher`, durante la junta | Marcos | #15 |
| 1 oct | README en dos versiones, cronograma y minutas de las cuatro juntas | Edson | este documento |

## Pull requests

| PR | Título | Autor | Mezclado | Issue |
|---|---|---|---|---|
| #9 | Plantilla de issues y `.gitattributes` | Edson | 16 sep | — |
| #10 | ADR de arquitectura IPC y delimitación de mensajes | Juan | 20 sep | #5 |
| #11 | Plan de verificación | Edson | 21 sep | #6 |
| #12 | Esqueleto inicial y documentación de arquitectura | Ángel | 27 sep | — |
| #14 | Prueba de contratos de interfaz entre módulos | Edson | 29 sep | #13 |
| #17 | Matriz de trazabilidad completa | Edson | 29 sep | #16 |
| #19 | Casos de prueba del Avance 01 | Edson | 29 sep | #18 |
| #21 | Script de verificación con un solo comando | Edson | 29 sep | #20 |
| #24 | Registro de aportación del núcleo (CLI, cola y control) | Dylan | 29 sep | #22, #23 |
| #25 | Protocolo TCP con delimitación de mensajes y entrada | Juan | 30 sep | — |
| #26 | Cola de trabajos | Dylan | 30 sep | — |
| #27 | Ajustes de sincronía y contratos en cola y control | Dylan | 1 oct | #23 |

## Issues

| Issue | Título | Responsable | Abierto | Cerrado |
|---|---|---|---|---|
| #1 | Estructura inicial del repositorio y configuración | Dylan | 6 sep | 15 sep |
| #2 | README, matriz de roles y cronograma inicial | Dylan | 6 sep | 15 sep |
| #3 | ADR de lenguaje y concurrencia | Dylan | 6 sep | 15 sep |
| #4 | ADR de persistencia y recuperación | Ángel | 6 sep | 15 sep |
| #5 | ADR de protocolo de red y delimitación | Juan | 6 sep | 15 sep |
| #6 | Plan de verificación y matriz de trazabilidad | Edson | 6 sep | 21 sep |
| #7 | Implementación inicial de `porter` y ejecutor local | Dylan | 6 sep | 15 sep |
| #8 | Monitoreo de procesos, señales y límites | Marcos | 15 sep | 16 sep |
| #13 | Prueba de contratos de interfaz | Edson | 29 sep | 29 sep |
| #15 | Defecto: `launcher` no implementa el contrato | Marcos | 29 sep | 1 oct |
| #16 | Completar matriz de trazabilidad | Edson | 29 sep | 29 sep |
| #18 | Casos de prueba del Avance 01 | Edson | 29 sep | 29 sep |
| #20 | Script de verificación con un solo comando | Edson | 29 sep | 29 sep |
| #22 | Implementación y validación de `cli.py` | — | 29 sep | 29 sep |
| #23 | Estructura de `cola.py` y lógica de `control.py` | — | 29 sep | 1 oct |

## Lo que sigue hasta la Technical Review 1

Plan propuesto; lo confirma el equipo en la siguiente junta.

| Fecha | Actividad |
|---|---|
| 2–3 de octubre | Subir a `main` persistencia, bitácora y operación; alinear `protocolo` y `entrada` con el contrato; primera prueba de punta a punta |
| 3–4 de octubre | Ejecutar los casos TC-001 a TC-006, TC-008, TC-014 y TC-015 y registrar la evidencia en `verif/results/` |
| 4 de octubre | Etiquetar la versión del avance; ensayo de la presentación desde un clon limpio |
| 5 de octubre | Confirmar que el repositorio está público; segundo ensayo |
| 6 de octubre | Technical Review 1 |
