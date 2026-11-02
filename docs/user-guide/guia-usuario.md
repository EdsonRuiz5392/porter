# Guía de usuario — Porter

Cómo instalar, configurar y usar Porter en un equipo con Linux. Esta guía cubre la operación local del Avance 02; la operación remota corresponde al Hito 3 y todavía no está disponible.

## 1. Requisitos

- Linux. Referencia: Ubuntu 24.04 LTS.
- Python 3.12 y `git`.
- No requiere root.

## 2. Instalación

```bash
git clone https://github.com/EdsonRuiz5392/porter.git
cd porter
python3 -m venv .venv
source .venv/bin/activate
pip install -r src/requirements.txt
```

El servicio y el cliente solo usan la biblioteca estándar de Python; `requirements.txt` instala herramientas de prueba. Todos los comandos de esta guía se ejecutan desde la raíz del repositorio.

## 3. Iniciar y detener el servicio

```bash
python -m src.servicio.main
```

Al arrancar muestra `[*] Servidor de entrada activo en ('127.0.0.1', 9000)` y la terminal se queda ocupada: usa otra para el cliente.

Para detenerlo, presiona `Ctrl+C` o envía `kill -TERM <PID>`. Las dos hacen el mismo cierre controlado:

1. Deja de aceptar trabajos nuevos. Los envíos reciben `SERVICE_CLOSING`; las consultas siguen funcionando.
2. Espera hasta `JOBRUNNER_SHUTDOWN_TIMEOUT` segundos a que terminen los trabajos en curso.
3. Cancela los que sigan corriendo (quedan `CANCELED`).
4. Los trabajos `QUEUED` se conservan y se ejecutan en el siguiente arranque.

El cierre tarda como máximo `SHUTDOWN_TIMEOUT + GRACE_SECONDS + 5` segundos, unos 40 s con los valores por defecto.

## 4. Comandos del cliente

En esta tabla, `porter` significa `python -m src.cliente.cli`.

| Comando | Qué hace |
|---|---|
| `porter --help` | Muestra la ayuda |
| `porter submit sleep 30` | Envía un trabajo y devuelve su ID |
| `porter submit --request-id FOLIO echo hola` | Envía un trabajo con folio, para poder reintentar sin duplicarlo |
| `porter status <ID>` | Estado, PID, tiempos, código de salida y folio |
| `porter list` | Lista todos los trabajos |
| `porter list --status FAILED` | Lista solo los de un estado |
| `porter cancel <ID>` | Cancela un trabajo en cola o en ejecución |
| `porter output <ID>` | Muestra la salida estándar capturada |
| `porter output <ID> stderr` | Muestra la salida de error capturada |
| `porter health` | Resumen: si está activo, trabajos en ejecución, en cola y errores |

**Importante:** el comando y sus argumentos van separados y sin comillas juntas. Escribe `submit sleep 30`. Con `submit "sleep 30"`, Porter busca un programa llamado literalmente `sleep 30` y el trabajo termina en `FAILED`.

**Si necesitas varias órdenes o una tubería**, usa bash: `porter submit bash -c "ls | wc -l"`.

El cliente termina con código **0** si la operación salió bien y con **1** si hubo un error, así que se puede usar en scripts.

## 5. Estados de un trabajo

| Estado | Significa |
|---|---|
| `QUEUED` | Espera un lugar para ejecutarse |
| `RUNNING` | Se está ejecutando |
| `SUCCEEDED` | Terminó con código 0 |
| `FAILED` | Terminó con código distinto de 0, no se pudo lanzar, murió por una señal que nadie pidió o se interrumpió por una caída del servicio |
| `CANCELED` | Alguien pidió cancelarlo, o lo terminó el cierre del servicio |

Cómo leer el código de salida:

| Código | Significa |
|---|---|
| `0` | Terminó bien |
| Positivo | El programa terminó con ese código de error |
| Negativo | Murió por esa señal: `-15` es SIGTERM y `-9` es SIGKILL |
| `-1` | Porter no pudo lanzarlo o capturarlo, o quedó interrumpido por una caída del servicio. La bitácora dice cuál fue (`ERROR` o `INTERRUPTED`) |
| Vacío | Todavía no termina, o se canceló antes de ejecutarse |

## 6. Cancelar un trabajo

- **En cola:** se retira y nunca se ejecuta.
- **En ejecución:** Porter envía SIGTERM a todo el grupo del trabajo (el programa y los procesos que haya lanzado). Si después de `JOBRUNNER_GRACE_SECONDS` sigue vivo alguno, envía SIGKILL.
- **Ya terminado:** responde `ALREADY_FINISHED` y no cambia nada.

La respuesta `CANCELING` significa que la solicitud se aceptó. Consulta `status` para ver el estado final.

## 7. Solicitudes repetidas (folio)

El folio es opcional y sirve cuando no sabes si un envío llegó, por ejemplo si se cortó la conexión.

| Situación | Resultado |
|---|---|
| Sin folio | Siempre se crea un trabajo nuevo |
| Folio nuevo | Se crea el trabajo y el folio queda ligado a él para siempre |
| Mismo folio, mismo comando y argumentos | Devuelve el trabajo original; no ejecuta nada |
| Mismo folio, otro comando o argumentos | Error `REQUEST_ID_CONFLICT` |

## 8. Si el servicio se reinicia o se cae

