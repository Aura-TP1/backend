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
DATABASE_URL=postgresql://user:password@localhost:5432/aura_db?sslmode=require
GOOGLE_CLIENT_ID=tu_google_client_id
AURA_ENCRYPTION_KEY=clave_aes256_de_32_bytes_en_base64
ALLOWED_ORIGINS=
ENVIRONMENT=development
```

- `GOOGLE_CLIENT_ID`: usado para verificar el `aud` de los access tokens de
  Google (ver [SECURITY.md](./SECURITY.md) §2). Sin esta variable, el
  backend rechaza toda autenticación (fail-closed).
- `AURA_ENCRYPTION_KEY`: clave AES-256 (32 bytes en base64) para encriptar
  embeddings/thumbnails/nombres en reposo. Generarla con
  `python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"`.
  En producción debe vivir en un secret manager, nunca en un `.env`
  versionado.
- `ALLOWED_ORIGINS`: orígenes permitidos por CORS, separados por coma. La
  app móvil no lo necesita; solo aplica a clientes de browser.
- `ENVIRONMENT=development` habilita los endpoints `/dev/token` usados por
  Swagger para auto-autenticarse. En cualquier otro valor (o sin
  configurar) esos endpoints no existen — ver SECURITY.md §2.

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

Todos los endpoints (excepto `/health`) requieren el Google Access Token que
la app obtiene tras el login con Google:

```
Authorization: Bearer <google_access_token>
```

El backend valida el token contra el endpoint `tokeninfo` de Google,
verifica que el `aud`/`azp` coincida con `GOOGLE_CLIENT_ID` (para rechazar
tokens válidos emitidos para otra aplicación) y extrae el `google_user_id`
(`sub`). No existe tabla de usuarios: cada usuario solo ve y modifica sus
propios datos. Token inválido, expirado, o con audience incorrecto →
`401 Unauthorized`. Sin `GOOGLE_CLIENT_ID` configurado en el servidor →
`500` (fail-closed: no se acepta ningún token sin poder verificar su
audience).

En Swagger UI usa el botón **Authorize** y pega el token (o, en
`ENVIRONMENT=development`, se auto-carga vía `/dev/token`).

## Endpoints

| Método | Ruta                     | Descripción                                   |
|--------|--------------------------|-----------------------------------------------|
| POST   | `/sync/objects/upload`   | Sube/actualiza objetos (idempotente por `id`). Requiere consentimiento vigente (403 si no lo tiene) |
| GET    | `/sync/objects/download` | Descarga todos los objetos del usuario        |
| DELETE | `/sync/objects/{id}`     | Elimina un objeto del usuario                 |
| PUT    | `/sync/settings`         | Crea/actualiza la configuración del usuario   |
| GET    | `/sync/settings`         | Obtiene la configuración del usuario          |
| GET    | `/sync/consent`          | Devuelve el estado de consentimiento          |
| POST   | `/sync/consent`          | Otorga consentimiento para sincronizar objetos personales |
| DELETE | `/sync/consent`          | Revoca el consentimiento (bloquea futuros uploads) |
| DELETE | `/sync/account`          | Borra permanentemente todos los datos del usuario (objetos + settings + consentimiento) |
| GET    | `/health`                | Health check (sin autenticación)              |

Ver [SECURITY.md](./SECURITY.md) para el detalle de encriptación,
consentimiento, borrado y manejo de fallas.

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
