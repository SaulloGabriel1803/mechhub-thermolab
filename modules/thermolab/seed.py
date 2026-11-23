"""Dados iniciais (seed) de materiais típicos de Engenharia Mecânica para o ThermoLab."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from extensions import db
from modules.thermolab.models import ThermalMaterial

DEFAULT_MATERIALS: list[dict] = [
    {
        "name": "Aço Carbono AISI 1020",
        "category": "Metálico",
        "specific_heat": 486.0,
        "thermal_expansion": 11.7e-6,
        "thermal_conductivity": 51.9,
        "density": 7870.0,
        "max_temp": 1420.0,
        "notes": "Aço estrutural de baixo carbono amplamente usado em eixos, chapas e suportes.",
    },
    {
        "name": "Aço Inoxidável AISI 304",
        "category": "Metálico",
        "specific_heat": 500.0,
        "thermal_expansion": 17.2e-6,
        "thermal_conductivity": 16.2,
        "density": 8000.0,
        "max_temp": 1400.0,
        "notes": "Aço austenítico resistente à corrosão, comum em trocadores de calor e tubulações.",
    },
    {
        "name": "Alumínio 6061-T6",
        "category": "Metálico",
        "specific_heat": 896.0,
        "thermal_expansion": 23.1e-6,
        "thermal_conductivity": 167.0,
        "density": 2700.0,
        "max_temp": 582.0,
        "notes": "Liga leve estrutural com alta condutividade térmica para dissipadores e chassis.",
    },
    {
        "name": "Cobre Eletrolítico C11000",
        "category": "Metálico",
        "specific_heat": 385.0,
        "thermal_expansion": 16.5e-6,
        "thermal_conductivity": 388.0,
        "density": 8940.0,
        "max_temp": 1083.0,
        "notes": "Condutor térmico de referência para serpentinas, barramentos e trocadores.",
    },
    {
        "name": "Latão C36000",
        "category": "Metálico",
        "specific_heat": 380.0,
        "thermal_expansion": 20.5e-6,
        "thermal_conductivity": 115.0,
        "density": 8500.0,
        "max_temp": 900.0,
        "notes": "Liga cobre-zinco de fácil usinagem usada em válvulas, conexões e buchas.",
    },
    {
        "name": "Liga de Titânio Ti-6Al-4V",
        "category": "Metálico",
        "specific_heat": 526.0,
        "thermal_expansion": 8.6e-6,
        "thermal_conductivity": 6.7,
        "density": 4430.0,
        "max_temp": 1604.0,
        "notes": "Alta resistência mecânica em temperaturas elevadas e baixa dilatação térmica.",
    },
    {
        "name": "Ferro Fundido Cinzento ASTM A48",
        "category": "Metálico",
        "specific_heat": 490.0,
        "thermal_expansion": 10.8e-6,
        "thermal_conductivity": 50.0,
        "density": 7150.0,
        "max_temp": 1175.0,
        "notes": "Utilizado em blocos de motores, carcaças, bases de máquinas e discos de freio.",
    },
    {
        "name": "Lã de Rocha (Isolante Térmico Industrial)",
        "category": "Isolante",
        "specific_heat": 840.0,
        "thermal_expansion": 6.0e-6,
        "thermal_conductivity": 0.040,
        "density": 100.0,
        "max_temp": 750.0,
        "notes": "Material isolante fibroso de baixíssima condutividade térmica para fornos e dutos.",
    },
]


def seed_materials() -> int:
    """Popula a tabela de materiais térmicos caso ainda esteja vazia.

    Retorna o número de materiais inseridos.
    """
    if ThermalMaterial.query.count() > 0:
        return 0

    inserted = 0
    for item in DEFAULT_MATERIALS:
        material = ThermalMaterial(**item)
        db.session.add(material)
        inserted += 1

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return 0
    return inserted
