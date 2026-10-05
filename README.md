# Despliegue de aplicación multiservicio con Docker

**Autor:** DIEGO MAURICIO GOMEZ RODRIGUEZ\
**Usuario de GitHub:** Gomers16\
**Programa:** Despliegue de aplicaciones y servicios en contenedores Docker (SENA, Regional Tolima)

Proyecto de la formación complementaria **Despliegue de aplicaciones y servicios en contenedores Docker** (SENA, Centro de Comercio y Servicios, Regional Tolima, competencia 220501086).

Una aplicación web de tres servicios, levantada con **un solo comando**:

| Servicio | Imagen | Puerto interno | Función |
|---|---|---|---|
| `proxy` | `nginx:1.30-alpine` | 80 | Proxy inverso. Único servicio expuesto al exterior (`8080`). |
| `api` | Construida con el `Dockerfile` (`python:3.14-slim`) | 8000 | API FastAPI. Corre como usuario sin privilegios. |
| `db` | `postgres:18-alpine` | 5432 | Base de datos con volumen persistente. **No publica puertos.** |

Ninguna imagen usa la etiqueta `latest`: el despliegue es reproducible.

---

## Lo desarrollado

- Instalación de **Docker Engine 29.8.2** y Docker Compose v5.6.0 en Ubuntu sobre WSL2 (sin Docker Desktop).
- **API en FastAPI** con los endpoints `/health` y `/db` (consulta a PostgreSQL).
- **Dockerfile multi-etapa** con usuario sin privilegios (UID 1001).
- **Nginx** como proxy inverso, único servicio expuesto (puerto 8080).
- **PostgreSQL 18** con volumen persistente y sin puertos publicados.
- **Docker Compose** con tres servicios, red interna, healthcheck y reinicio automático.
- Variables sensibles en `.env` (no versionado) y plantilla `.env.example`.
- **GitHub Actions** (`.github/workflows/publicar-imagen.yml`): construye y publica la imagen en GHCR con cada push a `main`, con etiquetas `latest` y `sha-...`.
- Imagen pública: `ghcr.io/gomers16/docker-despliegue-sena`.
- Pruebas realizadas desde un clon limpio: salud de la API, base de datos, red interna, aislamiento, persistencia y usuario sin privilegios.

---

## Tabla de contenido

