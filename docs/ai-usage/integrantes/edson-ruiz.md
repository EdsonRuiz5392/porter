# Registro de uso de IA — Edson Ruiz

**Autor:** Edson Ruiz
**Modalidad:** En conversación continua a lo largo del Avance.
**Herramienta:** Claude (Claude Code).
**Área:** Verificación y trazabilidad · **Avances:** 1 y 2

## Usos de la IA

- **Aprendizaje de Git y GitHub:** La utilicé como guía para entender y practicar el flujo issue → rama → commit → pull request, y para resolver problemas concretos (clon de un repositorio vacío, ramas atrasadas respecto a `main`, autenticación con `gh`).
- **Entorno de trabajo:** Apoyo para preparar la máquina virtual de Linux y el entorno virtual de Python donde ejecuto las pruebas.
- **Análisis de los documentos del cliente:** La usé para contrastar el estado del repositorio contra los requisitos (RF/RNF), los estándares de repositorio y el plan de verificación, y detectar faltantes.
- **Artefactos de verificación:** La IA redactó los borradores del plan de verificación, la matriz de trazabilidad, los casos de prueba, la prueba de contratos y el script de verificación. Yo los revisé, los ejecuté en mi máquina virtual y los subí desde mis ramas mediante pull requests.
- **Documentación:** Redacción del README, el cronograma y las minutas a partir del historial del repositorio y de la evidencia de las juntas. Esos commits llevan la coautoría de la herramienta declarada en el mensaje.

## Ejemplos representativos

| Tipo | Qué pedí | Qué hice con el resultado |
|---|---|---|
| **Aceptado** | Una prueba que compruebe que cada módulo cumple su contrato de interfaz | La ejecuté en mi entorno: 53 de 56 comprobaciones pasaron y las 3 que fallaron correspondían a un defecto real (issue #15). Evidencia en `verif/results/20260929-1508-2cedea0/` |
| **Modificado** | La matriz de trazabilidad completa | El primer borrador se basaba en una estructura anterior del proyecto; se ajustó a los dueños de `roles-matrix.md` y a los ADR actuales, y RNF-01 y RNF-03 regresaron a "Pendiente" por no tener una corrida registrada |
| **Rechazado** | Una estructura de carpetas para el repositorio | Proponía `docs/adr/`, `docs/minutas/` y `tests/`, que no coinciden con la estructura mínima del documento de estándares (`docs/decisions/`, `verif/`, `project-management/`). Se descartó y se conservó la estructura del estándar |

El uso de IA fue un apoyo para aprender, redactar y revisar más rápido. Los resultados se aceptaron después de ejecutarlos o contrastarlos contra los documentos del cliente, y soy responsable de comprender y defender lo que entregué.

---

## Declaración de uso de IA — Avance 02

Durante el Avance 02 del proyecto Porter usé una herramienta de IA: Claude (Anthropic), en Claude Code.

Verificación: la usé para auditar el repositorio contra los requisitos y para preparar pruebas de robustez que reprodujeran fallas del servicio: saturación de la cola, cancelación, procesos huérfanos, duplicados y reinicios. También me ayudó a interpretar los resultados de las corridas y a investigar las fallas intermitentes.

Git, GitHub y entorno: me guió para configurar el GitHub Project del equipo, instalar Kali Linux en WSL2, autenticarme con `gh`, crear mi rama desde el issue #48 y abrir mi pull request. Ejecuté yo mismo las corridas de línea base y final, y sus commits son míos.

Documentación: redactó el borrador de la documentación de este avance (README, guías, casos TC, incidente, matriz, cronograma y riesgos) a partir del código, los resultados y el historial del repositorio. Yo la revisé y la subí desde mi rama, con mis propios commits.

No escribí código de `src/` con esta herramienta. Las decisiones técnicas del proyecto las tomó el equipo, y soy responsable de comprender y defender lo que entregué.

| Tipo | Qué pedí | Qué hice con el resultado |
|---|---|---|
| **Aceptado** | Probar el servicio bajo las condiciones que pide la Technical Review 2 | Repetí las corridas por mi cuenta. La línea base dio 23 de 57 y quedó como evidencia en `verif/results/2026-10-21_avance01-linea-base_bc113057/` |
| **Modificado** | Interpretar una falla de TC-022 en Kali | Se leyó primero como un posible estado imposible. Al repetir el escenario, el `QUEUED` desapareció 3 segundos después, así que se corrigió el diagnóstico a una lectura transitoria (#59) |
| **Rechazado** | Una ruta de trabajo de 33 pasos con ADR y responsables propuestos | No se siguió tal cual, porque el equipo adoptó su propio flujo de PR y su numeración de ADR |
