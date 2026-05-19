"""Punto de entrada de la AURA Sync API.

Crea la app FastAPI, configura Swagger e incluye los routers.
La documentación interactiva queda disponible en /docs (Swagger UI).
"""

from fastapi import FastAPI

from app.interfaces.routers import sync_objects, sync_settings

app = FastAPI(
    title="AURA Sync API",
    version="1.0.0",
    description="Backend de sincronización para app móvil AURA",
)

# Routers de sincronización (requieren token Google válido).
app.include_router(sync_objects.router)
app.include_router(sync_settings.router)


@app.get("/health", tags=["Health"])
def health():
    """Health check. Único endpoint que NO requiere autenticación."""
    return {"status": "ok"}
