# ADR-01: Selección de Lenguaje de Programación y Modelo de Concurrencia

* **Estatus:** Propuesto / En discusión[cite: 1]
* **Contexto:** Se requiere elegir el lenguaje y el mecanismo para ejecutar trabajos en procesos separados sin bloquear la atención de peticiones (`RF-04`)[cite: 1].
* **Alternativas Consideradas:**
  1. C (Uso de `fork()`, `execvp()` y POSIX Signals/IPC)[cite: 1].
  2. Go (Goroutines, subprocesos `os/exec` y canales)[cite: 1].
* **Decisión Seleccionada:** [Pendiente de ratificación por el equipo]
* **Consecuencias:** [Por documentar]
