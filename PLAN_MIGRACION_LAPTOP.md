# PLAN DE MIGRACIÓN: CRM-VENTAS A LAPTOP

> **Instrucción para el agente IA que ejecute esto:**
> Eres un agente de software instalado en una laptop Windows. Tu misión es recibir este proyecto CRM-VENTAS y dejarlo funcionando completamente en la laptop usando Docker Desktop. Debes ejecutar paso a paso cada sección, verificar resultados y detenerte a pedir ayuda al usuario solo si encuentras un error que no puedas resolver automáticamente.

---

## 1. REQUISITOS PREVIOS DE LA LAPTOP

Antes de empezar, confirma que la laptop cumple lo siguiente:

| Requisito | Mínimo | Recomendado |
|---|---|---|
| Sistema operativo | Windows 10 64-bit | Windows 11 |
| Procesador | 64-bit con virtualización | Intel i5 / AMD Ryzen 5 o superior |
| RAM | 8 GB | 16 GB |
| Espacio libre en disco | 15 GB | 25 GB |
| Virtualización | Habilitada en BIOS | Habilitada en BIOS |
| WSL2 | Instalado | Instalado |
| Puertos libres | 5173, 8000, 5432 | 5173, 8000, 5432 |

### Cómo verificar la virtualización
1. Abre el **Administrador de tareas**.
2. Ve a la pestaña **Rendimiento** → **CPU**.
3. Busca **Virtualización: Habilitada**.
4. Si dice **Deshabilitada**, reinicia la laptop, entra al BIOS/UEFI y habilita **Intel VT-x** o **AMD-V**.

### Cómo verificar WSL2
Ejecuta en PowerShell:

```powershell
wsl --status
```

Si no está instalado, ejecuta:

```powershell
wsl --install
```

Luego reinicia la laptop.

---

## 2. COPIAR EL PROYECTO A LA LAPTOP

El proyecto debe llegar a la laptop en una carpeta llamada `CRM-VENTAS`.

### 2.1. Si se copia por USB, nube, red u otro medio físico

Copia la carpeta completa excepto estas carpetas/archivos (se regeneran solos):

```
CRM-VENTAS/
├── .git/                   # opcional, solo si no se va a usar git
├── apps/web/node_modules/
├── apps/web/dist/
├── apps/api/.venv/
├── apps/api/__pycache__/
├── apps/api/**/__pycache__/
└── apps/api/tmp_debug.xlsx # opcional, es un archivo temporal
```

### 2.2. Si se usa Git

Clona el repositorio:

```powershell
git clone <URL-DEL-REPO> CRM-VENTAS
cd CRM-VENTAS
```

### 2.3. Ubicación recomendada en la laptop

Coloca la carpeta en una ruta sin espacios ni caracteres especiales:

```
C:\Users\<tu-usuario>\Documents\CRM-VENTAS
```

o

```
C:\dev\CRM-VENTAS
```

> **Nota importante:** Si la ruta tiene espacios, algunos comandos de Docker pueden fallar. Evita rutas como `C:\Users\Mi Usuario\Mis Documentos\...`.

---

## 3. INSTALAR DOCKER DESKTOP

### 3.1. Descargar e instalar

1. Ve a https://www.docker.com/products/docker-desktop
2. Descarga el instalador para Windows.
3. Ejecuta el instalador como administrador.
4. **Asegúrate de marcar la opción para usar WSL2** en lugar de Hyper-V (es la opción recomendada).
5. Completa la instalación y reinicia si lo pide.
6. Abre **Docker Desktop** y espera a que termine de iniciar (aparece la interfaz verde).

### 3.2. Verificar que Docker funciona

En PowerShell ejecuta:

```powershell
docker --version
docker compose version
```

Ambos deben mostrar una versión sin errores.

---

## 4. CONFIGURAR EL ARCHIVO `.env`

Dentro de la carpeta `CRM-VENTAS` debe existir un archivo `.env`. Si no existe, créalo a partir de `.env.example`:

```powershell
cd CRM-VENTAS
copy .env.example .env
```

Abre `.env` con un editor de texto y asegúrate de que tenga al menos estos valores:

