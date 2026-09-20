	# Registro de Uso de Herramientas de Inteligencia Artificial

Este documento recopila ejemplos representativos del uso de IA durante el desarrollo del Hito 0 e Hito 1 de JobRunner, cumpliendo con los estándares de responsabilidad técnica.

## 1. Resultado Aceptado
* **Objetivo:** Diseñar la estructura inicial del parser de argumentos y subcomandos con `argparse` en Python para `src/porter.py`.
* **Resultado Recibido:** Un bloque de código base utilizando `add_subparsers()` para los comandos `submit`, `status`, `list` y `cancel`.
* **Revisión Realizada:** Se analizó el código línea por línea, verificando que manejara correctamente los argumentos posicionales y opcionales.
* **Cambios Aplicados:** Ninguno significativo; el diseño estructurado cumplía directamente con los requerimientos de la interfaz de línea de comandos (CLI).
* **Prueba Agregada:** Ejecución manual del comando de ayuda (`python3 src/porter.py --help`).
* **Aprendizaje:** Permitió acelerar la configuración inicial del CLI manteniendo la legibilidad.

## 2. Resultado Modificado
* **Objetivo:** Implementar la captura del estado de un proceso en ejecución mediante su PID utilizando subprocesos.
* **Resultado Recibido:** Una propuesta de la IA que utilizaba comandos del sistema operativo directamente concatenados sin validar excepciones de procesos huérfanos.
* **Revisión Realizada:** Se detectó que el código fallaba si el PID ya no existía en el sistema (`ProcessLookupError`).
* **Cambios Aplicados:** Se modificó la lógica para envolver la consulta en bloques `try-except` robustos y utilizar `os.kill()` de manera controlada.
* **Prueba Agregada:** Caso de prueba enviando un trabajo que termina rápido y consultando su estado posterior.
* **Aprendizaje:** La IA proporciona bases útiles, pero el manejo de señales y excepciones a nivel de sistema operativo requiere validación humana estricta.

## 3. Resultado Rechazado
* **Objetivo:** Proponer una arquitectura de red basada en sockets asíncronos con librerías externas avanzadas para el Hito 3.
* **Resultado Recibido:** Un script completo que dependía de frameworks de terceros muy pesados no permitidos por la restricción de portabilidad limpia.
* **Revisión Realizada:** Se evaluó contra el estándar del proyecto y se determinó que violaba la simplicidad requerida y las restricciones de dependencias del entorno Linux.
* **Motivo Técnico del Rechazo:** Introducía complejidad innecesaria y dependencias externas no justificadas para la primera etapa del proyecto.
* **Acción Tomada:** Se descartó el enfoque y se decidió optar por bibliotecas nativas de Python (`socket` / `asyncio`) para mantener la reproducibilidad.
