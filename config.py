"""Configurações da aplicação host local MechHub para desenvolvimento e testes do Módulo 04 (ThermoLab)."""

import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


_DEFAULT_DB_PATH = (
    "/tmp/mechhub.db"
    if os.environ.get("VERCEL")
    else os.path.join(BASE_DIR, "mechhub.db")
)


class Config:
    """Configurações padrão do Flask e SQLAlchemy."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "mechhub-thermolab-dev-key-2026")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{_DEFAULT_DB_PATH}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
