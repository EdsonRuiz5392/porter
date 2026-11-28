# ADR-014: Límite de clientes, tiempos de espera y ciclo de vida de las conexiones (Python)

- Estado: Aceptado
- Fecha: 2026-11-19
- Requisitos relacionados: RF-15, RF-22, RF-23, RNF-08, RNF-25, RNF-29, RNF-33
- Relación con otros ADR: complementa ADR-001 (una tarea por cliente) y ADR-004 (framing). **Modifica ADR-011** en el orden de arranque y en el cierre de conexiones. La espera del lado del cliente (`JOBRUNNER_TIMEOUT`) se fija en ADR-018 (2026-11-21).

## Contexto y problema
Con el servicio accesible por red aparecen problemas que en localhost no se notaban (defecto 4 del volumen 2 y pruebas del avance 3):

1. **Sin límite de conexiones.** Cada cliente ocupa un descriptor y una tarea. Abrir cientos de conexiones agota los descriptores del proceso, y entonces fallan también los pipes de los trabajos y la base (RNF-29 pide rechazo explícito también para clientes y descriptores).
2. **Sin tiempos de espera.** Un cliente que se conecta y no manda nada, o que manda el encabezado y nunca el cuerpo (*slowloris*), retiene su conexión para siempre. Uno que no lee las respuestas bloquea `drain()` de su tarea.
3. **El cierre no cerraba las conexiones.** En Python 3.12+ `serve_forever` espera a que terminen todas las conexiones, así que un cliente ocioso podía retrasar el apagado.
4. **Arranque (defecto 6 del vol. 2).** El puerto se revisaba con un socket de prueba y se cerraba; si se ocupaba en ese instante, los trabajos recuperados ya se habían lanzado en un servicio que no podría atender a nadie.

## Alternativas consideradas (exceso de clientes)

### Alternativa A: sin límite (avance 2)
- Desventajas/riesgos: el agotamiento de descriptores afecta a los trabajos, no solo a la red.

### Alternativa B: hacer esperar a los clientes de más (semáforo)
- Ventajas: nadie recibe error.
- Desventajas/riesgos: la espera no tiene límite claro y la conexión ya ocupa un descriptor mientras espera; no es el "rechazo explícito" que pide RNF-29.

### Alternativa C: rechazo inmediato con un error propio
- Ventajas: comportamiento explícito y observable; consistente con `QUEUE_FULL` (ADR-005).
- Desventajas/riesgos: en un pico, algunos clientes deben reintentar.

## Alternativas consideradas (tiempos de espera)
- **Un solo tiempo total por conexión**: corta también a clientes legítimos que mandan muchas solicitudes seguidas.
- **Dos tiempos: inactividad y mensaje**: uno para esperar a que *empiece* un mensaje y otro, más corto, para que termine de llegar una vez empezado. Distingue a un cliente que simplemente no tiene nada que pedir de uno que deja un mensaje a medias.

## Decisión
**Alternativa C** y **dos tiempos de espera**, con variables nuevas validadas al arrancar:

| Variable | Defecto | Qué pasa al excederse | Evento |
|---|---|---|---|
| `JOBRUNNER_MAX_CLIENTS` | 128 | La conexión de más recibe `TOO_MANY_CLIENTS` y se cierra | `CLIENT_REJECTED` |
| `JOBRUNNER_IDLE_TIMEOUT` | 60 s | Se cierra la conexión sin respuesta (no es un error) | `CLIENT_TIMEOUT` |
| `JOBRUNNER_MESSAGE_TIMEOUT` | 10 s | Mensaje empezado e incompleto: error `TIMEOUT` y se cierra. También limita `drain()` al responder | `PROTOCOL_ERROR` |

- El límite de 128 se eligió para cubrir con holgura las pruebas de carga del avance 2 (lotes de 90 y de 50 conexiones simultáneas) y quedar lejos del límite habitual de 1024 descriptores (`ulimit -n`), que también usan los pipes de los trabajos.
- Las conexiones rechazadas por red (ADR-013) no ocupan lugar: el filtro de red se aplica primero.
- Se reutiliza `operacion.check_rate_limit`, que estaba definida y sin uso (defecto 11 del vol. 2).
- `health` informa `clients_connected` y `max_clients`.

**Ciclo de vida (modifica ADR-011):**
1. Arranque: configuración → recuperación **sin despachar** → abrir el puerto (`ServidorEntrada.abrir`) → despachar lo recuperado → atender. Si el puerto no se puede abrir, el servicio termina con código 1 y los trabajos recuperados siguen QUEUED. Se elimina la verificación previa con un socket de prueba, que tenía la ventana descrita (es la alternativa "abrir antes de servir" que ADR-011 había comparado).
2. Cierre: igual que ADR-011 para los trabajos (las consultas siguen funcionando mientras dura); después se cierra el puerto y **todas** las conexiones abiertas, con un límite de 2 s, y luego se cancela la tarea del servidor.

## Consecuencias
- Positivas: el servicio no se queda sin descriptores por culpa de la red; los clientes lentos u ociosos no retienen recursos; el cierre ya no depende de los clientes; no se lanzan trabajos si no se puede escuchar.
- Negativas: un cliente que deje la conexión abierta más de `IDLE_TIMEOUT` sin pedir nada tendrá que reconectarse (el CLI abre una conexión por comando, así que no le afecta). En un pico de más de 128 conexiones algunas reciben error.
- Riesgos y mitigación: un valor de `IDLE_TIMEOUT` muy bajo cortaría a clientes en redes lentas → mínimo mayor que 0 y por defecto 60 s; el futuro panel web, si mantiene una conexión abierta, debe reconectarse cuando se cierre.

## Evidencia / prueba
`verif/scripts/test_tc016_tc024_limites_de_clientes_avance03.py` (cliente de más con `TOO_MANY_CLIENTS`, conteo de clientes en `health`, 20 clientes simultáneos, cliente ocioso desconectado, mensaje a medias con `TIMEOUT`, 200 conexiones sin fuga de descriptores) y `test_tc005_tc007_tc009_tc013_robustez_avance03.py::TC009CierreConClientes`. Siguen pasando `test_tc009_cierre_controlado.py::test_puerto_ocupado` y las pruebas de carga de TC-004 y TC-024.
