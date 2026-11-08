# Plan de trabajo — CRM DATA SERVICE (React + FastAPI)

## 0. Contexto

DATA SERVICE registra hoy su gestión comercial en el Excel **FOR-VEN-001 INFORME SEMANAL DE VENTAS V03.xlsx**. Se construirá un CRM web que lo reemplace, para Ventas, Gerencia y Administración, que gestione prospectos **personas naturales (DNI) y jurídicas (RUC)** en un único módulo y cubra todo el ciclo: registro → seguimiento → oportunidad → cotización → venta/cliente o pérdida.

Principios rectores:
- *"Cada prospecto tiene definido su tipo de persona, estado, responsable, historial y próxima acción."*
- *"Todo lo que ocurre en Ventas se convierte en información medible y accionable."*

Directorio del proyecto (`C:\Users\PC\Downloads\CRM-VENTAS`) está **vacío**: se parte de cero.
Decisiones confirmadas con el usuario:
- **Pipeline basado en Oportunidades separadas** (un prospecto/cliente puede tener varias).
- **Perder una oportunidad NO pierde al prospecto ni al cliente** (§5.0).
- **Despliegue en VPS/nube con Docker**.
- **Paleta corporativa naranja, negro y blanco**, UI moderna tipo SaaS, con experiencia móvil real (§5.1).
- **Catálogo real de 31 productos** con precios finales en soles (§4.6). El precio registrado es siempre el precio final.
- **Logo y color oficiales:** `DSCONT_CRM.png` (DSCONT Software) y naranja **`#E03E0F`**.
- **Datos de ejemplo inventados** (seed demo + un Excel FOR-VEN-001 sintético para probar el importador) (§9).

---

## 1. Contraste entre los dos documentos (resolución)

| Tema | Prompt Maestro (antiguo) | Solicitud final (nueva) | Decisión en este plan |
|---|---|---|---|
| Stack | Vue 3 + NestJS + Prisma | React + FastAPI + SQLAlchemy | **React + FastAPI** (ver §2) |
| Tipo de prospecto | Solo empresas (RUC obligatorio) | Natural (DNI) + Jurídica (RUC) + otros docs a futuro | Modelo **"Party" único** con `person_type` y `document_type` catalogado |
| Contactos | N contactos por empresa | Igual para jurídica | Natural: la persona es el contacto principal; contactos adicionales opcionales |
| MVVM | Obligatorio y estricto | "Sin forzar patrones" | MVVM pragmático: hooks = ViewModel, organizado por *feature* |
| Monorepo `packages/shared/types` | Tipos compartidos TS | — | Tipos TS **generados desde OpenAPI** (no hay TS en backend) |
| Pipeline | Etapa en prospecto + "N oportunidades" (contradictorio) | — | **Etapa vive en Oportunidad**; prospecto tiene *estado de ciclo de vida* |
| Código "Producto vendido A/N" | Tratado como producto | — | A/N = **Actualización / Nuevo** → mapea a `tipo comercial`, no al catálogo de productos |
| Interés "M/P/N" vs Alto/Regular/Bajo | Inconsistente | — | Catálogo configurable con `legacy_code`; confirmar con el Excel real |
| Contacto P/R | Presencial / Remoto | — | Catálogo **modalidad de contacto** (distinto de forma de contacto C/T/V/W/F/R) |
| Usuario eliminado | Migrar prospectos con historial | — | Usuarios nunca se borran: **desactivación + asistente de reasignación** (§6.3) |

**Todo lo demás del Prompt Maestro se conserva** (alertas, scoring, duplicados, import/export, auditoría, filtros guardados, forecast, etc.). La solicitud nueva llegó truncada en §6.1 ("Ventas registr…"); se asume que el resto coincide con el Prompt Maestro.

---

## 2. Evaluación del stack

React + FastAPI es **adecuado** y no presenta problemas de fondo. Ajustes/complementos:

**Frontend:** React 18/19 + TS + Vite, React Router, TanStack Query, Zustand (solo sesión/UI global), React Hook Form + Zod, Tailwind + shadcn/ui, Recharts.
Se añaden: **TanStack Table** (tablas server-side), **dnd-kit** (Kanban), **openapi-typescript + openapi-fetch** (cliente tipado generado), **date-fns** (zona `America/Lima`), **cmdk** (Ctrl+K, ya incluido en shadcn), Vitest + Testing Library + **Playwright** (E2E), MSW (mocks).

**Backend:** Python 3.12, FastAPI, Pydantic v2 + pydantic-settings, **SQLAlchemy 2 (sync) + psycopg 3**, Alembic, Pytest.
- Sync en vez de async: el volumen (decenas de usuarios) no lo requiere y simplifica pruebas y transacciones; FastAPI ejecuta endpoints sync en threadpool.
Se añaden: **argon2** (pwdlib) para contraseñas, **PyJWT**, **slowapi** (rate limit), **openpyxl** (import/export Excel), **APScheduler** en contenedor *worker* (alertas), **structlog** (logs JSON), **ruff + mypy**, **testcontainers/Postgres en Docker** para tests de integración, **factory-boy**.

