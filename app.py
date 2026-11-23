"""Host local do MechHub para execução e demonstração do Módulo 04 (ThermoLab)."""

from __future__ import annotations

import os

from flask import Flask, redirect, url_for

from config import Config
from extensions import db
from modules.thermolab import init_thermolab_db, thermolab_bp


def create_app(config_class: type[Config] | dict | None = None) -> Flask:
    """Fábrica da aplicação Flask (Application Factory Pattern)."""
    app = Flask(__name__)
    app.config.from_object(Config)

    if isinstance(config_class, dict):
        app.config.update(config_class)
    elif config_class is not None:
        app.config.from_object(config_class)

    db.init_app(app)
    app.register_blueprint(thermolab_bp)

    # Inicializa tabelas e popula dados padrão de Engenharia Térmica
    init_thermolab_db(app)

    @app.route("/")
    def index():
        """Redireciona a raiz do host local diretamente para o Módulo 04 (ThermoLab)."""
        return redirect(url_for("thermolab.dashboard"))

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug)