```env
# ── Entorno ─────────────────────────────────────────────
ENVIRONMENT=development
LOG_LEVEL=INFO

# ── Base de datos ───────────────────────────────────────
DATABASE_URL=postgresql+psycopg://crm:crm@localhost:5432/crm
POSTGRES_USER=crm
POSTGRES_PASSWORD=crm
POSTGRES_DB=crm

# ── Seguridad ───────────────────────────────────────────
JWT_SECRET=<genera uno nuevo>
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=7
COOKIE_SECURE=false
CORS_ORIGINS=["http://localhost:5173"]

# ── Administrador inicial ───
INITIAL_ADMIN_EMAIL=admin@dataservice.pe
INITIAL_ADMIN_PASSWORD=<pon una contraseña segura>
INITIAL_ADMIN_NAME=Administrador del sistema

# ── Producción (no se usa en desarrollo, déjalo como está) ──
DOMAIN=crm.tu-dominio.pe
LETSENCRYPT_EMAIL=sistemas@tu-dominio.pe
```

### 4.1. Generar un nuevo `JWT_SECRET`

Ejecuta en PowerShell:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Si Python no está instalado, usa este comando en PowerShell para generar un secreto aleatorio:

```powershell
-join ((48..57) + (65..90) + (97..122) + 45 + 95 | Get-Random -Count 64 | ForEach-Object { [char]$_ })
```

Copia el resultado y pégalo en `JWT_SECRET`.

> **Importante:** No uses el `JWT_SECRET` que vino en el `.env` original. En la laptop nueva se debe generar uno nuevo por seguridad.

---

## 5. LEVANTAR EL PROYECTO CON DOCKER

### 5.1. Abrir terminal en la carpeta del proyecto

Abre **PowerShell** como administrador (o como usuario normal si Docker Desktop está bien configurado) y navega a la carpeta:

```powershell
cd C:\Users\<tu-usuario>\Documents\CRM-VENTAS
```

Reemplaza `<tu-usuario>` con el nombre de usuario de la laptop.

### 5.2. Ejecutar Docker Compose

Ejecuta:

```powershell
docker compose -f infra/compose.dev.yml up -d --build
```

Este comando:
1. Descarga las imágenes de Docker necesarias (PostgreSQL, Python, Node).
2. Construye la imagen del backend.
3. Crea y arranca los contenedores: `db`, `api`, `worker`, `web`.
4. Ejecuta automáticamente las migraciones de la base de datos.
5. Crea el usuario administrador inicial si no existe.

### 5.3. Esperar la primera vez

La primera ejecución puede tardar entre **5 y 20 minutos** dependiendo de la velocidad de internet y la laptop. Docker descargará varias imágenes. No cierres la terminal.

### 5.4. Verificar que los contenedores estén corriendo

Ejecuta:

```powershell
docker compose -f infra/compose.dev.yml ps
```

Debes ver los 4 servicios con estado `running` o `healthy`:

```
NAME                           IMAGE                          COMMAND                  SERVICE   CREATED          STATUS          PORTS
infra-db-1                     postgres:16-alpine             "docker-entrypoint.s…"   db        ...              healthy         0.0.0.0:5432->5432/tcp
infra-api-1                    ...                            "sh -c 'alembic upgr…'"  api       ...              running         0.0.0.0:8000->8000/tcp
infra-worker-1                 ...                            "python -m app.worker…"  worker    ...              running
infra-web-1                    node:22-alpine                 "docker-entrypoint.s…"  web       ...              running         0.0.0.0:5173->5173/tcp
```

Si alguno dice `Restarting` o `Exit`, revisa los logs:

```powershell
docker compose -f infra/compose.dev.yml logs --tail 100 <nombre-del-servicio>
```

Por ejemplo:

```powershell
docker compose -f infra/compose.dev.yml logs --tail 100 api
```

---

## 6. VERIFICAR QUE TODO FUNCIONA

### 6.1. Comprobar servicios en el navegador

Abre el navegador de la laptop y verifica estas URLs:

| URL | Qué debe mostrar |
|---|---|
| http://localhost:5173 | El login del CRM |
| http://localhost:8000/api/docs | Documentación interactiva de la API (Swagger UI) |
| http://localhost:8000/api/health | Un JSON tipo `{"status":"ok"}` |

### 6.2. Probar el login

En http://localhost:5173 ingresa con:

- **Email:** `admin@dataservice.pe`
- **Contraseña:** la que pusiste en `INITIAL_ADMIN_PASSWORD`

Debes poder iniciar sesión y ver el panel principal del CRM.

### 6.3. Verificar logs generales

Si algo no carga, revisa los logs de todos los servicios:

```powershell
docker compose -f infra/compose.dev.yml logs -f
```

Presiona `Ctrl + C` para salir de los logs.

---

## 7. COMANDOS ÚTILES PARA EL DÍA A DÍA

### Detener el proyecto

```powershell
docker compose -f infra/compose.dev.yml down
```

### Detener y borrar la base de datos (¡cuidado!)

