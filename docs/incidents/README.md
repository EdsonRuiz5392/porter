# Incidentes técnicos

Cada incidente registra síntomas, evidencia, hipótesis, causa, corrección y prueba de regresión (doc 04).

| ID | Título | Estado | Issues |
|---|---|---|---|
| [INC-001](INC-001-trabajos-fantasma-cola-llena.md) | La cola llena con envíos simultáneos crea trabajos fantasma | Cerrado | #35, #36 |

## Defectos abiertos en observación

Aparecieron de forma intermitente y aún no tienen corrección. Se registran como issues.

| Issue | Síntoma | Dónde se observó |
|---|---|---|
| #58 | Trabajos válidos terminan `FAILED -1` con `database is locked` | Kali en WSL2, con carga |
| #59 | `health` reporta 0 y 0 con un trabajo en tránsito, y TC-022 lee un `QUEUED` transitorio | Kali en WSL2 |
