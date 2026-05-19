# AURA Sync API

Backend de **sincronización opcional** para la app móvil AURA (Flutter), que
ayuda a adultos mayores con discapacidad visual a guardar y encontrar objetos
personales mediante embeddings de MobileNetV2.

> La app funciona **100% offline**. Este backend solo sincroniza datos entre
> dispositivos del mismo usuario.

## Stack

- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy
- Alembic (migraciones)
- Autenticación con Google OAuth (Google ID Token)
- Python 3.11+

## Arquitectura (DDD)

```
app/
├── domain/          # Entidades de negocio puras
├── application/     # Casos de uso / servicios
├── infrastructure/  # DB, modelos ORM, repositorios
└── interfaces/      # Routers FastAPI, schemas Pydantic, auth
```

## Requisitos previos

- Python 3.11 o superior
- PostgreSQL en ejecución con una base de datos creada (ej: `aura_db`)
- Un **Google Client ID** (el mismo que usa la app Flutter)

## Puesta en marcha

### 1. Crear y activar entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

(En Linux/macOS: `python3 -m venv .venv && source .venv/bin/activate`)

### 2. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

Copia `.env.example` a `.env` y ajusta los valores:

```
DATABASE_URL=postgresql://user:password@localhost:5432/aura_db
GOOGLE_CLIENT_ID=tu_google_client_id
```

### 4. Ejecutar migraciones

```powershell
alembic upgrade head
```

Esto crea las tablas `saved_objects` y `user_settings`.

### 5. Levantar el servidor

```powershell
uvicorn app.main:app --reload
```

- API: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Autenticación

Todos los endpoints (excepto `/health`) requieren el Google ID Token que la
app obtiene tras el login con Google:

```
Authorization: Bearer <google_id_token>
```

El backend valida el token contra Google y extrae el `google_user_id` (`sub`).
No existe tabla de usuarios: cada usuario solo ve y modifica sus propios datos.
Token inválido o expirado → `401 Unauthorized`.

En Swagger UI usa el botón **Authorize** y pega el token.

## Endpoints

| Método | Ruta                     | Descripción                                   |
|--------|--------------------------|-----------------------------------------------|
| POST   | `/sync/objects/upload`   | Sube/actualiza objetos (idempotente por `id`) |
| GET    | `/sync/objects/download` | Descarga todos los objetos del usuario        |
| DELETE | `/sync/objects/{id}`     | Elimina un objeto del usuario                 |
| PUT    | `/sync/settings`         | Crea/actualiza la configuración del usuario   |
| GET    | `/sync/settings`         | Obtiene la configuración del usuario          |
| GET    | `/health`                | Health check (sin autenticación)              |

### Notas

- Los campos binarios `embedding` y `thumbnail` viajan como **base64** dentro
  del JSON y se almacenan como `BYTEA` en PostgreSQL.
- El `upload` recibe una lista de objetos y es idempotente: si el `id` ya
  existe para el usuario, lo actualiza; si no, lo crea.
- `GET /sync/settings` devuelve valores por defecto
  (`tts_speed=0.85`, `tts_volume=0.8`) si el usuario aún no guardó nada.

## Migraciones (Alembic)

```powershell
# Aplicar todas las migraciones
alembic upgrade head

# Revertir la última
alembic downgrade -1

# Generar una nueva migración tras cambiar los modelos
alembic revision --autogenerate -m "descripcion del cambio"
```
