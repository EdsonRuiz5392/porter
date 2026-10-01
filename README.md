# Porter (JobRunner)

Porter es un sistema para Linux que **ejecuta, administra, observa y controla trabajos**: recibe un comando, lo corre en segundo plano como un proceso separado, le da un identificador, y permite consultar su estado, listar los trabajos, cancelarlos y conocer su código de salida. Funciona con un **servicio** que se queda corriendo y un **cliente** de línea de comandos que le envía solicitudes.

Proyecto de la materia Programación de Sistemas Avanzados, CUCEI, 2026B. "JobRunner" es el nombre de la especificación del cliente; **Porter** es el nombre de nuestra implementación.

## ¿Qué parte de esta guía leer?

| Si… | Lee |
|---|---|
| Ya usas Linux, Git y Python | [Guía rápida](#guía-rápida) |
| Es tu primera vez con una terminal o con estas herramientas | [Guía paso a paso](#guía-paso-a-paso) |
| Quieres entender cómo está hecho | [Cómo funciona por dentro](#cómo-funciona-por-dentro) y [Documentación](#documentación) |

Las dos guías llegan al mismo resultado; la segunda explica cada paso y qué deberías ver.

## Estado del proyecto

**Al 1 de octubre de 2026 — Avance 01 (núcleo local), en integración.** La operación remota todavía no forma parte de este avance.

| Módulo | Responsable | Estado |
|---|---|---|
| `src/cliente/cli.py` | Dylan | Implementado |
| `src/servicio/gestion_trabajos/cola.py`, `control.py` | Dylan | Implementados |
| `src/servicio/gestion_trabajos/launcher.py` | Marcos | Implementado con `asyncio` |
| `src/comun/protocolo.py`, `src/servicio/entrada.py` | Juan | Implementados; pendiente alinear firmas y constantes con el contrato |
| `src/servicio/persistencia.py`, `bitacora.py`, `operacion.py` | Ángel | En integración: demostrados en la junta del 1 de octubre, pendientes de subir a `main` |
| `src/servicio/main.py` | Ángel | Listo |
| Verificación (`verif/`) | Edson | Plan, matriz de trazabilidad, 9 casos de prueba, prueba de contratos y script de evidencia |

**Qué funciona hoy desde `main`:** clonar, instalar, correr las pruebas automatizadas y la ayuda del cliente. **El servicio completo aún no arranca desde `main`** hasta que termine la integración de los módulos marcados arriba; los pasos de ejecución de esta guía describen el uso previsto para la revisión del 6 de octubre.

## Guía rápida

Para quien ya conoce Linux, Git y Python.

**Requisitos:** Linux (referencia: Ubuntu 24.04 LTS), Python 3.12, `git`, `python3-venv`. No requiere root para operar.

```bash
git clone https://github.com/EdsonRuiz5392/porter.git
cd porter
python3 -m venv .venv && source .venv/bin/activate
pip install -r src/requirements.txt
```

**Configuración** por variables de entorno `JOBRUNNER_*` (host, puerto, concurrencia, cola, tiempo de gracia, directorio de datos, redes permitidas, tamaño máximo de mensaje). Los valores de ejemplo están en `src/.env.example`; para cargarlos en la terminal actual:

```bash
set -a; source src/.env.example; set +a
```

**Ejecución.** Servicio en una terminal, cliente en otra; ambas con el entorno virtual activo y las mismas variables cargadas, desde la raíz del repositorio:

```bash
python -m src.servicio.main
```

```bash
python -m src.cliente.cli submit sleep 30     # devuelve el ID del trabajo
python -m src.cliente.cli status <ID>         # estado y código de salida
python -m src.cliente.cli list                # todos los trabajos
python -m src.cliente.cli cancel <ID>         # SIGTERM y, tras el tiempo de gracia, SIGKILL
python -m src.cliente.cli --help
```

El servicio se detiene con `Ctrl+C` (cierre controlado). Los datos quedan en `JOBRUNNER_DATA_DIR`: `jobs.db` (SQLite), `jobrunner.log` (bitácora) y la salida de cada trabajo.

**Pruebas, con un solo comando:**

```bash
bash verif/scripts/run_verification.sh
```

Corre `pytest` sobre `verif/scripts/` y guarda la evidencia en `verif/results/<run-id>/` (commit, entorno, comando, salida y resumen PASS/FAIL). Termina con código 0 si todo pasa y 1 si algo falla. Los casos de prueba manuales están en `verif/test-cases/`.

## Guía paso a paso

Para quien empieza desde cero. No necesitas saber programar para seguirla.

### Qué es Porter, en palabras simples

Imagina una oficina con una **ventanilla**. Tú entregas un encargo ("ejecuta este programa"), te dan un **número de folio** y te vas. Adentro, alguien hace el trabajo mientras tú sigues con lo tuyo. Después puedes volver a la ventanilla con tu folio y preguntar: ¿ya terminó?, ¿salió bien?, o pedir que lo cancelen.

- La oficina que se queda abierta es el **servicio**.
- La ventanilla desde la que pides cosas es el **cliente**.
- Cada encargo es un **trabajo**, y su folio es el **ID**.

### Palabras que vas a ver

| Palabra | Qué significa |
|---|---|
| Terminal | La ventana donde se escriben comandos en lugar de usar el ratón |
| Comando | Una instrucción escrita; se ejecuta al presionar Enter |
| Repositorio | La carpeta del proyecto, guardada en GitHub con todo su historial |
| Clonar | Descargar una copia del repositorio a tu computadora |
| Entorno virtual | Una "caja" aislada donde se instalan las herramientas del proyecto sin afectar al resto del sistema |
| Proceso | Un programa que está corriendo en este momento |
| Código de salida | El número con que un programa avisa cómo terminó: 0 significa "bien", cualquier otro significa "hubo un problema" |
| Variable de entorno | Un ajuste (por ejemplo, el puerto) que se le pasa al programa desde la terminal |

### Lo que necesitas

Una computadora con **Linux**. Si usas Windows, puedes instalar Ubuntu con WSL2 o usar una máquina virtual; el equipo usa Ubuntu 24.04. Abre una terminal y escribe los comandos uno por uno, presionando Enter después de cada uno.

### Paso 1 — Instalar las herramientas base

Solo la primera vez. Te pedirá tu contraseña; al escribirla no se ve nada, es normal.

```bash
sudo apt update && sudo apt install -y git python3 python3-venv
```

**Qué deberías ver:** muchas líneas de texto y, al final, de nuevo el símbolo `$` esperando otro comando.

### Paso 2 — Descargar el proyecto

```bash
git clone https://github.com/EdsonRuiz5392/porter.git
```

```bash
cd porter
```

El primer comando descarga el proyecto a una carpeta llamada `porter`; el segundo entra en ella. **Todos los pasos siguientes se hacen dentro de esa carpeta.**

### Paso 3 — Preparar el entorno del proyecto

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r src/requirements.txt
```

El primero crea la "caja" aislada, el segundo entra en ella y el tercero instala lo que el proyecto necesita. **Qué deberías ver:** tu línea de comandos ahora empieza con `(.venv)`. Cada vez que abras una terminal nueva, repite el segundo comando.

### Paso 4 — Comprobar que todo quedó bien

```bash
python -m src.cliente.cli --help
```

**Qué deberías ver:** la lista de comandos disponibles: `submit`, `status`, `list` y `cancel`.

```bash
bash verif/scripts/run_verification.sh
```

Esto corre las pruebas automáticas del proyecto. **Qué deberías ver:** una lista de comprobaciones marcadas `PASSED` o `FAILED` y, al final, un resumen con `PASS` o `FAIL` y la carpeta donde quedó guardado el resultado.

### Paso 5 — Encender el servicio

Carga la configuración de ejemplo y enciende el servicio:

```bash
set -a; source src/.env.example; set +a
```

```bash
python -m src.servicio.main
```

**Qué deberías ver:** la terminal se queda "ocupada", sin devolverte el `$`. Eso es correcto: el servicio está atendiendo. **No cierres esta terminal.**

> Si aparece un mensaje con `NotImplementedError`, es porque la integración del servicio aún no termina en esta versión; revisa la sección [Estado del proyecto](#estado-del-proyecto).

### Paso 6 — Enviar tu primer trabajo

Abre **otra terminal**, entra a la carpeta y repite la preparación:

```bash
cd porter && source .venv/bin/activate && set -a && source src/.env.example && set +a
```

Envía un trabajo que simplemente espera 30 segundos:

```bash
python -m src.cliente.cli submit sleep 30
```

**Qué deberías ver:** un mensaje con el **ID** del trabajo. Cópialo.

Pregunta cómo va (cambia `ID` por el tuyo):

```bash
python -m src.cliente.cli status ID
```

Mira todos los trabajos:

```bash
python -m src.cliente.cli list
```

Cancela el trabajo antes de que termine:

```bash
python -m src.cliente.cli cancel ID
```

**Los estados posibles** de un trabajo:

| Estado | Significa |
|---|---|
| `QUEUED` | Está en la fila, esperando turno |
| `RUNNING` | Se está ejecutando |
| `SUCCEEDED` | Terminó bien (código de salida 0) |
| `FAILED` | Terminó con error (código distinto de 0) |
| `CANCELED` | Alguien lo canceló |

### Paso 7 — Apagar

En la terminal del servicio, presiona `Ctrl+C`. El servicio deja de aceptar trabajos nuevos y se cierra de forma ordenada.

### Si algo sale mal

| Lo que ves | Qué hacer |
|---|---|
| `command not found: python3` o `git` | Repite el Paso 1 |
| `ensurepip is not available` | `sudo apt install -y python3-venv` y repite el Paso 3 |
| `No module named pytest` | Falta activar el entorno: `source .venv/bin/activate` |
| `No module named src` | No estás en la carpeta del proyecto: `cd porter` |
| `Error de conexión con el servicio` | El servicio no está encendido, o las dos terminales no cargaron la misma configuración (Paso 5) |

## Cómo funciona por dentro

```
   Cliente (cli.py)
        │  mensaje por socket TCP en localhost
        ▼
   Entrada ──────────► Operación (configuración, cierre, salud)
        │
        ▼
   Control de trabajos ──► Cola (los que esperan)
        │        │
        │        └──────► Lanzador ──► procesos hijos, uno por trabajo
        ├──────► Persistencia (SQLite: estado, tiempos, código de salida)
        └──────► Bitácora (eventos con fecha e ID de trabajo)
```

El **recorrido de una solicitud**: el cliente arma un mensaje y lo envía; `entrada` lo lee y lo valida; `control` crea el trabajo, lo guarda, lo anota en la bitácora y lo encola; cuando hay lugar, el `launcher` lo arranca como un **proceso separado**; al terminar, se registra su **código de salida** y su estado final. Una cancelación envía la señal `SIGTERM` y, si el proceso no termina dentro del tiempo de gracia, `SIGKILL`.

## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `src/cliente/` | Cliente de línea de comandos |
| `src/comun/` | Modelo de trabajo y protocolo de mensajes |
| `src/servicio/` | Servicio: entrada, operación, persistencia, bitácora y gestión de trabajos |
| `docs/decisions/` | Decisiones de arquitectura (ADR) |
| `docs/technical-guide/` | Contratos de interfaz, mapa de uso y módulos explicados |
| `docs/ai-usage/` | Registro del uso de herramientas de IA |
| `verif/verification-plan/` | Plan de verificación y matriz de trazabilidad |
| `verif/test-cases/` | Casos de prueba `TC-XXX` |
| `verif/scripts/` | Pruebas automatizadas y script de verificación |
| `verif/results/` | Evidencia de cada corrida |
| `project-management/` | Roles, alcance, cronograma y minutas |

## Documentación

- Decisiones de arquitectura: [`docs/decisions/`](docs/decisions/)
- Contratos entre módulos: [`docs/technical-guide/contratos-interfaces.md`](docs/technical-guide/contratos-interfaces.md)
- Módulos explicados en prosa: [`docs/technical-guide/modulos-explicados.md`](docs/technical-guide/modulos-explicados.md)
- Alcance del Avance 1: [`project-management/alcance-avance-1.md`](project-management/alcance-avance-1.md)
- Roles y responsabilidades: [`project-management/roles-matrix.md`](project-management/roles-matrix.md)
- Cronograma y actividad del proyecto: [`project-management/cronograma.md`](project-management/cronograma.md)
- Minutas de las juntas: [`project-management/minutas/`](project-management/minutas/)
- Plan de verificación: [`verif/verification-plan/plan-verificacion.md`](verif/verification-plan/plan-verificacion.md)
- Matriz de trazabilidad: [`verif/verification-plan/traceability-matrix.md`](verif/verification-plan/traceability-matrix.md)
- Casos de prueba: [`verif/test-cases/`](verif/test-cases/)

## Equipo

| Integrante | Correo institucional | Área | Módulos |
|---|---|---|---|
| Dylan | `dylan.encina3006@alumnos.udg.mx` | Cliente y gestión de trabajos | `cli.py`, `control.py`, `cola.py` |
| Juan Zepeda | `juan.zepeda5221@alumnos.udg.mx` | Entrada y protocolo | `entrada.py`, `protocolo.py` |
| Ángel Vences | `angel.vences6219@alumnos.udg.mx` | Persistencia y operación; responsable de producto | `persistencia.py`, `bitacora.py`, `operacion.py` |
| Marcos Garcia | `albertodejesus.garcia@alumnos.udg.mx` | Lanzador de procesos | `launcher.py` |
| Edson Ruiz | `edson.ruiz5392@alumnos.udg.mx` | Verificación y trazabilidad; líder de verificación | Matriz, casos `TC-XXX` y scripts |

## Forma de trabajo

Issue asignado → rama propia → commits → pull request con `Closes #N` → revisión del equipo → merge a `main` → issue cerrado. La evidencia de cada prueba se guarda en `verif/results/`. El uso de herramientas de IA está permitido y se registra en `docs/ai-usage/`; el equipo es responsable de comprender, probar y defender todo lo entregado.