```powershell
docker compose -f infra/compose.dev.yml down -v
```

### Reiniciar el proyecto

```powershell
docker compose -f infra/compose.dev.yml restart
```

### Ver logs en tiempo real

```powershell
docker compose -f infra/compose.dev.yml logs -f
```

### Ver logs de un solo servicio

```powershell
docker compose -f infra/compose.dev.yml logs -f api
```

### Reconstruir después de cambios importantes

```powershell
docker compose -f infra/compose.dev.yml up -d --build
```

---

## 8. SOLUCIÓN DE PROBLEMAS COMUNES

### 8.1. Error: "Ports are not available" o "address already in use"

Significa que los puertos 5173, 8000 o 5432 ya están ocupados.

Para ver qué programa los ocupa:

```powershell
netstat -ano | findstr :5173
netstat -ano | findstr :8000
netstat -ano | findstr :5432
```

Si PostgreSQL está instalado localmente en la laptop, detén el servicio:

```powershell
net stop postgresql-x64-16
```

(o el nombre del servicio que corresponda).

### 8.2. Error: "Docker Desktop is not running"

Abre Docker Desktop y espera a que termine de cargar completamente.

### 8.3. Error: "WSL2 installation is incomplete"

Ejecuta:

```powershell
wsl --update
```

Luego reinicia la laptop.

### 8.4. El frontend muestra error de conexión con la API

Verifica que el contenedor `api` esté corriendo:

```powershell
docker compose -f infra/compose.dev.yml ps
```

Y revisa sus logs:

```powershell
docker compose -f infra/compose.dev.yml logs --tail 100 api
```

### 8.5. El login falla con credenciales correctas

Es posible que el usuario admin no se haya creado. Revisa los logs del API y busca errores de la base de datos. Si es necesario, reinicia con:

```powershell
docker compose -f infra/compose.dev.yml restart api
```

### 8.6. Docker tarda mucho o se queda congelado

En laptops con poca RAM, Docker puede ser lento. Asegúrate de:
- Cerrar navegadores y programas pesados.
- Asignar más memoria a Docker Desktop:
  - Abre Docker Desktop → Settings → Resources → Memory.
  - Aumenta a 4 GB o más si es posible.

---

## 9. ALTERNATIVA SIN DOCKER (SOLO SI DOCKER NO FUNCIONA)

Si Docker Desktop no puede instalarse o no corre en la laptop, instala manualmente:

1. **PostgreSQL 16** desde https://www.postgresql.org/download/windows/
2. **Python 3.12+** desde https://www.python.org/downloads/
3. **Node.js 22+** desde https://nodejs.org/

Luego ejecuta en orden:

```powershell
# --- Base de datos ---
# Usa pgAdmin o psql para crear la base de datos:
CREATE USER crm WITH PASSWORD 'crm';
CREATE DATABASE crm OWNER crm;
\c crm
CREATE EXTENSION pg_trgm;
CREATE EXTENSION unaccent;

# --- Backend ---
cd apps/api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
alembic upgrade head
python -m app.seeds.base
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# --- Frontend (en otra terminal) ---
cd apps/web
npm install
npm run dev
```

Accede a http://localhost:5173.

---

## 10. CHECKLIST FINAL

Antes de dar por terminada la tarea, confirma que:

- [ ] Docker Desktop está instalado y corriendo.
- [ ] El proyecto `CRM-VENTAS` está copiado en la laptop.
- [ ] El archivo `.env` existe y tiene `JWT_SECRET` nuevo.
- [ ] `INITIAL_ADMIN_PASSWORD` fue cambiado por una contraseña segura.
- [ ] Se ejecutó `docker compose -f infra/compose.dev.yml up -d --build` sin errores.
- [ ] Los 4 servicios aparecen como `running`/`healthy`.
- [ ] http://localhost:5173 muestra el login.
- [ ] http://localhost:8000/api/docs muestra la documentación.
- [ ] Se puede iniciar sesión con `admin@dataservice.pe`.
- [ ] Se informó al usuario el espacio en disco final utilizado.

---

## 11. NOTAS PARA EL USUARIO FINAL

- El CRM quedará accesible solo desde la laptop en la que se instale, por las URLs `http://localhost:5173` y `http://localhost:8000`.
- Para usar el CRM, primero debe estar corriendo Docker Desktop.
- Si apagas la laptop, al encenderla deberás abrir Docker Desktop y ejecutar:
  ```powershell
  docker compose -f infra/compose.dev.yml up -d
  ```
- No subas el archivo `.env` a Git. Ya está configurado en `.gitignore`.

---

**Fin del plan.**
