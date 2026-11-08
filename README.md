# CRM DATA SERVICE

CRM comercial para DATA SERVICE. Monorepo con backend (FastAPI + PostgreSQL) y frontend (React + Vite).

## Estructura

```
CRM-VENTAS/
├── apps/
│   ├── api/          # Backend FastAPI (Python 3.12+)
│   └── web/          # Frontend React + Vite (Node 22+)
├── infra/
│   ├── compose.dev.yml   # Entorno de desarrollo (Docker)
│   ├── compose.prod.yml  # Entorno de producción (VPS)
│   └── docker/           # Dockerfiles
├── .env.example      # Plantilla de variables de entorno
└── .env              # Variables de entorno (NO se versiona)
```

## Requisitos

Para ejecutar el proyecto en otro equipo necesitas:

- **Git** (para clonar/copiar el proyecto)
- **Docker Desktop** (recomendado) — incluye Docker Compose
  - o, si no usas Docker: **Python 3.12+**, **Node.js 22+**, **PostgreSQL 16** con extensiones `pg_trgm` y `unaccent`

## Opción 1 — Con Docker (recomendado)

Es la forma más sencilla: levanta base de datos, API, worker y frontend con un solo comando.

### 1. Copiar el proyecto al otro equipo

```bash
git clone <url-del-repo> CRM-VENTAS
cd CRM-VENTAS
```

> Si no usas Git, copia la carpeta completa (sin `node_modules`, `dist`, `.venv`, `__pycache__`).

### 2. Crear el archivo `.env`

```bash
cp .env.example .env
```

Edita `.env` y cambia al menos:

- `JWT_SECRET` (genera uno con `python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- `INITIAL_ADMIN_PASSWORD` (contraseña del admin inicial)
- En producción: `POSTGRES_PASSWORD`, `DOMAIN`, `LETSENCRYPT_EMAIL`, `COOKIE_SECURE=true`

### 3. Levantar en desarrollo

```bash
docker compose -f infra/compose.dev.yml up -d --build
```

Servicios:

- Web (Vite): http://localhost:5173
- API: http://localhost:8000 (docs en http://localhost:8000/api/docs)
- PostgreSQL: localhost:5432 (usuario `crm` / clave `crm` / db `crm`)

El contenedor de la API ejecuta automáticamente las migraciones (`alembic upgrade head`) y la semilla base (`python -m app.seeds.base`), que crea el administrador inicial si no existe.

### 4. Detener

```bash
docker compose -f infra/compose.dev.yml down
```

Para borrar también los volúmenes (base de datos):

```bash
docker compose -f infra/compose.dev.yml down -v
```

### 5. Producción (VPS)

```bash
docker compose -f infra/compose.prod.yml --env-file .env up -d --build
```

Publica en los puertos 80/443 con Nginx + HTTPS (Let's Encrypt). Requiere un dominio apuntando al servidor y los valores de `.env` de producción.

## Opción 2 — Sin Docker (ejecución manual)

### Backend (API)

1. Instalar PostgreSQL 16 y crear usuario/db:

```sql
CREATE USER crm WITH PASSWORD 'crm';
CREATE DATABASE crm OWNER crm;
\c crm
CREATE EXTENSION pg_trgm;
CREATE EXTENSION unaccent;
-- base de pruebas (opcional)
CREATE DATABASE crm_test OWNER crm;
\c crm_test
CREATE EXTENSION pg_trgm;
CREATE EXTENSION unaccent;
```

2. Preparar el entorno Python:

```bash
cd apps/api
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements-dev.txt
```

3. Crear `apps/api/.env` (o usar el `.env` de la raíz exportando las variables). Asegúrate de que `DATABASE_URL=postgresql+psycopg://crm:crm@localhost:5432/crm`.

4. Migrar y sembrar:

```bash
alembic upgrade head
python -m app.seeds.base
```

5. Arrancar la API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

6. (Opcional) Arrancar el worker (tareas programadas):

```bash
python -m app.workers.scheduler
```

### Frontend (Web)

```bash
cd apps/web
npm install
npm run dev
```

El frontend corre en http://localhost:5173 y hace proxy de `/api` a http://localhost:8000.

## Credenciales iniciales

- Email: `admin@dataservice.pe` (configurable en `.env` → `INITIAL_ADMIN_EMAIL`)
- Contraseña: `Admin123!` (configurable en `.env` → `INITIAL_ADMIN_PASSWORD`)

## Comandos útiles

```bash
# Tests backend
cd apps/api && pytest

# Tests frontend
cd apps/web && npm test

# Typecheck frontend
cd apps/web && npm run typecheck

# Build frontend
cd apps/web && npm run build

# Regenerar tipos de API (OpenAPI → TypeScript)
cd apps/web && npm run gen:api
```

## Notas

- El `.env` no se versiona (está en `.gitignore`). En cada equipo hay que crearlo a partir de `.env.example`.
- La semilla inicial solo crea el admin si no existe; es idempotente.
- En desarrollo la cookie de refresh usa `SameSite=Strict` y `COOKIE_SECURE=false`, por lo que todo debe servirse por `localhost`.
