# Seguridad y privacidad — AURA Sync API

Este documento responde, para el módulo de sincronización de objetos
personales (embeddings + thumbnails vía OAuth de Google), los puntos que el
diseño original no especificaba: algoritmo de encriptación, almacenamiento
seguro, proceso de consentimiento, política de borrado, riesgos de subir
embeddings de objetos personales, y qué implica una falla del sistema en
términos de seguridad y autonomía del usuario.

## 1. Algoritmo de encriptación

- **AES-256-GCM**, implementado en `app/infrastructure/encryption.py` sobre
  `cryptography.hazmat.primitives.ciphers.aead.AESGCM`.
- Se encriptan a nivel aplicación (antes de tocar la base de datos) los tres
  campos que pueden identificar objetos/espacios personales del usuario:
  `embedding`, `thumbnail` y `name`.
- Formato almacenado: `nonce (12 bytes) || ciphertext || tag (16 bytes,
  incluido por AESGCM)`. Cada fila usa un nonce aleatorio nuevo — nunca se
  reutiliza un nonce con la misma clave.
- **Manejo de claves**: la clave maestra de 32 bytes vive en la variable de
  entorno `AURA_ENCRYPTION_KEY` (base64). En desarrollo puede estar en
  `.env` local (no versionado); en producción **debe** provenir de un
  secret manager (Railway secrets, AWS KMS/Secrets Manager, GCP Secret
  Manager, etc.), nunca de un archivo committeado. Si la variable falta, el
  proceso de encriptación/desencriptación falla explícitamente
  (`EncryptionKeyNotConfigured`) en vez de guardar datos en claro
  silenciosamente.
- **Qué protege**: un dump robado de la base de datos (backup filtrado,
  acceso no autorizado al motor de Postgres, credenciales de DB
  comprometidas sin acceso al proceso del backend).
- **Qué NO protege** (limitación aceptada en esta iteración, no es cifrado
  extremo a extremo): un atacante que compromete el proceso del backend en
  ejecución tiene la clave en memoria y puede leer/desencriptar todo. Para
  cerrar ese vector haría falta cifrado E2E (clave derivada en el
  dispositivo del usuario, el backend nunca ve texto plano), lo cual impide
  cualquier procesamiento server-side futuro sobre los embeddings y requiere
  cambios en el cliente Flutter — quedó fuera de alcance de esta iteración
  y se documenta como trabajo futuro si el requisito de privacidad se
  endurece.

## 2. Almacenamiento seguro

- PostgreSQL, columnas `BYTEA` con el contenido ya encriptado (ver §1) —
  `app/infrastructure/models.py`.
- **Transporte**: Railway termina TLS frente al backend; `DATABASE_URL`
  debe usar `sslmode=require` cuando la base de datos no está co-ubicada
  con la app (documentado en el despliegue, no forzado por código porque
  depende del proveedor).
- **CORS**: whitelist explícita vía `ALLOWED_ORIGINS` (`app/main.py`) — sin
  configurar, no se acepta ningún origen de browser. La app móvil no
  depende de CORS.
- **Superficie de ataque reducida**: se eliminaron los endpoints
  `POST/GET /dev/token` de cualquier entorno que no sea
  `ENVIRONMENT=development` — antes existían sin autenticación en
  cualquier despliegue (incluido producción) y devolvían el último token
  OAuth real visto por el servidor a quien sea que los llamara.
- **OAuth reforzado**: `app/interfaces/dependencies.py` valida el access
  token contra `tokeninfo` de Google y **verifica el `aud`/`azp` contra
  `GOOGLE_CLIENT_ID`**. Antes solo se llamaba a `userinfo`, que no confirma
  para qué aplicación se emitió el token — cualquier access token válido de
  Google (de cualquier app) autenticaba contra este backend.
- **Límites de abuso**: `POST /sync/objects/upload` rechaza batches de más
  de 200 objetos y payloads individuales que excedan ~64KB (embedding) /
  ~256KB (thumbnail) — bien por encima del tamaño esperado (~5KB / ~15KB)
  pero suficiente para frenar abuso obvio del único endpoint de escritura
  masiva.
- **Logging de auditoría sin datos sensibles**: `app/main.py` loguea
  método/path/status/duración y un hash truncado del header
  `Authorization` (para correlacionar requests de una sesión sin loguear el
  token ni el `google_user_id` en claro). Nunca se loguea el cuerpo del
  request, así que embeddings/thumbnails/tokens no pasan por los logs.

## 3. Proceso de consentimiento

- Antes de que un usuario pueda subir objetos personales, debe llamar a
  `POST /sync/consent`, que registra `consent_given_at` (timestamp) y
  `consent_policy_version` (versión de la política vigente,
  `CURRENT_CONSENT_POLICY_VERSION` en
  `app/application/sync_settings_service.py`) en `user_settings`.
- `POST /sync/objects/upload` devuelve **403** si el usuario no tiene
  consentimiento vigente para la versión actual de la política.
- `GET /sync/consent` expone el estado actual; `DELETE /sync/consent`
  revoca el consentimiento (bloquea futuros uploads, pero **no** borra los
  datos ya sincronizados — para eso ver §4).