Al arrancar, Porter recupera lo que hay en su base de datos:

| Estado guardado | Qué pasa |
|---|---|
| `SUCCEEDED`, `FAILED`, `CANCELED` | Se conserva sin cambios |
| `QUEUED` | Vuelve a la cola en su orden original y se ejecuta |
| `RUNNING` | Si el proceso sigue vivo y es de Porter, se termina. El trabajo queda `FAILED` con código `-1` y el evento `INTERRUPTED`. No se vuelve a ejecutar, porque repetir un comando no siempre es seguro |

Si hay más pendientes que `JOBRUNNER_MAX_QUEUE`, se recuperan todos y los envíos nuevos reciben `QUEUE_FULL` hasta que la cola baje.

## 9. Configuración

Se configura con variables de entorno. Para cargar los valores de ejemplo en la terminal actual:

```bash
set -a; source src/.env.example; set +a
```

| Variable | Por defecto | Qué controla | Válido |
|---|---|---|---|
| `JOBRUNNER_HOST` | `127.0.0.1` | Interfaz de escucha | — |
| `JOBRUNNER_PORT` | `9000` | Puerto | 1 a 65535 |
| `JOBRUNNER_MAX_CONCURRENCY` | `3` | Trabajos simultáneos | Al menos 1 |
| `JOBRUNNER_MAX_QUEUE` | `100` | Lugares en la cola | Al menos 1 |
| `JOBRUNNER_GRACE_SECONDS` | `5` | Espera entre SIGTERM y SIGKILL | 0 o más |
| `JOBRUNNER_SHUTDOWN_TIMEOUT` | `30` | Espera máxima al cerrar antes de cancelar | 0 o más |
| `JOBRUNNER_DATA_DIR` | `./data` | Carpeta de datos | — |
| `JOBRUNNER_ALLOWED_NETWORKS` | `127.0.0.1` | Redes permitidas. **Todavía no se aplica** (Hito 3) | — |
| `JOBRUNNER_MAX_MESSAGE_BYTES` | `1048576` | Tamaño máximo de un mensaje | Al menos 1024 |

El cliente usa `JOBRUNNER_HOST`, `JOBRUNNER_PORT` y `JOBRUNNER_MAX_MESSAGE_BYTES`. Deben coincidir con los del servicio.

Si un valor es inválido, el servicio no arranca y dice cuál variable falló.

## 10. Dónde quedan los datos

Dentro de `JOBRUNNER_DATA_DIR`:

| Archivo | Contenido |
|---|---|
| `jobs.db` (y `-wal`, `-shm`) | Base de datos SQLite con los trabajos |
| `jobrunner.log` | Bitácora: una línea por evento con fecha UTC, ID de trabajo, evento y detalle |
| `output/<ID>.stdout.log` | Salida estándar de cada trabajo |
| `output/<ID>.stderr.log` | Salida de error de cada trabajo |

**Limpieza.** Porter no borra nada por sí solo. Para limpiar, detén el servicio con cierre controlado y borra la carpeta de datos **completa**. Nunca borres solo `jobs.db` dejando `-wal` y `-shm`.

## 11. Mensajes de error frecuentes

| Mensaje | Causa | Qué hacer |
|---|---|---|
| `Error de conexión con el servicio` | El servicio está apagado, o el puerto no coincide | Inicia el servicio o revisa `JOBRUNNER_PORT` |
| `[QUEUE_FULL]` | La cola está llena; el trabajo no se aceptó | Reintenta más tarde o sube `JOBRUNNER_MAX_QUEUE` |
| `[SERVICE_CLOSING]` | El servicio se está cerrando | Espera a que reinicie |
| `[INVALID_REQUEST]` | La solicitud está mal formada | Revisa el comando con `--help` |
| `[NOT_FOUND]` | No existe un trabajo con ese ID | Revisa el ID con `list` |
| `[REQUEST_ID_CONFLICT]` | El folio ya se usó con otro comando | Usa otro folio |
| `[VERSION_UNSUPPORTED]` | El cliente y el servicio usan versiones distintas del protocolo | Usa el cliente de esta misma versión |
| `Configuración inválida` | Una variable tiene un valor no permitido | Corrige la variable que indica el mensaje |
| `No se puede escuchar en` | El puerto está ocupado | Cambia `JOBRUNNER_PORT` o detén el otro proceso |
| Trabajo `FAILED`, código `-1`, evento `ERROR` | No se pudo lanzar, por ejemplo porque el programa no existe | Revisa el nombre del comando y `jobrunner.log` |

## 12. Límites conocidos

- **Operación remota:** todavía no está disponible; `JOBRUNNER_ALLOWED_NETWORKS` aún no se aplica.
- **Trabajos interactivos:** no están soportados. El trabajo recibe una entrada vacía.
- **Salidas muy grandes:** `output` devuelve el archivo completo y puede exceder `JOBRUNNER_MAX_MESSAGE_BYTES`. En ese caso, lee el archivo directamente en `output/`.
- **Procesos que se separan a propósito** de su grupo (por ejemplo con `setsid`) quedan fuera del control de Porter.
- **Disco:** los datos crecen sin límite hasta que se limpian a mano.
- **Carga alta:** en algunas pruebas de carga un trabajo válido terminó `FAILED` con `database is locked`. Está registrado como defecto abierto en #58.
