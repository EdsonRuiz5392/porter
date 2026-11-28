# ADR-013: Acceso de red: dónde escucha el servicio y quién puede conectarse (Python)

- Estado: Aceptado
- Fecha: 2026-11-19
- Requisitos relacionados: RF-18, RF-19, RF-20, RNF-12, RNF-13, RNF-15, RNF-26
- Relación con otros ADR: complementa ADR-004 (protocolo). El orden de arranque que permite abrir el puerto antes de despachar está en ADR-014.

## Contexto y problema
El Hito 3 pide operar JobRunner desde otro equipo, pero solo desde localhost, la LAN autorizada o una VPN, y demostrar una conexión permitida y otra rechazada. Hasta el avance 2, `JOBRUNNER_ALLOWED_NETWORKS` se leía pero `entrada.main` la ignoraba: con `JOBRUNNER_HOST=0.0.0.0` cualquier equipo podía enviar comandos (se comprobó conectando desde otra IP). Además `JOBRUNNER_HOST` aceptaba una sola dirección, así que para usar la LAN había que escuchar en todas las interfaces o perder el acceso por `127.0.0.1`.

La demostración será en una LAN creada con el hotspot de un celular, pero el equipo puede cambiar a una VPN con WireGuard (sobre el mismo hotspot o abriendo un puerto en un router). La decisión no debe depender de cuál se use.

## Alternativas consideradas

### Alternativa A: solo firewall del sistema (`ufw`/`iptables`)
- Ventajas: no hay código; el paquete se bloquea antes de llegar al programa.
- Desventajas/riesgos: requiere root (choca con RNF-03 para la operación normal); la regla vive fuera del repositorio, no se puede probar con las pruebas automáticas ni demostrar con la bitácora; si alguien olvida configurarla, el servicio queda abierto.

### Alternativa B: lista de redes permitidas dentro del servicio, con `ipaddress`
- Descripción: al aceptar cada conexión (`_on_connect`) se toma la IP de origen y se compara contra la lista de `JOBRUNNER_ALLOWED_NETWORKS` (IPs sueltas o redes CIDR).
- Ventajas: biblioteca estándar; funciona igual en LAN, VPN o localhost porque solo mira la IP de origen; queda registrado en la bitácora; se prueba de forma reproducible.
- Desventajas/riesgos: la IP de origen se puede falsificar en una red sin controles (para TCP es difícil, porque el saludo de tres vías exige recibir la respuesta).

### Alternativa C: autenticación con contraseña o certificados (TLS)
- Ventajas: identifica a la persona, no solo a la red.
- Desventajas/riesgos: la autenticación empresarial está fuera de alcance; manejo de secretos (RNF-15) y certificados; no sustituye la restricción por red que piden RF-20 y RNF-13.

## Decisión
**Alternativa B**, y el firewall de la A se documenta como **defensa adicional recomendada**, no obligatoria.

1. **Dónde escucha (`JOBRUNNER_HOST`)**: ahora acepta una lista, por ejemplo `127.0.0.1,192.168.43.10`. El servicio escucha en todas a la vez (`asyncio.start_server` con varias direcciones). Por defecto sigue siendo solo `127.0.0.1` (RNF-12).
   - Se rechaza al arrancar cualquier dirección pública de Internet (`ip.is_global`) y todo lo que no sea una IP o `localhost` (RNF-26).
   - `0.0.0.0` / `::` se permiten porque la lista de redes sigue decidiendo quién entra, pero se registra el evento `BIND_ALL_INTERFACES` como advertencia.
2. **Quién entra (`JOBRUNNER_ALLOWED_NETWORKS`)**: lista de IPs o redes CIDR; por defecto `127.0.0.1,::1`.
   - El servicio **no arranca** si una entrada no es válida, si la lista queda vacía o si incluye redes públicas (`0.0.0.0/0`, `8.8.8.0/24`). Se aceptan redes privadas, loopback, link-local y la red compartida `100.64.0.0/10` (la que usan VPN como Tailscale).
   - Las IPv4 que llegan por un socket IPv6 (`::ffff:192.168.1.5`) se comparan como IPv4.
3. **Rechazo**: el servicio responde un error `ACCESS_DENIED` con un mensaje genérico (sin revelar la lista ni la configuración), espera hasta 1 s a que el cliente lo lea y cierra. Se registra `ACCESS_DENIED` con la IP y el puerto de origen. El rechazo ocurre **antes de leer** cualquier solicitud: un intruso no puede ni consultar.
4. **Lógica compartida**: el filtro vive en `src/comun/acceso_red.py`, no en `servicio/`, para que el futuro panel web aplique exactamente la misma regla.

**Se comparó responder `ACCESS_DENIED` contra cerrar en silencio.** Cerrar en silencio da menos información a un atacante, pero el usuario legítimo mal configurado no sabría por qué falla (RNF-21). Como el servicio solo escucha en redes privadas, se eligió responder con un mensaje que no expone nada de la configuración.

**Cómo queda cada escenario (sin cambiar código):**

| Escenario | `JOBRUNNER_HOST` | `JOBRUNNER_ALLOWED_NETWORKS` |
|---|---|---|
| Solo local | `127.0.0.1` | `127.0.0.1,::1` |
| LAN con hotspot | `127.0.0.1,<IP del servidor>` | `127.0.0.1,<IP de cada laptop>/32` o la red `/24` |
| VPN WireGuard (sobre el hotspot o con puerto abierto) | `127.0.0.1,10.8.0.1` | `127.0.0.1,10.8.0.0/24` |

Con WireGuard y puerto abierto en el router, a Internet solo queda expuesto el puerto UDP de WireGuard; JobRunner sigue escuchando en la IP de la VPN.

## Consecuencias
- Positivas: cumple RF-20 y RNF-13 con evidencia en la bitácora; la misma versión sirve para LAN y VPN; un error de configuración se detecta al arrancar y no durante la demostración; las operaciones no cambian entre local y remoto (RF-19).
- Negativas: si el cliente está en el **mismo** equipo pero se conecta a la IP de la LAN, su IP de origen es esa, no `127.0.0.1`; hay que incluirla en la lista o usar `--host 127.0.0.1` (documentado en `.env.example`). Las IPs del hotspot pueden cambiar de un día a otro y hay que revisar la lista antes de la demostración.
- Riesgos y mitigación: falsificación de IP en la misma red → aceptable en el alcance académico (red controlada); con la VPN el riesgo baja porque WireGuard autentica cada equipo por su llave. Una lista demasiado amplia (`/16`) sigue siendo privada pero deja entrar a más equipos de lo necesario → la guía recomienda IPs `/32` para la demostración.

## Evidencia / prueba
`verif/scripts/test_tc010_tc011_red_avance03.py`: flujo completo desde una dirección autorizada distinta de 127.0.0.1, misma semántica local y remota, varias direcciones de escucha, escucha en la IP real de la LAN, rechazo con y sin solicitud, redes CIDR, configuración por defecto (solo 127.0.0.1 en `/proc/net/tcp`) y siete configuraciones inválidas que impiden el arranque. Con el avance 2: 9 de 11 fallan; con el avance 3: 11 de 11 pasan.
