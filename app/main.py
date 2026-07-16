"""Punto de entrada de la AURA Sync API."""

import hashlib
import logging
import os
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.interfaces.routers import account, sync_objects, sync_settings

logging.basicConfig(level=logging.INFO)
access_logger = logging.getLogger("aura.access")

ENVIRONMENT = os.getenv("ENVIRONMENT", "production")
_is_dev = ENVIRONMENT == "development"

app = FastAPI(
    title="AURA Sync API",
    version="1.0.0",
    description="Backend de sincronización para app móvil AURA",
    docs_url=None,  # Deshabilitamos el Swagger por defecto para personalizar
)

# CORS: whitelist explícita de orígenes vía env var (coma-separado). Sin
# entradas configuradas, no se permite ningún origen de browser (la app
# móvil no envía Origin, así que no depende de CORS).
_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sync_objects.router)
app.include_router(sync_settings.router)
app.include_router(account.router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log de auditoría mínimo: método, path y status. Nunca loguea el
    cuerpo del request (embeddings/thumbnails/tokens nunca pasan por acá).
    El google_user_id no está disponible en este punto (se resuelve recién
    en la dependencia de auth de cada endpoint), así que se identifica al
    llamante por un hash truncado del Authorization header, suficiente para
    correlacionar requests de una misma sesión sin loguear el token en claro.
    """
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000

    auth_header = request.headers.get("authorization", "")
    caller_hash = (
        hashlib.sha256(auth_header.encode("utf-8")).hexdigest()[:12]
        if auth_header
        else "anon"
    )
    access_logger.info(
        "%s %s -> %s (%.1fms) caller=%s",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
        caller_hash,
    )
    return response


@app.get("/health", tags=["Health"])
def health():
    """Health check. Único endpoint que NO requiere autenticación."""
    return {"status": "ok"}


# ── Token de desarrollo en memoria (SOLO ENTORNO DE DESARROLLO) ─────────────
# El teléfono envía el token aquí al hacer login para que Swagger lo lea
# automáticamente. Nunca debe existir fuera de ENVIRONMENT=development: en
# cualquier otro entorno estas rutas ni siquiera se registran, para no
# exponer un endpoint capaz de devolver el último token OAuth visto.
_dev_token: str | None = None

if _is_dev:

    @app.post("/dev/token", include_in_schema=False)
    async def store_dev_token(request: Request):
        """Recibe el token de Google del teléfono y lo guarda en memoria."""
        global _dev_token
        body = await request.json()
        _dev_token = body.get("token")
        return {"ok": True}

    @app.get("/dev/token", include_in_schema=False)
    async def get_dev_token():
        """Swagger llama a este endpoint al cargar para auto-autenticarse."""
        return {"token": _dev_token}


# ── Swagger personalizado que se auto-autentica ──────────────────────────────
_AUTO_AUTH_JS = """
<script>
(function () {
    var _tokenCargado = false;

    function showBanner(msg, color) {
        var old = document.getElementById('aura-banner');
        if (old) old.remove();
        var b = document.createElement('div');
        b.id = 'aura-banner';
        b.innerText = msg;
        b.style.cssText = 'position:fixed;top:0;left:0;right:0;background:' + color +
            ';color:white;text-align:center;padding:10px;font-size:15px;z-index:9999;cursor:pointer';
        b.onclick = function () { b.remove(); };
        document.body.prepend(b);
    }

    async function tryLoadToken() {
        if (!window.ui) return false;
        try {
            var resp = await fetch('/dev/token');
            var data = await resp.json();
            if (data.token) {
                window.ui.preauthorizeApiKey('HTTPBearer', data.token);
                _tokenCargado = true;
                showBanner('✅ Token de Google cargado automáticamente. Ya puedes usar los endpoints.', '#2e7d32');
                console.log('[AURA] Token inyectado en Swagger.');
                return true;
            }
        } catch (e) { console.warn('[AURA]', e); }
        return false;
    }

    // 1) Esperar a que Swagger UI esté listo y luego intentar cargar el token
    var initTimer = setInterval(async function () {
        if (!window.ui) return;
        clearInterval(initTimer);
        var ok = await tryLoadToken();
        if (!ok) {
            showBanner('⚠️ Inicia sesión en la app AURA para cargar el token automáticamente. ' +
                       'O haz clic en "Cargar token" abajo.', '#e65100');
        }
    }, 200);

    // 2) Sondear cada 5 segundos por si el usuario se loguea después de abrir Swagger
    setInterval(async function () {
        if (_tokenCargado) return;
        await tryLoadToken();
    }, 5000);

    // 3) Agregar botón manual de recarga en la barra de Swagger
    window.addEventListener('load', function () {
        setTimeout(function () {
            var topbar = document.querySelector('.swagger-ui .topbar-wrapper');
            if (!topbar) return;
            var btn = document.createElement('button');
            btn.innerText = '🔄 Cargar token';
            btn.title = 'Recarga el token de Google desde la app';
            btn.style.cssText = 'margin-left:12px;padding:6px 14px;background:#1565c0;' +
                'color:white;border:none;border-radius:4px;cursor:pointer;font-size:13px;';
            btn.onclick = async function () {
                _tokenCargado = false;
                var ok = await tryLoadToken();
                if (!ok) showBanner('❌ No hay token disponible. Asegúrate de estar logueado en la app.', '#c62828');
            };
            topbar.appendChild(btn);
        }, 1000);
    });
})();
</script>
"""


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    html = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="AURA Sync API",
    )
    html_str = html.body.decode("utf-8")

    # El auto-auth vía /dev/token solo existe (y solo se inyecta) en desarrollo.
    if _is_dev:
        html_str = html_str.replace("</body>", _AUTO_AUTH_JS + "\n</body>")
    return HTMLResponse(html_str)
