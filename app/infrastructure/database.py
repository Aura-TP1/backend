"""Conexión a PostgreSQL y configuración de SQLAlchemy.

Expone:
- engine: motor de conexión a la base de datos.
- SessionLocal: fábrica de sesiones.
- Base: clase base declarativa para los modelos ORM.
- get_db(): dependencia de FastAPI que abre y cierra una sesión por request.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/aura_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