**BD:** PostgreSQL 16 con extensiones `pg_trgm` y `unaccent` (búsqueda rápida y tolerante a tildes/similares).

**Infra:** Docker + Compose (dev/prod), Nginx (reverse proxy + estáticos + HTTPS Let's Encrypt), GitHub Actions (lint, tests, build), backups `pg_dump` programados a almacenamiento externo.

---

## 3. Arquitectura

### 3.1 Estructura del repositorio (monorepo)
```
crm-dataservice/
├─ apps/
│  ├─ api/                     # FastAPI
│  └─ web/                     # React
├─ infra/
│  ├─ docker/ (Dockerfiles, nginx.conf)
│  ├─ compose.dev.yml  compose.prod.yml
│  └─ backup/ (scripts pg_dump + restore)
├─ docs/ (arquitectura, ADRs, modelo de datos, import/export, manual usuario)
├─ .github/workflows/
├─ .env.example
└─ README.md
```

### 3.2 Backend — por módulo funcional (Clean Architecture pragmática)
```
apps/api/app/
├─ core/            config, security (jwt, hashing), db (session, base, mixins),
│                   errors (excepciones de dominio → respuestas HTTP), logging, pagination, permissions
├─ shared/          tipos comunes, filtros, utilidades de fechas, unit of work
├─ modules/
│  ├─ auth/ users/ rbac/ catalogs/ settings/
│  ├─ prospects/ (incluye contacts, duplicates, assignments)
│  ├─ interactions/ tasks/ opportunities/ products/ quotes/ sales/
│  ├─ tags/ attachments/ notifications/ alerts/ scoring/
│  ├─ dashboard/ reports/ import_export/ audit/ saved_views/ search/
│  └─ <modulo>/
│       ├─ api/router.py            # Controllers: solo HTTP, deps, permisos
│       ├─ schemas.py               # DTOs Pydantic (Create/Update/Read/Filter)
│       ├─ application/use_cases.py # Casos de uso (1 clase/función por caso)
│       ├─ domain/                  # Entidades/reglas puras, enums, value objects, errores
│       ├─ infrastructure/models.py # Modelos SQLAlchemy
│       ├─ infrastructure/repository.py  # Implementación
│       └─ repository.py            # Protocol (interfaz) del repositorio
├─ workers/         scheduler.py (jobs de alertas, vencimientos)
├─ migrations/      Alembic
└─ tests/           unit/ integration/ api/ (por módulo)
```
Reglas: routers delgados; casos de uso reciben repositorios por inyección (`Depends`); el dominio no importa FastAPI ni SQLAlchemy; la auditoría y los eventos (asignación, cambio de etapa) se emiten desde casos de uso mediante un **bus de eventos in-process** simple (notificaciones/auditoría se suscriben → bajo acoplamiento).

### 3.3 Frontend — por feature (MVVM natural en React)
```
apps/web/src/
├─ app/            router, providers (QueryClient, theme), layout (sidebar, topbar, Ctrl+K)
├─ shared/
│  ├─ api/         cliente openapi-fetch generado + interceptor refresh token
│  ├─ ui/          componentes shadcn + propios (DataTable, StatusBadge, EmptyState,
│  │               CatalogSelect, DateRangeFilter, KpiCard, Timeline, ConfirmDialog)
│  ├─ hooks/ lib/ (formatos moneda PEN, fechas Lima, permisos <Can/>)
│  └─ stores/      zustand: sesión, preferencias UI
└─ features/
   └─ prospects/
      ├─ model/      tipos, esquemas Zod, mapeos
      ├─ api/        services (llamadas) + query keys
      ├─ hooks/      ViewModels: useProspectList, useProspectForm, useProspectDetail
      ├─ components/ vistas parciales (ProspectCard, QuickCreateDialog, ContactList…)
      └─ pages/      ProspectListPage, ProspectDetailPage
```
Features: auth, dashboard, prospects, interactions, tasks, pipeline, quotes, sales, products, reports, import-export, notifications, admin (users, roles, catalogs, settings, audit).
"Repository" en frontend: no se crea capa extra; TanStack Query + services cumple ese rol.

---

## 4. Modelo de datos (PostgreSQL)

Convenciones: PK `id` (bigint identity) + `public_id` UUID expuesto en API; `created_at/updated_at/created_by/updated_by`; `deleted_at` (soft delete) en entidades comerciales; montos `numeric(14,2)`; moneda `PEN` por defecto con campo `currency`; timestamps `timestamptz`.

### 4.1 Seguridad
- `users` (email único, nombre, password_hash, is_active, last_login_at, deactivated_at)
- `roles`, `permissions` (código p.ej. `prospects.read.all`, `prospects.read.own`), `user_roles`, `role_permissions`
- `refresh_tokens` (hash, user, expires_at, revoked_at, family_id para rotación)

### 4.2 Catálogos
- `catalogs` (code: `contact_channel`, `contact_mode`, `interest_level`, `contact_result`, `opportunity_type`, `prospect_source`, `priority`, `loss_reason`, `task_type`, `document_type`, …)
- `catalog_options` (catalog_id, code, name, description, color, sort_order, is_active, legacy_code, weight numeric, metadata jsonb, is_system)
- Tablas dedicadas cuando hay reglas propias:
  - `pipeline_stages` (name, order, default_probability, is_won, is_lost, stale_days_warning, stale_days_critical)
  - `products` (code, name, description, category, reference_price, is_active, legacy_code)
  - `tags` (name, color, description)
- `ubigeo` (departamento/provincia/distrito Perú, seed INEI)

Seeds iniciales: forma de contacto C/T/V/W/F/R, modalidad P/R, logro C/D/V (+ "Sin respuesta", "Contestó", "Volver a llamar"), tipo comercial A/N, interés Alto/Regular/Bajo, tipo documento DNI/RUC/CE/Pasaporte, motivos de pérdida, etapas de pipeline.

### 4.3 Núcleo comercial
- `prospects`
  - `code` correlativo (PRO-000123), `person_type` (NATURAL | JURIDICA)
  - `document_type_id`, `document_number` — índice único parcial `(document_type_id, document_number) WHERE deleted_at IS NULL AND document_number IS NOT NULL`
  - Natural: `first_name`, `last_name`, `birth_date?`
  - Jurídica: `legal_name`, `trade_name`
  - `display_name` (columna generada/actualizada: razón social o nombres)
  - `email`, `phone`, `phone_alt`, `whatsapp`, `address`, `ubigeo_id`
  - `source_id`, `acquisition_channel_id`, `interest_level_id`, `priority_id`
  - `relationship_type` (PROSPECTO | CLIENTE) — una vez CLIENTE, nunca retrocede automáticamente
  - `status` (ACTIVO, EN_PAUSA, DESCARTADO, NO_CALIFICA, INACTIVO) — solo cambia por acción explícita con motivo (ver §5.0)
  - `converted_at`, `converted_by`, `discard_reason_id`
  - `owner_id` (vendedor actual)
  - **Campos desnormalizados mantenidos por casos de uso** (para listados/alertas rápidos): `first_contact_at`, `last_contact_at`, `next_action_at`, `next_action_desc`, `interaction_count`, `last_result_id`, `score`, `score_breakdown jsonb`
  - `notes`, `legacy_source`, `legacy_row`, `legacy_code`, `legacy_attempts`
  - Índices: trigram GIN sobre `unaccent(display_name)`, `trade_name`, `email`, `phone`; btree en `owner_id`, `relationship_type`, `status`, `next_action_at`, `created_at`
- `prospect_contacts` (prospect, full_name, position, area, email, phone, whatsapp, is_primary, notes)
- `prospect_assignments` (prospect, from_user, to_user, assigned_by, reason, assigned_at) — historial inmutable
- `prospect_tags` (N:M)
- `prospect_status_history` (from/to relationship_type y status, changed_by, reason)

### 4.4 Actividad
- `interactions` (prospect, opportunity?, user, occurred_at, channel_id, mode_id, contact_id?, result_id, interest_level_id, attempt_number (calculado), notes, next_action_desc, next_action_at, stage_before, stage_after)
- `tasks` (prospect, opportunity?, assignee, type_id, title, description, due_at, priority_id, status PENDING/DONE/CANCELLED, completed_at, remind_at) — "Vencida" es **derivado** (`PENDING AND due_at < now`), no se almacena.
- `notifications` (user, type, title, body, entity_type, entity_id, read_at, dedupe_key único)

### 4.5 Oportunidades, cotizaciones, ventas
- `opportunities` (prospect, owner, title, opportunity_type_id (Actualización/Nuevo), stage_id, amount_estimated, probability, expected_close_date, status OPEN/WON/LOST, closed_at, loss_reason_id, stage_entered_at)
- `opportunity_stage_history` (from, to, changed_by, changed_at, duration_in_prev_stage) → tiempo por etapa, aging
- `quotes` (code COT-2026-0001, prospect, opportunity, seller, opportunity_type_id, issue_date, valid_until, status, subtotal, discount, total, currency, notes) + `quote_items` (product, description, qty, unit_price, discount, line_total) — precios de ítem **copiados** del producto al cotizar (cambios futuros de precio no alteran cotizaciones históricas)
- `sales` (code, prospect, opportunity?, quote?, seller, sale_date, opportunity_type_id, subtotal, discount, total, notes) + `sale_items`
- Estados de cotización: Borrador, Enviada, Recibida, En negociación, Aceptada, Rechazada, Vencida, Convertida.

### 4.6 Productos de DATA SERVICE (seed obligatorio de producción)
- `product_categories` (code, name, sort_order) con 6 categorías:
  DS-CONT Productos (4) · DS-CONT Licencias SaaS anual (6) · DS_BUSINESS Productos (5) · DS_BUSINESS Licencias SaaS INHOUSE (5) · DS_BUSINESS Acceso SaaS (2) · DSCONT CLOUD (9) = **31 productos**.
- `products` ampliado: `code` (p.ej. DSCPRO001, DSCSAA0003, DSBSAA017, DSCCLOUD05), `name`, `category_id`, `product_line` (DS-CONT, DS_BUSINESS, DSCONT CLOUD), `kind` (LICENCIA_PERPETUA, SUSCRIPCION, USUARIO_ADICIONAL, DEMO), `billing_period` (UNICO, SEMANAL, MENSUAL, ANUAL), `list_price` (S/, precio final), `is_active`.
- Cálculo simple: `line_total = qty × unit_price − descuento`; `total = Σ line_total − descuento global`.
- El seed carga los 31 productos exactamente con los códigos y precios entregados (incluido el plan demo S/ 0.00). Se marcará para revisión el nombre "DS_BUSSINES PEQUEÑA" (posible errata de "DS_BUSINESS"); el administrador podrá editarlo.
- **Mejora derivada:** los productos `ANUAL`/`MENSUAL` permiten calcular **fecha de renovación** en `sale_items` (`service_start`, `service_end`) → alerta "renovación próxima" (30/15/7 días) y creación sugerida de oportunidad tipo **Actualización**. Esto conecta naturalmente con el indicador Actualización vs Nuevos del Excel. El plan DEMO de 1 semana genera tarea automática de seguimiento al vencer.

### 4.8 Transversales
- `attachments` (entity_type, entity_id, original_name, storage_key UUID, mime, size, uploaded_by) — almacenamiento detrás de interfaz `FileStorage` (disco local → S3 a futuro)
- `audit_logs` (user, action, entity_type, entity_id, before jsonb, after jsonb, ip, user_agent, created_at) — particionable por mes a futuro
- `settings` (key, value jsonb): umbrales de alertas, reglas de scoring, RUC único sí/no
- `saved_views` (user, module, name, filters jsonb, is_default, is_shared)
- `import_jobs` + `import_job_rows` (estado, errores por fila, resultado)

---

## 5. Módulos funcionales y reglas de negocio clave

### 5.0 Estados comerciales — separación en tres niveles
| Nivel | Qué representa | Valores | Quién lo cambia |
|---|---|---|---|
| **Relación** (prospecto) | ¿Nos ha comprado alguna vez? | PROSPECTO → CLIENTE | Automático al registrar la primera venta; nunca retrocede solo |
| **Estado** (prospecto) | ¿Seguimos trabajándolo? | Activo, En pausa, Descartado, No califica, Inactivo | Solo acción **explícita** del usuario, con motivo; reversible ("Reactivar") |
| **Oportunidad** | Una negociación concreta | Abierta (en etapa) / Ganada / Perdida | Kanban o acciones de la oportunidad |

Reglas:
- **Perder una oportunidad solo cierra esa oportunidad** (con motivo de pérdida). El prospecto/cliente conserva su relación, estado, responsable, historial y demás oportunidades abiertas.
- Si un prospecto queda **sin oportunidades abiertas**, el sistema *sugiere* (no ejecuta) una acción: crear nueva oportunidad, programar re-contacto futuro (p.ej. 90 días) o marcarlo En pausa/Descartado.
- Un **cliente** que pierde una oportunidad sigue siendo cliente; puede pasar a "Inactivo" solo manualmente (o por sugerencia si no tiene compras ni servicios vigentes en X meses, configurable).
- Descartado/No califica son reversibles y siempre conservan el historial.
- Los KPI distinguen: oportunidades perdidas (y razones) ≠ prospectos descartados ≠ clientes inactivos.

### 5.1 Sistema de diseño UI/UX (naranja · negro · blanco)

**Identidad y color (tokens CSS en Tailwind / variables shadcn):**
- **Naranja corporativo** = color primario: botones principales, ítem de navegación activo, foco, enlaces, gráficos destacados. HEX oficial **`#E03E0F`** como tono 600, con escala 50–950 generada a partir de él (tonos claros para fondos/hover, oscuros para estado presionado).
- **Logo** `DSCONT_CRM.png` (isotipo "S" naranja/gris oscuro + "DSCONT SOFTWARE"): se copia a `apps/web/src/assets/brand/`; versión completa en login y sidebar expandido, **isotipo recortado** en sidebar colapsado, favicon y PWA icon; variante del logo en blanco sobre el sidebar oscuro (texto "DSCONT" del logo es gris oscuro y no contrasta sobre negro).
- **Negro** = sidebar y textos principales, tomado del gris carbón del logo (≈ `#232323`) con neutros zinc para grises; aporta sobriedad corporativa.
- **Blanco** = fondo de contenido y tarjetas (fondo general gris muy claro `#FAFAFA` para dar capas).
- **Colores de estado separados de la marca** para que el naranja no se confunda con "advertencia": éxito verde, atención **ámbar** (tono distinto al naranja de marca), crítico rojo, info azul, neutro gris. Interés Alto/Regular/Bajo y semáforos usan estos tokens. Todas las combinaciones validadas con contraste WCAG AA.
- Opacidades por niveles definidos (hover 4–8 %, seleccionado 10–12 %, overlays 40–60 % con blur moderado de 4–8 px solo en overlays/topbar).
- Modo claro como principal; tokens preparados para un modo oscuro posterior.

**Tipografía y ritmo:** Inter (o Geist) — escala 12/14/16/20/24/30 con pesos 400/500/600; números tabulares en montos y KPIs. Espaciado en escala de 4 px; radios 8 px (inputs/botones) y 12 px (cards/drawers); sombras sutiles en 3 niveles; bordes 1 px neutros. Iconos **lucide** (consistentes con shadcn).

**Movimiento:** librería **Motion (Framer Motion)** + transiciones Tailwind. Duraciones 120–220 ms, easing `ease-out`; hover/press en botones, apertura de drawers/modales/sheets, tabs con indicador deslizante, aparición escalonada leve de cards/listas, skeleton con shimmer suave, feedback de guardado (toast + check), reordenamiento animado en Kanban. Se respeta `prefers-reduced-motion`.

**Patrones de pantalla:**
- *Desktop:* sidebar negro colapsable + topbar blanca con búsqueda (Ctrl+K), notificaciones y usuario; contenido en cards con mucho aire.
- *Ficha de prospecto:* cabecera con avatar/iniciales, badges de tipo de persona/relación/estado, score y próxima acción destacada; tabs; acciones rápidas siempre visibles.
- *Timeline:* línea vertical con iconos por canal y color por resultado.
- *Formularios:* secciones, campos condicionales natural/jurídica, obligatorios marcados, validación en línea, en drawer lateral para no perder contexto.
- *Estados:* skeletons, estados vacíos ilustrados con acción sugerida, errores comprensibles, sin permisos.

**Móvil real (no solo "se acomoda"):**
- Navegación inferior (Inicio, Prospectos, Tareas, Buscar, Más) + botón flotante naranja "Registrar contacto".
- Tablas → **listas de tarjetas** con 3–4 datos clave y swipe/acciones; filtros en *bottom sheet*.
- Formularios a una columna, inputs nativos de fecha/hora/teléfono, áreas táctiles ≥ 44 px, botones de acción fijos abajo.
- Drawers como *bottom sheets* con gesto de cierre; Kanban como columnas deslizables horizontalmente con cambio de etapa por menú.
- Flujos móviles priorizados: buscar, abrir ficha, llamar/WhatsApp con un toque (`tel:` / `wa.me`), registrar interacción, crear tarea, revisar recordatorios, cambiar estado, registrar venta básica.

**Consistencia:** librería propia `shared/ui` sobre shadcn con variantes únicas (Button, Badge, KpiCard, DataTable/CardList, Drawer/Sheet, EmptyState, Timeline, StatusPill); página interna `/design-system` (solo dev) para revisar todos los componentes y estados. Gráficos Recharts con la misma paleta (naranja para serie principal, neutros para comparativas).

### 5.2 Módulos

1. **Prospectos (único, adaptativo):** formulario cambia según `person_type`. Registro rápido: tipo persona, documento, nombre/razón social, contacto, teléfono, correo, origen, vendedor, interés, próxima acción. Validación de DNI (8 dígitos) y RUC (11 dígitos + dígito verificador módulo 11; prefijo 10 = natural con negocio, 20 = jurídica → sugiere tipo automáticamente). Interfaz `DocumentLookupProvider` (RENIEC/SUNAT a futuro) desacoplada, sin implementación externa inicial.
2. **Duplicados:** endpoint `POST /prospects/duplicate-check` (documento exacto, email, teléfono normalizado, similitud trigram de nombre > 0.6). Documento duplicado = bloqueo (configurable); el resto = advertencia con enlace al registro.
3. **Ficha del prospecto:** cabecera (estado, responsable, score con explicación, próxima acción, semáforo) + tabs Resumen · Seguimiento (timeline) · Oportunidades · Cotizaciones · Ventas · Tareas · Archivos · Historial. Barra de acciones rápidas (llamada, correo, visita, nota, tarea, cotización, venta, convertir).
4. **Interacciones:** registro en drawer en < 10 s; `attempt_number` automático (más `legacy_attempts` si es importado); actualiza `last_contact_at`, `interaction_count`, interés; si el prospecto sigue abierto y no hay próxima acción → advertencia (no bloqueo) y KPI "sin próxima acción". Opción "registrar y crear tarea".
5. **Tareas/recordatorios:** vistas Hoy / Mañana / 7 días / Vencidas; completar desde lista.
6. **Oportunidades + Kanban:** columnas = `pipeline_stages`; drag & drop con permiso; mover a etapa `is_lost` exige motivo y **afecta solo a la oportunidad** (§5.0); a `is_won` sugiere registrar venta. Cada movimiento → historial + auditoría.
7. **Cotizaciones:** selector de productos por categoría con búsqueda por código/nombre; precio sugerido del catálogo editable con descuento; backend calcula subtotales y total; cambio a "Convertida" al generar venta desde la cotización (copia ítems). PDF de cotización con el logo DSCONT en fase posterior.
8. **Ventas y conversión:** registrar venta → si el prospecto es PROSPECTO pasa a **CLIENTE** (`converted_at/by`), oportunidad a WON. Nunca duplica ni borra historial; clientes siguen siendo la misma entidad (pueden tener nuevas oportunidades, p.ej. actualizaciones).
9. **Asignación:** individual y masiva, con motivo; carga de trabajo por vendedor; notificación al nuevo responsable.
10. **Alertas (worker cada 15 min, idempotente con `dedupe_key`):** renovación de licencia/suscripción próxima; fin de plan demo; asignado sin contacto > X h; sin seguimiento > X días; próxima acción vencida; tarea vencida; cotización por vencer / vencida sin respuesta; alto interés sin próxima actividad; alto valor sin actividad; demasiados intentos; oportunidad estancada en etapa. Umbrales en `settings`/`pipeline_stages`. Semáforo Normal/Atención/Crítico. Interfaz `NotificationChannel` (in-app ahora; email/WhatsApp después).
11. **Lead scoring transparente:** reglas configurables con pesos (interés, monto, recencia, nº interacciones, cotización existente, etapa, cercanía de cierre). Se recalcula en eventos + job nocturno; `score_breakdown` muestra "por qué".
12. **Búsqueda global (Ctrl+K):** documento, nombre/razón social, comercial, contacto, correo, teléfono, código; trigram + unaccent, debounce 300 ms.
13. **Listado:** paginación/orden/filtros en servidor, columnas configurables, selección múltiple (asignar, etiquetar, exportar), filtros guardados ("Mis calientes sin contacto 7 días").
14. **Dashboards:**
    - *Ventas:* mis tareas hoy/vencidas, nuevos asignados, seguimientos hoy, sin contacto, alto interés, cotizaciones pendientes, oportunidades próximas a cerrar, mi resumen de ventas, botones rápidos.
    - *Gerencia:* KPIs y gráficas del Prompt Maestro §23/§25 (embudo, conversiones, ticket promedio, tiempo a primera atención y a cierre, ventas/cotizaciones por vendedor/producto/canal/origen, razones de pérdida, aging, forecast bruto/ponderado), **desglose natural vs jurídica**, con filtros globales compartidos.
    - *Bloque FOR-VEN-001:* matriz HOY / ACUMULADO MES × ACTUALIZACIÓN / NUEVOS → nº y monto de cotizaciones y ventas, calculado de la BD.
    - *Productividad por vendedor* (coaching, no solo ranking).
    - Endpoints agregados (`/dashboard/...`) con SQL optimizado; nunca cálculo en navegador.
15. **Reportes y exportación:** interfaz `ReportExporter` con `CrmExcelExporter` (hojas Resumen, Prospectos, Contactos, Seguimientos, Oportunidades, Cotizaciones, Ventas, Tareas) y `LegacyForVen001Exporter` (replica el formato del Excel actual); respetan filtros; `PdfExporter` a futuro. Exportaciones auditadas.
16. **Importación del Excel legacy:** módulo aislado: subir → parsear (adaptador `ForVen001Parser`) → mapear códigos legacy → detectar duplicados → **preview con errores por fila** → confirmar → job → resumen (importados/actualizados/duplicados/omitidos/error). Cada fila agrupada por prospecto genera prospecto + contactos + interacciones históricas + ventas, con `legacy_*`.
17. **Administración:** usuarios, roles/permisos (matriz), catálogos (CRUD con orden/color/legacy), etapas, productos, etiquetas, settings (umbrales, scoring), auditoría con filtros, papelera (restaurar soft-deleted).

### 6. Seguridad y RBAC
6.1 **Auth:** login → access token JWT 15 min (en memoria) + refresh token 7 días en cookie `httpOnly; Secure; SameSite=Strict` con **rotación y detección de reutilización**; logout revoca; rate limit 5/min en login; bloqueo temporal tras intentos fallidos; argon2id.
6.2 **RBAC:** permisos por código; roles iniciales **Administrador**, **Gerente**, **Ventas** (separar Admin de Gerente para que Gerencia no gestione infraestructura si no se desea; ambos pueden asignarse a la misma persona). Alcance de datos: `.own` vs `.all` aplicado en repositorios (filtro obligatorio por `owner_id`), no solo en UI. Componente `<Can permission="…">` en frontend.
6.3 **Baja de usuario:** no hay borrado físico. Al desactivar, asistente obliga a reasignar prospectos, oportunidades abiertas y tareas pendientes a otro(s) usuario(s) (individual o reparto). El historial (interacciones, cotizaciones, ventas) queda ligado al **prospecto** y conserva su autor original; se registra en `prospect_assignments` y auditoría. Se revocan sus refresh tokens.
6.4 Otros: CORS por entorno, cabeceras de seguridad en Nginx, validación de archivos (MIME real + tamaño + nombre aleatorio), errores amigables con código (`PROSPECT_DUPLICATE_DOCUMENT` → "Ya existe un prospecto con este RUC"), logs sin datos sensibles.

---

## 7. Plan de trabajo por fases

Sprints de ~2 semanas. Cada fase termina con la app **ejecutable**, tests verdes y demo.

| Fase | Contenido | Entregable / criterio de salida |
|---|---|---|
| **0. Descubrimiento y diseño** (1 sem) | Mapeo Excel→CRM a partir de la estructura descrita (y del archivo real si se aporta); Excel FOR-VEN-001 sintético; catálogos iniciales; tokens de diseño naranja/negro/blanco; mockups de login, dashboard ventas, listado, ficha, registro rápido, Kanban y versión móvil | Mapeo documentado, design tokens y mockups aprobados |
| **1. Fundaciones** | Monorepo, Docker Compose dev (db, api, web, worker), Alembic, config por entorno, logging, manejo de errores, paginación estándar, CI; auth JWT+refresh, usuarios, RBAC, catálogos, settings y **31 productos** con seeds; **design system** (`shared/ui`, tokens, motion, `/design-system`), layout desktop + navegación móvil, login con marca, cliente API generado | Login funcional, admin gestiona usuarios/roles/catálogos/productos; tests de auth y permisos |
| **2. Prospectos** | Modelo party natural/jurídica, registro rápido + completo, validación DNI/RUC, contactos, duplicados, asignación/reasignación/masiva, etiquetas, listado server-side, búsqueda global, ficha (Resumen/Historial), soft delete, auditoría base | Gerente crea y asigna; vendedor ve solo lo suyo |
| **3. Seguimiento** | Interacciones + timeline, intentos automáticos, próxima acción, tareas/recordatorios (hoy/mañana/7d/vencidas), dashboard de Ventas v1 | Vendedora registra un contacto en segundos y ve su agenda |
| **4. Pipeline** | Oportunidades, etapas configurables, Kanban drag&drop (y versión móvil), motivos de pérdida, historial de etapas, estados del prospecto §5.0 con sugerencias al quedar sin oportunidades | Perder una oportunidad no altera al prospecto/cliente (test dedicado) |
| **5. Cotizaciones y ventas** | Cotizaciones con ítems del catálogo, estados, venta desde cotización o directa, conversión a cliente, fechas de servicio/renovación, adjuntos | Criterio de aceptación §69 hasta "convertir en cliente" |
| **6. Importación + bloque FOR-VEN-001** | Importador legacy con preview, export FOR-VEN-001, bloque HOY/MES × Actualización/Nuevos | **MVP: puede reemplazar el Excel** → piloto en paralelo con Excel |
| **7. Alertas y scoring** | Worker APScheduler, centro de notificaciones, semáforos de estancamiento, scoring explicable | Alertas visibles y configurables |
| **8. Analítica gerencial** | Dashboard gerencial completo, filtros globales, productividad, forecast, export CRM completo, reportes filtrables | Gerente responde las 15 preguntas del §60 |
| **9. UX y productividad** | Filtros guardados, Ctrl+K, "guardar y crear otro/seguimiento", responsive móvil para operaciones clave, estados vacíos/skeletons, accesibilidad | Pruebas con usuarias reales, ajustes |
| **10. Endurecimiento y salida** | E2E Playwright del flujo completo, pruebas de carga básicas, revisión de seguridad, compose prod + Nginx + HTTPS en VPS, backups automáticos + prueba de restauración, monitoreo (healthchecks, logs), README, manual de usuario, capacitación, migración final del Excel, go-live | Sistema en producción, Excel retirado |

Orden respetando dependencias; fases 7–9 pueden reordenarse según prioridad de Gerencia tras el piloto.

---

## 8. Calidad y pruebas
- **Backend:** unit (dominio: validación RUC/DNI, cálculo de totales, scoring, reglas de transición), integración con Postgres real en Docker (repositorios, filtros por alcance), API (permisos por rol para cada endpoint crítico), import con archivos de muestra. Cobertura objetivo ≥ 80 % en `domain/` y `application/`.
- **Frontend:** Vitest para ViewModels (hooks) y esquemas Zod, Testing Library para formularios críticos, MSW para mocks.
- **E2E (Playwright):** flujo §69 completo — login gerente → crear vendedor → crear prospecto natural y jurídico → asignar → login vendedora → contacto + seguimiento → recordatorio → cotización → venta → conversión → dashboard actualizado → filtro por vendedor/fecha → exportar Excel → historial intacto.
- CI: ruff, mypy, eslint, tsc, tests, build de imágenes; verificación de que el cliente TS generado coincide con el OpenAPI.

## 9. Datos
- **Seeds obligatorios (producción):** permisos, roles, catálogos, etapas, settings (umbrales), ubigeo, **6 categorías + 31 productos reales**, usuario admin inicial desde `.env`.
- **Seeds demo inventados** (solo dev, comando separado `make seed-demo`, generador determinista con semilla fija para que siempre produzca lo mismo):
  - Usuarios: 1 administrador, 1 gerente (p.ej. "Ricardo Salazar"), 3 vendedoras ("María Quispe", "Lucía Fernández", "Carla Rojas") — contraseñas demo solo en README de desarrollo.
  - **~60 prospectos ficticios peruanos**: ~35 jurídicos (estudios contables, ferreterías, distribuidoras, clínicas, colegios, transportes en Lima, Arequipa, Trujillo, Piura, Cusco…) con RUC 20xxxxxxxxx de dígito verificador válido pero ficticio, 1–3 contactos cada uno; ~25 naturales (contadores independientes, emprendedores, RUC 10 o solo DNI ficticio).
  - Historial de 6 meses: ~400 interacciones con todos los canales (C/T/V/W/F/R), modalidades, resultados e intereses; oportunidades en todas las etapas (incluye perdidas con motivos variados, sin afectar al prospecto); ~80 cotizaciones con productos reales y ~35 ventas (mezcla Nuevo/Actualización, licencias anuales con renovaciones próximas, planes cloud mensuales, un demo por vencer); tareas de hoy, vencidas y futuras; notificaciones; etiquetas; algunos prospectos "olvidados" y estancados para que alertas y semáforos se vean.
  - Fechas relativas a "hoy" para que el dashboard (HOY / ACUMULADO MES) siempre muestre datos.
- **Excel sintético `FOR-VEN-001_demo.xlsx`** con la estructura descrita (encabezado, totales HOY/ACUMULADO, Actualización/Nuevos, filas de prospecto con códigos legacy, intentos, montos, observaciones) y **errores intencionales** (RUC inválido, duplicados, fechas mal escritas) para probar el importador. Cuando se disponga del Excel real, solo se ajusta el adaptador `ForVen001Parser`.

## 10. Despliegue (VPS)
VPS Linux (2 vCPU / 4 GB suficiente al inicio) · Docker Compose prod: `nginx`, `web` (estáticos), `api` (gunicorn+uvicorn workers), `worker`, `db` (volumen persistente) · HTTPS Let's Encrypt · `alembic upgrade head` en el arranque del deploy · backups `pg_dump` diarios con retención 7 diarios / 4 semanales / 12 mensuales copiados fuera del VPS + backup de `attachments` · prueba de restauración mensual documentada · zona horaria `America/Lima`.

## 11. Riesgos y mitigaciones
- **Rechazo de usuarias acostumbradas a Excel** → registro rápido, piloto temprano (fase 6), capacitación, export FOR-VEN-001 durante la transición.
- **Calidad de datos del Excel** → preview con errores por fila, códigos legacy preservados, importación repetible.
- **Ambigüedad de códigos legacy** → todo en catálogos configurables con `legacy_code`.
- **Alcance grande** → MVP en fase 6; resto incremental.

## 12. Supuestos adoptados (configurables, no bloquean el inicio)
- Ventas ve **solo sus prospectos** (`prospects.read.own`); Gerencia/Admin ven todos. Se cambia desde la matriz de permisos.
- Moneda **PEN**; campo `currency` preparado para USD.
- Precios del catálogo son precios finales; las cotizaciones y ventas solo calculan cantidades, descuentos y totales.
- Marca: naranja `#E03E0F` + logo `DSCONT_CRM.png` (ya disponible en la carpeta del proyecto).
- Excel real opcional: se trabaja con el sintético y se ajusta el parser si luego se aporta.

## 13. Verificación del plan una vez implementado
- `docker compose -f infra/compose.dev.yml up` levanta todo; Swagger en `/api/docs`.
- `pytest` (api) y `pnpm test` / `pnpm e2e` (web) en verde en CI.
- Ejecución manual del flujo de aceptación §69 con usuarios demo.
- Revisión visual en desktop (1440 px), tablet (768 px) y móvil (390 px) de dashboard, listado, ficha, registro de interacción y Kanban; Lighthouse accesibilidad ≥ 90.
- Test específico: marcar una oportunidad como perdida → el prospecto/cliente mantiene relación, estado y demás oportunidades.
- Verificar que el seed carga los 31 productos con códigos y precios exactos y que una cotización (p.ej. 2 × DSCSAA0004 a S/ 350.00 con S/ 50.00 de descuento = S/ 650.00) calcula el total correctamente.
- Importar el Excel sintético (y el real, si se aporta) y comparar los totales del bloque FOR-VEN-001 con los del Excel original (deben coincidir).
- Restaurar un backup en un entorno limpio y verificar integridad.
