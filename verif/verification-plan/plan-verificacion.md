# Plan de Verificación, Validación y Aceptación — Porter

**Responsable:** Edson Ruiz (líder de verificación) · **Aprueba:** Dylan (responsable de producto)
**Versión:** 0.1 (borrador del Avance 01) · **Fecha:** 2026-09-21
**Base:** doc 05 (Plan de verificación del cliente), doc 04 (Estándares), doc 06 (Hitos).
**Matriz asociada:** [traceability-matrix.md](traceability-matrix.md)

## 1. Propósito

Demostrar, con evidencia objetiva y reproducible, que Porter cumple los requisitos RF-01 a RF-30 y RNF-01 a RNF-34 y que resuelve las necesidades del usuario.

Toda verificación sigue la cadena del doc 05:

**Requisito → Método → Caso → Resultado esperado → Evidencia → PASS/FAIL**

Una demostración manual, o un reporte generado por IA, no sustituye una prueba reproducible.

## 2. Responsabilidades

| Rol | Quién | Qué hace |
|---|---|---|
| Líder de verificación | Edson | Mantiene este plan y la matriz; diseña los casos TC; mantiene el script de verificación; registra la evidencia |
| Autor de cada módulo | Dylan (`src/cli`), Juan (`src/network`), Ángel (`src/db`), Marcos (`src/core`) | Implementa su módulo con pruebas unitarias y corre los casos de su área |
| Revisor distinto del autor | Según `project-management/roles-matrix.md` | Confirma los resultados críticos del área que revisa |
| Responsable de producto | Dylan | Decide la aceptación y aprueba las excepciones |

## 3. Métodos de verificación

| Método | Cuándo se usa | Ejemplo en Porter |
|---|---|---|
| **Prueba** | Se ejecuta el sistema con entradas controladas y se compara con el resultado esperado | Enviar `false` y comprobar que el código de salida registrado es 1 |
| **Análisis** | Se revisa código, arquitectura o datos para demostrar una propiedad | Revisar que la escritura en la base de datos sea atómica |
| **Inspección** | Se comprueban directamente archivos, configuración o estructura | Verificar que `src/` esté dividido en módulos |
| **Demostración** | Se muestra una operación ante el cliente | El flujo local completo en la RT-1. Complementa, no reemplaza, a la prueba |

## 4. Niveles de prueba

| Nivel | Qué cubre | Dónde vive | Primer hito |
|---|---|---|---|
| Unitarias | Funciones y módulos aislados | Pruebas de cada módulo | H1 |
| Integración | Procesos, IPC, persistencia y red | `verif/scripts/` | H1 |
| Sistema | Flujo completo del cliente al servicio | Casos TC | H1 |
| Robustez | Fallos, límites y desconexiones | TC-008, TC-016 a TC-022 | H1 y H2 |
| Seguridad | Exposición, validación y autorización de red | TC-011, TC-012 | H3 |
| Aceptación | Escenarios de usuario sobre una versión candidata | Escenarios A a E (sección 11) | H4 |

## 5. Formato de los casos TC

Cada caso vive en `verif/test-cases/TC-XXX.md` y contiene, como pide el doc 05:

1. Identificador y título
2. Requisitos cubiertos
3. Objetivo
4. Precondiciones
5. Entorno y configuración
6. Datos de entrada
7. Pasos reproducibles
8. Resultado esperado
9. Resultado observado
10. Artefactos de evidencia
11. Estado: PASS, FAIL o BLOCKED
12. Responsable y versión probada (commit o etiqueta)

Los datos de entrada controlados van en `verif/test-data/`.

## 6. Entorno controlado

Entorno de referencia propuesto (**pendiente de que el equipo lo confirme**):

| Elemento | Valor |
|---|---|
| Distribución | Ubuntu 24.04.4 LTS |
| Arquitectura | x86_64 |
| Plataforma | VM Multipass `sisav`, sin privilegios de root |
| Python | 3.12.3 |
| SQLite | 3.45.1 |
| Límite de concurrencia | 3 (valor de RNF-04) |
| Interfaz y puerto | 127.0.0.1, puerto por definir (ADR-03) |
| Topología LAN/VPN | Por definir en el Hito 3 |

Cada corrida registra además el **commit** probado y la configuración usada. Si un integrante usa otra distribución, sus resultados sirven como apoyo, pero la evidencia formal se toma en el entorno de referencia (RNF-01 exige *una* distribución declarada).

**Herramienta de pruebas (decisión pendiente):** se propone `python3 -m unittest`, que viene con Python y no requiere instalar nada, lo que favorece la construcción desde un clon limpio (RNF-02). Si el equipo prefiere `pytest`, hay que declararlo con su versión en un archivo de dependencias, porque hoy no está instalado en el entorno de referencia.

## 7. Criterios de entrada y de salida

**Para iniciar una verificación formal** (doc 05): el código está integrado en una versión candidata; la construcción es limpia; los requisitos están en línea base; los casos fueron revisados; el entorno está disponible; y los defectos críticos previos están cerrados o aceptados formalmente.

**Para dar por terminada la verificación final** (doc 05):

