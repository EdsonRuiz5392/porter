# Registro de uso de IA — Edson Ruiz

**Autor:** Edson Ruiz
**Modalidad:** En conversación continua a lo largo del Avance.
**Herramienta:** Claude (Claude Code).
**Área:** Verificación y trazabilidad · **Avance:** 1

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
