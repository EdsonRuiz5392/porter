# Cronograma Inicial e Hitos

* **Hito 0:** Inicio y línea base (Estructura, roles e Issues)[cite: 1].
* **Hito 1 (Avance 1):** Núcleo local (función `porter` local, cola, subprocesos y captura stdout/stderr)[cite: 1].
* **Hito 2:** Concurrencia, límites, cancelación, persistencia y recuperación[cite: 1].
* **Hito 3:** Operación remota privada por red LAN/VPN y restricción de acceso[cite: 1].
* **Hito 4:** Candidato de entrega, automatización y pruebas cruzadas[cite: 1].
* **Hito 5:** Aceptación final y defensa individual[cite: 1].

# Registro de Riesgos Iniciales

| ID | Riesgo / Dependencia | Impacto | Mitigación |
| :--- | :--- | :--- | :--- |
| **R-01** | Condiciones de carrera al actualizar estado del trabajo bajo solicitudes concurrentes (`RF-26`)[cite: 1]. | Alto | Definir modelo de sincronización estricto en ADR-01[cite: 1]. |
| **R-02** | Corrupción de persistencia ante cierres inesperados del servicio (`RNF-28`)[cite: 1]. | Crítico | Implementar escrituras atómicas y validar estado en el arranque (`RF-13`)[cite: 1]. |
| **R-03** | Exposición indebida en interfaces de red públicas (`RNF-12`, `RNF-13`)[cite: 1]. | Crítico | Restringir bind a localhost / IP de LAN autorizada (`RF-20`)[cite: 1]. |
| **D-01** | Dependencia de entorno de red privada para pruebas de cliente remoto[cite: 1]. | Medio | Configurar interfaces de red virtuales o VPN local para pruebas[cite: 1]. |
