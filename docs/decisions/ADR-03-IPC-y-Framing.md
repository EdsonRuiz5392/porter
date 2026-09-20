# ADR-03: Arquitectura de Comunicación IPC, Red y Framing de Protocolo

## 1. Contexto y Requisitos Satisfechos
El proyecto Porter (JobRunner) requiere separar la interfaz de línea de comandos (CLI) del motor de ejecución (Daemon) para gestionar trabajos en segundo plano (RF-04). Además, debe soportar en el futuro comunicaciones remotas en LAN/VPN (RF-18, RF-20) y garantizar la integridad de los mensajes evitando lecturas parciales o fragmentación TCP (RF-21, RNF-13). 

## 2. Decisión
Para el módulo `src/network/`, se adopta la siguiente arquitectura de comunicación:
1. **Transporte Unificado (TCP/IP):** Tanto la CLI local como los futuros clientes remotos se comunicarán vía sockets TCP asíncronos (`asyncio`). Por defecto, el daemon escuchará estrictamente en 127.0.0.1 (loopback) para cumplir con el avance local, dejando la apertura a interfaces LAN controlada por futuras Listas de Control de Acceso (ACL).
2. **Protocolo con Framing Explícito (Length-Prefixed):** Para evitar el problema de la "mezcla de flujos" (TCP stream fragmentation), cada mensaje enviado sobre el socket tendrá dos partes:
   - Header (4 bytes): Un entero sin signo (Big-Endian) que indica el tamaño exacto del cuerpo del mensaje.
   - Payload (JSON): Un string codificado en UTF-8 conteniendo los datos estructurados.

## 3. Consecuencias
* Positivas: El daemon sabrá exactamente cuántos bytes leer, aislando por completo fallos de lectura parcial y protegiendo al servicio de bloqueos por tramas incompletas (TC-012). Es escalable directamente a la red remota.
* Negativas / Riesgos: Agrega una ligera sobrecarga computacional al empaquetar y desempaquetar el header binario en cada petición.
