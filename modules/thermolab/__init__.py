"""Pacote do Módulo 04 (ThermoLab - Análise Térmica) da plataforma MechHub.

Exporta o Blueprint Flask `thermolab_bp` e a função auxiliar `init_thermolab_db`
para registro limpo na aplicação central do MechHub.
"""

from __future__ import annotations

from extensions import db
from modules.thermolab.routes import thermolab_bp
from modules.thermolab.seed import seed_materials


def init_thermolab_db(app) -> None:
    """Cria as tabelas do ThermoLab no banco ativo e executa o seed inicial."""
    with app.app_context():
        db.create_all()
        seed_materials()


__all__ = ["thermolab_bp", "init_thermolab_db"]
