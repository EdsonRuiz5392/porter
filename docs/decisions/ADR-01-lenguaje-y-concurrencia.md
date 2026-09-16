# ADR-01: Selección de Lenguaje de Programación y Modelo de Concurrencia

* **Estatus:** Aprobado / Decidido
* **Fecha:** 2026-09-15
* **Contexto:** Se requiere definir el lenguaje base y el mecanismo para ejecutar trabajos en procesos separados sin bloquear la atención de peticiones CLI ni la interfaz de red.

## Alternativas Consideradas
1. **C:** Alto rendimiento y control nativo POSIX (, ), pero mayor complejidad de desarrollo y manejo de memoria.
2. **Go:** Excelente manejo de concurrencia nativa (goroutines) y compilación a binario estático.
3. **Python (Seleccionado):** Alta velocidad de desarrollo, bibliotecas estándar maduras para gestión de subprocesos (`subprocess`), sockets, manejo de señales POSIX (`signal`) y facilidad de colaboración entre los 5 integrantes.

## Decisión Seleccionada
Se elige **Python 3** como el lenguaje oficial del proyecto **Porter**. 
La concurrencia local se gestionará mediante el módulo `subprocess` para la ejecución asíncrona de comandos y `asyncio` / `threading` para la gestión del servicio y comunicaciones IPC.

## Consecuencias
* **Positivas:** Desarrollo ágil, código legible para los 5 integrantes y portabilidad directa en sistemas Linux.
* **Negativas / Mitigación:** Menor velocidad de ejecución bruta en comparación con C/Go, lo cual es despreciable ya que la carga principal recae en los subprocesos que ejecute el sistema operativo.