- 100 % de los RF y RNF obligatorios trazados en la matriz.
- 100 % de los casos críticos en PASS.
- Ningún defecto bloqueante o crítico abierto.
- Evidencia completa.
- Instalación reproducida por un tercero.
- Validación remota en LAN o VPN.
- Acta de aceptación o lista explícita de excepciones.

## 8. Evidencia

**Evidencia aceptable** (doc 05): salidas de scripts, bitácoras, archivos de resultados, capturas cuando aporten contexto, mediciones, configuración y hash del commit. Toda evidencia identifica el caso, la fecha, el entorno y la versión.

**Dónde se guarda** (doc 04): cada ejecución formal en `verif/results/<run-id>/`, con:

- versión o commit
- entorno
- configuración
- comando ejecutado
- resultados
- bitácoras
- resumen PASS/FAIL

**Convención de `run-id`:** `AAAAMMDD-HHMM-<commit de 7 caracteres>`, por ejemplo `20260930-1815-a7c717e`.

Los resultados **no se editan** para ocultar fallas (doc 04).

## 9. Gestión de defectos

- Todo **FAIL** genera un issue de defecto con severidad, pasos, resultado esperado, resultado observado y evidencia (doc 05).
- **Severidades:** Bloqueante (impide probar o demostrar), Crítica (incumple un requisito crítico o de seguridad), Mayor (incumple un requisito con solución alternativa) y Menor (cosmética o de documentación).
- Después de corregir, se repite el caso y las pruebas de regresión afectadas.
- Una **excepción** requiere impacto, riesgo residual, responsable y aprobación del responsable de producto.
- El issue de defecto se liga al requisito en la columna "Defecto/Excepción" de la matriz.

## 10. Verificación por hito

| Hito | Casos que se verifican | Además |
|---|---|---|
| **H1 · Avance 01 (RT-1, 6 oct)** | TC-001, TC-002 (parcial), TC-003, TC-004, TC-005, TC-006, TC-008, TC-014, TC-015. Recomendados: TC-020 y TC-021 | Pruebas unitarias; script de verificación con un solo comando (RNF-20); primera corrida registrada sobre la versión etiquetada |
| H2 · Concurrencia y persistencia | TC-002 (completo), TC-007, TC-009, TC-013, TC-016, TC-017, TC-018, TC-020, TC-021, TC-022, TC-025, TC-026, TC-027 | Incidente de concurrencia, persistencia o procesos con su prueba de regresión (doc 06) |
| H3 · Operación remota | TC-010, TC-011, TC-012, TC-019, TC-023 | Conexión permitida y conexión rechazada (doc 01) |
| H4 · Candidato de entrega | TC-024 y regresión completa | Verificación cruzada con otro equipo; instalación desde clon limpio por un tercero |
| H5 · Aceptación | Matriz completa en PASS/FAIL | Requisito elegido al azar trazado de punta a punta |

## 11. Validación con usuarios

Escenarios del doc 05, que el usuario completa sin ayuda sustantiva:

| Escenario | Qué hace el usuario | Hito |
|---|---|---|
| A | Instalar e iniciar siguiendo la documentación | H4 |
| B | Enviar un trabajo, consultarlo y recuperar su salida | H4 |
| C | Cancelar un trabajo largo | H4 |
| D | Operar desde otro equipo en la LAN o la VPN | H4 |
| E | Diagnosticar una entrada inválida | H4 |

## 12. Decisión de aceptación

| Resultado | Condición (doc 05) |
|---|---|
| ACEPTADO | Se cumplen los criterios de salida |
| ACEPTADO CON EXCEPCIONES | Solo quedan defectos no críticos, con riesgo y fecha acordados |
| RECHAZADO | Falta trazabilidad, evidencia, seguridad de red o reproducibilidad, o existe un defecto crítico |

## 13. Verificación independiente y cruzada

- Una parte de la verificación la diseña o ejecuta un integrante distinto del autor. El líder de verificación diseña los casos, y el revisor de cada área confirma los resultados críticos.
- En la fase de candidato, otro equipo actuará como verificador y entregará defectos reproducibles ligados a requisitos (doc 05 y doc 06, Hito 4).

## 14. Incidente no anunciado

En una revisión técnica, el cliente puede introducir una falla sin aviso (doc 05). El equipo responde así:

1. Recopilar evidencia **antes** de modificar el sistema.
2. Formular y contrastar hipótesis.
3. Reducir el problema a un caso reproducible.
4. Decidir y justificar si se corrige, se mitiga o se acepta el riesgo.
5. Agregar una prueba de regresión y registrar el incidente en `docs/incidents/`.

## 15. Evidencia generada con IA

Una explicación, prueba o reporte producido por IA no es evidencia suficiente sin una ejecución reproducible y revisión humana (doc 05). Toda prueba sugerida por IA se ejecuta en el entorno de referencia, se revisa y se registra en `docs/ai-usage/` antes de contar como evidencia.

## 16. Decisiones pendientes de este plan

| Decisión | Propuesta | Responsable |
|---|---|---|
| Distribución de referencia | Ubuntu 24.04 LTS | Equipo |
| Herramienta de pruebas | `python3 -m unittest` | Edson con Dylan |
| Analizador estático para RNF-19 | Por definir | Edson con Dylan |
| Casos propuestos TC-025, TC-026 y TC-027 | Aceptarlos en la matriz | Dylan (producto) |