- Si se publica una nueva versión de la política (se sube
  `CURRENT_CONSENT_POLICY_VERSION`), el consentimiento previo deja de ser
  válido automáticamente (`consent_policy_version` ya no coincide) y el
  usuario debe volver a aceptar antes de poder sincronizar de nuevo.

## 4. Política de borrado

- `DELETE /sync/objects/{id}` — borra un objeto puntual (ya existía).
- `DELETE /sync/account` (nuevo) — purga **todos** los `saved_objects` y el
  registro completo de `user_settings` (incluido el consentimiento) del
  usuario autenticado, en una única transacción. Es un borrado real
  (`DELETE` en SQL), no soft-delete ni marcado lógico.
- No hay retención automática por tiempo en esta iteración: los datos
  quedan hasta que el usuario los borra explícitamente (por objeto o en
  bloque). Si se requiere una política de expiración automática (p. ej.
  purgar objetos no sincronizados en N días), es una mejora futura que
  necesitaría un job programado — se deja documentado como pendiente, no
  implementado, para no inventar un comportamiento que el producto no pidió.

## 5. Riesgos de subir embeddings de objetos personales

Un embedding de MobileNetV2 (1280 floats) más su thumbnail no es un dato
anónimo: identifica objetos específicos y únicos del entorno íntimo de una
persona con discapacidad visual (llaves, medicación, documentos, dinero,
objetos de valor). Combinado con `created_at` y el hecho de que el usuario
es una persona con baja visión o ciega —población con mayor vulnerabilidad
frente a explotación física y económica—, una filtración de estos datos
podría permitir:

- Inferir qué objetos de valor tiene el usuario en su casa.
- Inferir rutinas (qué objetos agrega/consulta y cuándo).
- Re-identificar al usuario entre datasets si el mismo objeto aparece en
  otro contexto.

Esto justifica el nivel de protección elegido (encriptación en reposo +
consentimiento explícito + borrado real bajo control del usuario) y por qué
`name` (la etiqueta que el usuario le puso al objeto, ej. "llaves de casa",
"pastillas de la presión") se trata con el mismo nivel de protección que el
embedding, no como metadata trivial.

## 6. Qué pasa si el sistema falla (seguridad y autonomía del usuario)

El backend **nunca es la única fuente de verdad de seguridad física** — solo
almacena y sirve datos; la decisión de actuar sobre una identificación
(cruzar una calle, tomar un medicamento, confiar en que un objeto es el
correcto) la toma el usuario a partir de lo que le comunica el cliente
móvil/AR. Esta separación de responsabilidades es intencional, pero implica
que el backend debe dar señales suficientes para que el cliente pueda
comunicar incertidumbre en vez de fallar en silencio:

- **Detección perdida** (el modelo on-device no reconoce el objeto): el
  sistema debe fallar "seguro" — no inventar una identificación. El backend
  no participa en la detección (ocurre 100% on-device), pero al exponer
  `created_at` en cada objeto permite que el cliente distinga datos frescos
  de datos desactualizados si en el futuro se agrega confianza/score por
  objeto.
- **Framerate bajo**: puede causar reconocimiento tardío o inconsistente.
  Riesgo de autonomía: el usuario puede tomar una decisión física basada en
  información vieja sin saberlo. Mitigación recomendada para el cliente
  (fuera de este repo): mostrar explícitamente al usuario cuándo la
  confianza de detección es baja, en vez de asumir silenciosamente la
  última lectura válida.
- **Retrieval incorrecto** (falso positivo — confundir dos objetos
  similares, ej. dos frascos de pastillas parecidos): mismo tipo de riesgo,
  pero con consecuencia potencialmente más grave (error de medicación).
  Motiva por qué los embeddings deben poder versionarse/invalidarse: si se
  detecta drift del modelo de reconocimiento, tiene que ser posible forzar
  un re-cálculo de embeddings ya sincronizados en vez de confiar
  ciegamente en datos viejos.
- En todos los casos, la responsabilidad de UX de fallback (avisar al
  usuario de forma clara y no accionable por error) es del cliente móvil;
  este backend se limita a no introducir corrupción de datos silenciosa
  (falla explícita si la desencriptación falla — `ValueError` en
  `encryption.decrypt`, nunca devuelve datos parcialmente corruptos como si
  fueran válidos) y a exponer los timestamps necesarios para que el cliente
  pueda tomar esa decisión de UX.

## Resumen de cambios respecto al diseño original

| Punto sin especificar | Resuelto en |
|---|---|
| Algoritmo de encriptación | `app/infrastructure/encryption.py` (AES-256-GCM) |
| Almacenamiento seguro | `object_repository`/`models.py` + hardening de OAuth/CORS/`/dev/token` en `main.py`/`dependencies.py` |
| Proceso de consentimiento | `sync_settings_service.py`, `routers/sync_settings.py` (`/sync/consent`) |
| Política de borrado | `routers/account.py` (`DELETE /sync/account`) |
| Riesgos de embeddings personales | §5 de este documento |
| Semántica de fallas (detección/framerate/retrieval) | §6 de este documento |