1. [Arquitectura](#1-arquitectura)
2. [Estructura del repositorio](#2-estructura-del-repositorio)
3. [Requisitos](#3-requisitos)
4. [Instalación de Docker Engine](#4-instalación-de-docker-engine)
5. [Puesta en marcha](#5-puesta-en-marcha)
6. [Endpoints de la API](#6-endpoints-de-la-api)
7. [Variables de entorno](#7-variables-de-entorno)
8. [Verificación del despliegue](#8-verificación-del-despliegue)
9. [Comandos de operación](#9-comandos-de-operación)
10. [Imagen de la API](#10-imagen-de-la-api)
11. [Publicación automática (CI/CD)](#11-publicación-automática-cicd)
12. [Seguridad aplicada](#12-seguridad-aplicada)
13. [Solución de problemas](#13-solución-de-problemas)
14. [Notas sobre PostgreSQL 18 y Compose v5](#14-notas-sobre-postgresql-18-y-compose-v5)

---

## 1. Arquitectura

```
                 Exterior (navegador, curl)
                          │
                    puerto 8080
                          │
        ┌─────────────────▼─────────────────┐
        │  red interna "interna" (bridge)   │
        │                                   │
        │   ┌───────┐   ┌───────┐   ┌─────┐ │
        │   │ proxy │──▶│  api  │──▶│ db  │ │
        │   │ :80   │   │ :8000 │   │:5432│ │
        │   └───────┘   └───────┘   └──┬──┘ │
        │                              │    │
        └──────────────────────────────┼────┘
                                       │
                              volumen "pgdata"
```

- El cliente solo llega a `proxy`.
- `proxy` reenvía a `api` por su nombre de servicio (`http://api:8000`).
- `api` consulta a `db` por su nombre de servicio (`db`).
- Los datos de PostgreSQL viven en el volumen `pgdata` y sobreviven a `docker compose down`.

---

## 2. Estructura del repositorio

```
.
├── .github/workflows/publicar-imagen.yml   # CI/CD: construye y publica la imagen en GHCR
├── app/
│   ├── __init__.py
│   └── main.py                             # API FastAPI (/health y /db)
├── nginx/
│   └── default.conf                        # Configuración del proxy inverso
├── .dockerignore
├── .env.example                            # Plantilla de variables (valores ficticios)
├── .gitattributes                          # Finales de línea LF
├── .gitignore                              # Excluye .env
├── Dockerfile                              # Multi-etapa, usuario sin privilegios
├── docker-compose.yml                      # Orquestación de los tres servicios
└── requirements.txt                        # Dependencias con versión fija
```

El archivo `.env` real **no** está en el repositorio: lo crea cada persona a partir de `.env.example`.

---

## 3. Requisitos

| Recurso | Mínimo | Recomendado |
|---|---|---|
| Memoria RAM | 4 GB | 8 GB o más |
| Disco libre | 15 GB | 25 GB o más |
| Procesador | 64 bits con virtualización habilitada | 2 núcleos o más |
| Conexión | Para descargar imágenes | Banda ancha estable |

Sistemas operativos soportados: **Ubuntu 22.04 / 24.04 / 26.04**, **Windows 10 (v2004+) o 11 con WSL2**, **macOS 13 o superior (Intel o Apple Silicon)**.

Versiones de referencia con las que se probó:

| Componente | Versión |
|---|---|
| Docker Engine | 29.8.2 |
| Docker Compose | v5.6.0 (plugin, se usa como `docker compose`) |
| PostgreSQL | 18 (`postgres:18-alpine`) |
| Python | 3.14 (`python:3.14-slim`) |
| Nginx | 1.30 (`nginx:1.30-alpine`) |
| FastAPI / Uvicorn / psycopg | 0.142.2 / 0.54.0 / 3.3.6 |

> Se usa **Docker Engine**, no Docker Desktop. Los comandos son los mismos que se usan en un servidor de producción.

---

## 4. Instalación de Docker Engine

Siga **solo** la sección de su sistema operativo.

### 4A. Ubuntu 22.04 / 24.04 / 26.04 (nativo)

```bash
# 1. Retirar paquetes no oficiales que puedan entrar en conflicto
sudo apt remove -y docker.io docker-compose docker-compose-v2 docker-doc podman-docker

# 2. Registrar el repositorio oficial de Docker
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF

# 3. Instalar el motor, la CLI y los plugins de Buildx y Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io \
  docker-buildx-plugin docker-compose-plugin

# 4. Arrancar el servicio y habilitarlo al inicio
sudo systemctl enable --now docker

# 5. Usar docker sin sudo
sudo usermod -aG docker $USER
```

Cierre la sesión por completo y vuelva a entrar (o reinicie) para que el cambio de grupo surta efecto.

### 4B. Windows 10 (v2004+) / Windows 11 con WSL2

Windows no tiene núcleo Linux, así que Docker Engine se instala **dentro de una Ubuntu en WSL2**. Todo lo demás (docker, git, el editor) se usa desde la terminal de Ubuntu.

**Regla:** PowerShell se usa únicamente para comandos que empiezan por `wsl`.

**1. Preparar WSL (PowerShell como Administrador):**

```powershell
wsl --install --no-distribution
wsl --update
wsl --shutdown
wsl --set-default-version 2
wsl --list --online
```

**2. Instalar Ubuntu** (PowerShell como Administrador):

```powershell
wsl --install -d Ubuntu-24.04 --web-download
```

Si el nombre no se reconoce, use `wsl --install -d Ubuntu --web-download`.

**3. Primer arranque:** se abre una ventana de Ubuntu. Cree un usuario (minúsculas, sin espacios ni tildes) y una contraseña (no se ve al escribirla).

**4. Confirmar que quedó en WSL 2:**

```powershell
wsl --list --verbose
```

La columna `VERSION` de Ubuntu debe decir `2`. Si hay varias distribuciones, deje Ubuntu como predeterminada:

```powershell
wsl --set-default Ubuntu
```

**5. Habilitar systemd** (dentro de Ubuntu), si `systemctl is-system-running` responde `offline`:

```bash
sudo tee /etc/wsl.conf > /dev/null <<EOF
[boot]
systemd=true
EOF
```

Luego, en PowerShell: `wsl --shutdown`, y vuelva a abrir Ubuntu.

**6. Instalar Docker Engine:** dentro de Ubuntu, ejecute los pasos 1 a 5 del apartado 4A, sin cambiar nada.

**7. Aplicar el cambio de grupo:** en PowerShell, `wsl --shutdown`, y vuelva a abrir Ubuntu.

**8. Instalar Git dentro de Ubuntu** y trabajar en el sistema de archivos de Linux:

```bash
sudo apt update && sudo apt install -y git
git config --global user.name "Su Nombre"
git config --global user.email "su.correo@ejemplo.com"
mkdir -p ~/proyecto && cd ~/proyecto
```

> Guarde siempre el proyecto en `/home/su-usuario/...` y **nunca** en `/mnt/c/...`: es mucho más lento y causa errores de permisos.

**Visual Studio Code:** instale VS Code en Windows con la extensión **WSL** de Microsoft. Conéctese con `Ctrl+Shift+P` → **WSL: Connect to WSL using Distro...** → **Ubuntu**.

**Si tenía Docker Desktop instalado:** desactive su integración con WSL o desinstálelo. Compruebe con `docker context ls` que el asterisco está en `default`.

### 4C. macOS 13 o superior (Intel o Apple Silicon) con Colima

```bash
# 1. Instalar Homebrew, si aún no lo tiene
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Instalar el cliente de Docker, el plugin de Compose y Colima
brew install docker docker-compose colima

# 3. Carpeta de configuración del cliente
mkdir -p ~/.docker

# 4. Crear y arrancar la máquina virtual con Docker Engine dentro
colima start --cpu 2 --memory 4 --disk 20

# 5. Comprobar el estado
colima status
```

Registre el plugin de Compose en `~/.docker/config.json` (créelo si no existe):

```json
{
  "cliPluginsExtraDirs": ["/opt/homebrew/lib/docker/cli-plugins"]
}
```

Esa es la ruta en Mac con Apple Silicon. En Mac con procesador Intel use `/usr/local/lib/docker/cli-plugins`. Si tiene dudas, `brew --prefix` más `/lib/docker/cli-plugins`.

Colima **no arranca solo** al encender el Mac: después de cada reinicio ejecute `colima start`.

### 4D. Verificar la instalación (común a los tres)

```bash
docker --version
docker compose version
docker context ls
docker run --rm hello-world
```

Resultado esperado: `Docker version 29.x`, `Docker Compose version v5.x` (o v2.x), el asterisco en `default`, y el mensaje **Hello from Docker!**.

| Su sistema | Arrancar el motor | Detener el motor |
|---|---|---|
| Ubuntu nativo | `sudo systemctl start docker` | `sudo systemctl stop docker` |
| Windows con WSL2 | Abrir la terminal de Ubuntu | `wsl --shutdown` (PowerShell) |
| macOS con Colima | `colima start` | `colima stop` |

---

## 5. Puesta en marcha

```bash
# 1. Clonar el repositorio
git clone https://github.com/Gomers16/docker-despliegue-sena.git
cd docker-despliegue-sena

# 2. Crear el archivo de variables a partir de la plantilla
cp .env.example .env

# 3. (Recomendado) cambiar la contraseña de la base de datos
nano .env

# 4. Construir y levantar los tres servicios
docker compose up -d --build

# 5. Comprobar el estado
docker compose ps
```

`docker compose ps` debe mostrar los tres servicios `Up`, y `db` en estado `healthy`. La primera ejecución tarda más porque descarga las imágenes.

Abra en el navegador o con `curl`:

```bash
curl http://localhost:8080/health
curl http://localhost:8080/db
```

En Windows, ejecute los comandos dentro de la terminal de Ubuntu y abra `http://localhost:8080` en el navegador de Windows: WSL2 reenvía los puertos. En macOS, Colima también los reenvía.

> Si el puerto `8080` está ocupado, cambie `"8080:80"` en la sección `proxy` de `docker-compose.yml`.

---

## 6. Endpoints de la API

Todos se consumen a través del proxy en `http://localhost:8080`.

| Método | Ruta | Respuesta | Descripción |
|---|---|---|---|
| GET | `/health` | `{"status":"ok"}` (200) | Comprueba que la API responde. |
| GET | `/db` | `{"version":"PostgreSQL 18.x ..."}` (200) | Consulta `SELECT version()` a PostgreSQL. |
| GET | `/db` (BD caída) | `{"detail":"Base de datos no disponible","error":"OperationalError"}` (503) | La API sigue viva aunque la BD falle. |

La respuesta de error incluye solo el tipo de excepción, para no exponer el host ni los datos de conexión.

---

## 7. Variables de entorno

Se definen en `.env` (no versionado). La plantilla `.env.example` tiene las mismas claves con valores ficticios.

| Variable | Ejemplo | Usada por | Descripción |
|---|---|---|---|
| `DB_NAME` | `appdb` | `db`, `api` | Nombre de la base de datos. |
| `DB_USER` | `postgres` | `api` | Usuario de conexión (por defecto `postgres`). |
| `DB_ADMIN_PASSWORD` | `cambiar_esta_clave` | `db`, `api` | Contraseña del usuario administrador. **Cámbiela.** |
| `DB_HOST` | `db` | `api` | Lo fija `docker-compose.yml`; es el nombre del servicio de BD. |

Genere una contraseña aleatoria:

```bash
openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | head -c 24; echo
```

> La contraseña de la base de datos solo se aplica **la primera vez** que se crea el volumen. Si la cambia después, debe borrar el volumen (`docker compose down -v`, destruye los datos) o cambiarla desde `psql`.

---

## 8. Verificación del despliegue

### 8.1 Levantado desde cero

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8080/health
```

### 8.2 Red interna

La API resuelve el nombre del servicio de base de datos:

```bash
docker compose exec api python -c "import socket; print(socket.gethostbyname('db'))"
```

Debe imprimir una IP privada (por ejemplo `172.19.0.2`).

### 8.3 Aislamiento de la base de datos

La BD no debe publicarse al exterior:

```bash
docker port $(docker compose ps -q db) || true
curl --max-time 3 http://localhost:5432 || echo "correcto: la BD no responde desde el host"
```

`docker port` debe salir vacío y `curl` debe fallar. En `docker compose ps`, solo `proxy` muestra `0.0.0.0:8080->80/tcp`; `api` y `db` muestran únicamente `8000/tcp` y `5432/tcp` (puertos internos, no publicados).

### 8.4 Persistencia

```bash
docker compose exec db psql -U postgres -d appdb \
  -c "CREATE TABLE IF NOT EXISTS prueba(id int); INSERT INTO prueba VALUES (1);"

docker compose down && docker compose up -d
# esperar a que db esté healthy (docker compose ps)

docker compose exec db psql -U postgres -d appdb -c "SELECT * FROM prueba;"
```

La fila con `id = 1` debe seguir ahí.

### 8.5 Consumo de recursos

```bash
docker stats --no-stream
```

El total de los tres servicios es de aproximadamente 80 MiB, muy por debajo de los 4 GB mínimos.

### 8.6 Usuario sin privilegios

```bash
docker compose exec api id
```

Debe mostrar `uid=1001(appuser)`, no `root`.

---

## 9. Comandos de operación

| Comando | Qué hace |
|---|---|
| `docker compose up -d` | Levanta todos los servicios en segundo plano. |
| `docker compose up -d --build` | Reconstruye la imagen de la API y levanta. |
| `docker compose ps` | Lista el estado de los servicios. |
| `docker compose logs -f` | Muestra los registros en tiempo real (`Ctrl+C` para salir). |
| `docker compose logs -f api` | Registros solo de la API. |
| `docker compose exec api sh` | Abre una terminal dentro del contenedor de la API. |
| `docker compose down` | Detiene y elimina los contenedores, **conserva los datos**. |
| `docker compose down -v` | Elimina también los volúmenes: **borra los datos**. |
| `docker stats` | Consumo de CPU y memoria. |
| `docker system df` | Espacio ocupado por Docker. |

---

## 10. Imagen de la API

El `Dockerfile` es **multi-etapa**: una etapa instala las dependencias y otra, más liviana, solo ejecuta.

```dockerfile
# Etapa 1: construcción
FROM python:3.14-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Etapa 2: ejecución
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN useradd --create-home --uid 1001 appuser
WORKDIR /app
COPY --from=builder /install /usr/local
COPY app/ ./app/
USER appuser
EXPOSE 8000
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

Construir y administrar a mano:

```bash
docker build -t api-app:1.0.0 .
docker images | grep api-app
docker history api-app:1.0.0
docker system df
```

La imagen ocupa unos 243 MB en disco (58 MB comprimida). `.dockerignore` excluye `.git/`, `__pycache__/`, `.env` y `docs/`.

---

## 11. Publicación automática (CI/CD)

El flujo `.github/workflows/publicar-imagen.yml` se ejecuta con cada push a `main` (y con etiquetas `v*.*.*`). Un runner limpio de GitHub construye la imagen y la publica en **GitHub Container Registry (GHCR)**.

| Paso | Acción |
|---|---|
| Descargar el código | `actions/checkout@v7` |
| Preparar Buildx | `docker/setup-buildx-action@v4` |
| Autenticarse en el registry | `docker/login-action@v4` con el `GITHUB_TOKEN` temporal |
| Calcular etiquetas | `docker/metadata-action@v6` |
| Construir y publicar | `docker/build-push-action@v7` con caché de capas |

Etiquetas que genera:

| Etiqueta | Cuándo | Para qué |
|---|---|---|
| `latest` | Push a `main` | Apunta a lo último de `main` (móvil). |
| `sha-xxxxxxx` | Cada commit | **Inmutable**, atada al commit que la originó. |
| `1.2.3` | Al publicar la etiqueta `v1.2.3` | Versión semántica. |

Nombre de la imagen: `ghcr.io/gomers16/docker-despliegue-sena`.

Descargarla en cualquier equipo:

```bash
docker pull ghcr.io/gomers16/docker-despliegue-sena:latest
# o una versión exacta
docker pull ghcr.io/gomers16/docker-despliegue-sena:sha-ad5fca4
```

> Si el paquete es privado, antes ejecute `docker login ghcr.io -u <usuario>` con un token con permiso `read:packages`.

Publicar una versión semántica:

```bash
git tag -a v1.0.0 -m "primera version"
git push origin v1.0.0
```

**Despliegue en producción:** en un servidor nunca se usa `latest`; se despliega una etiqueta inmutable (`sha-...` o `v1.2.3`). Así siempre se sabe qué versión corre y se puede volver atrás apuntando a la etiqueta anterior. En el servidor, el `docker-compose.yml` usa `image:` en lugar de `build:`.

---

## 12. Seguridad aplicada

- **Aislamiento:** solo el proxy publica un puerto; `api` y `db` solo son alcanzables desde la red interna.
- **Usuario sin privilegios:** la API corre como `appuser` (UID 1001), no como root.
- **Secretos fuera del código:** las credenciales llegan por variables de entorno; `.env` está en `.gitignore` y `.dockerignore`.
- **Imágenes con versión explícita:** ninguna usa `latest` (reproducibilidad).
- **Imagen mínima:** multi-etapa y bases `slim`/`alpine`.
- **Token temporal en CI:** el flujo usa `GITHUB_TOKEN`, que GitHub crea y destruye en cada corrida.
- **Errores sin fugas:** `/db` no expone el mensaje completo de la excepción.
- **Reinicio automático:** `restart: unless-stopped` en los tres servicios, y `healthcheck` en la base de datos para ordenar el arranque.

---

## 13. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `port is already allocated` | Otro programa usa el `8080` | Libérelo o cambie el mapeo en `docker-compose.yml`. |
| `permission denied ... docker.sock` | El cambio de grupo no se aplicó | Cierre sesión (Ubuntu) o ejecute `wsl --shutdown` (WSL) y vuelva a entrar. |
| `Cannot connect to the Docker daemon` | El servicio está detenido | Ubuntu/WSL: `sudo systemctl enable --now docker`. macOS: `colima start`. |
| `503 Bad Gateway` en Nginx | El proxy no encuentra la API | Revise `docker compose ps` y `docker compose logs api`. |
| `/db` responde 503 | La BD no está lista o la clave no coincide | Espere a `healthy`; revise `DB_NAME` y `DB_ADMIN_PASSWORD`. |
| `db` reinicia en bucle | Volumen en la ruta equivocada (PostgreSQL 18) | Monte el volumen en `/var/lib/postgresql` (ver sección 14). |
| El volumen no abre con PostgreSQL 18 | Volumen creado con otra versión mayor | `docker volume rm` del volumen viejo, o use otro nombre. |
| `exec format error` / `no such file or directory` | Finales de línea de Windows (CRLF) | Use `.gitattributes` con `* text=auto eol=lf` y reconstruya. |
| `no space left on device` | Imágenes y capas acumuladas | `docker system prune -a` (borra lo que no se use). |
| WSL: `System has not been booted with systemd` | systemd desactivado | Cree `/etc/wsl.conf` (ver 4B) y `wsl --shutdown`. |
| WSL: `There is no distribution with the supplied name` | WSL antiguo | `wsl --install --no-distribution`, `wsl --update`, o instale con `-d Ubuntu`. |
| WSL se queda en blanco o se cuelga | Procesos de WSL bloqueados | PowerShell: `taskkill /F /IM wslservice.exe`, luego `wsl --shutdown`. |
| VS Code se conecta a `docker-desktop` | Distro predeterminada incorrecta | `wsl --set-default Ubuntu`. |
| `docker: 'compose' is not a docker command` (macOS) | Plugin sin registrar | Agregue `cliPluginsExtraDirs` a `~/.docker/config.json`. |
| `denied: permission_denied: write_package` (Actions) | Falta permiso de escritura | Settings → Actions → General → Workflow permissions → **Read and write**. |
| `invalid reference format: repository name must be lowercase` | Mayúsculas en el nombre de la imagen | Use minúsculas (el workflow ya las normaliza). |

---

## 14. Notas sobre PostgreSQL 18 y Compose v5

Dos diferencias respecto a versiones anteriores, detectadas durante las pruebas:

1. **Ruta del volumen de PostgreSQL 18.** Desde la versión 18, la imagen oficial guarda los datos en un subdirectorio versionado y el volumen debe montarse en `/var/lib/postgresql`, **no** en `/var/lib/postgresql/data`. Con la ruta antigua el contenedor `db` entra en bucle de reinicio. Por eso el compose usa:

   ```yaml
   volumes:
     - pgdata:/var/lib/postgresql
   ```

2. **`docker compose port` en Compose v5.** Cuando el puerto no está publicado, `docker compose port db 5432` imprime `:0` y termina con código 0, por lo que un `|| echo "..."` nunca se ejecuta. Para comprobar el aislamiento use `docker port <contenedor>` (sale vacío) y el `curl` al puerto 5432 del host (debe fallar).

---

## Licencia y autoría

Proyecto formativo SENA, Centro de Comercio y Servicios, Regional Tolima. Autor: DIEGO MAURICIO GOMEZ RODRIGUEZ (`Gomers16`).
