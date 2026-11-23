"""Modelos SQLAlchemy do Módulo 04 (ThermoLab - Análise Térmica)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from extensions import db


def _utc_now() -> datetime:
    """Retorna o timestamp UTC atual sem fuso horário para compatibilidade com SQLite."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ThermalMaterial(db.Model):
    """Representa um material de engenharia com suas propriedades térmicas e físicas."""

    __tablename__ = "thermolab_materials"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    category = db.Column(db.String(60), nullable=False, default="Metálico")
    specific_heat = db.Column(db.Float, nullable=False)        # c [J/(kg*K)]
    thermal_expansion = db.Column(db.Float, nullable=False)    # alpha [1/K]
    thermal_conductivity = db.Column(db.Float, nullable=False) # k [W/(m*K)]
    density = db.Column(db.Float, nullable=False)              # rho [kg/m^3]
    max_temp = db.Column(db.Float, nullable=True)              # T_max [°C]
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utc_now)

    @property
    def thermal_diffusivity(self) -> float:
        """Calcula a difusividade térmica alpha_dif = k / (rho * c) em m^2/s."""
        denom = self.density * self.specific_heat
        if denom <= 0:
            return 0.0
        return self.thermal_conductivity / denom

    @property
    def volumetric_heat_capacity(self) -> float:
        """Calcula a capacidade térmica volumétrica (rho * c) em J/(m^3*K)."""
        return self.density * self.specific_heat

    def to_dict(self) -> dict[str, Any]:
        """Serializa o material para dicionário Python/JSON."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "specific_heat": self.specific_heat,
            "thermal_expansion": self.thermal_expansion,
            "thermal_conductivity": self.thermal_conductivity,
            "density": self.density,
            "max_temp": self.max_temp,
            "notes": self.notes or "",
            "thermal_diffusivity": self.thermal_diffusivity,
            "volumetric_heat_capacity": self.volumetric_heat_capacity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<ThermalMaterial {self.id}: {self.name}>"


class ThermalCalculation(db.Model):
    """Armazena o histórico persistido de cálculos, comparações e simulações térmicas."""

    __tablename__ = "thermolab_calculations"

    id = db.Column(db.Integer, primary_key=True)
    calc_type = db.Column(db.String(50), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    material_id = db.Column(
        db.Integer,
        db.ForeignKey("thermolab_materials.id", ondelete="SET NULL"),
        nullable=True,
    )
    input_data = db.Column(db.Text, nullable=False, default="{}")
    result_data = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.DateTime, nullable=False, default=_utc_now, index=True)

    material = db.relationship(
        "ThermalMaterial",
        backref=db.backref("calculations", lazy="dynamic", passive_deletes=True),
    )

    def get_input_dict(self) -> dict[str, Any]:
        """Desserializa o JSON de parâmetros de entrada."""
        try:
            return json.loads(self.input_data or "{}")
        except json.JSONDecodeError:
            return {}

    def get_result_dict(self) -> dict[str, Any]:
        """Desserializa o JSON de resultados calculados."""
        try:
            return json.loads(self.result_data or "{}")
        except json.JSONDecodeError:
            return {}

    def to_dict(self) -> dict[str, Any]:
        """Serializa o registro de cálculo completo."""
        return {
            "id": self.id,
            "calc_type": self.calc_type,
            "title": self.title,
            "material_id": self.material_id,
            "material_name": self.material.name if self.material else "Manual / Múltiplos",
            "input_data": self.get_input_dict(),
            "result_data": self.get_result_dict(),
            "created_at": self.created_at.strftime("%d/%m/%Y %H:%M:%S")
            if self.created_at
            else "",
        }

    def __repr__(self) -> str:
        return f"<ThermalCalculation {self.id} [{self.calc_type}]: {self.title}>"
