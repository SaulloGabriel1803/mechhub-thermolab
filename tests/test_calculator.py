"""Testes unitários do motor de cálculos térmicos (calculator.py)."""

import math
import pytest

from modules.thermolab.calculator import (
    calculate_sensible_heat,
    calculate_thermal_conduction,
    calculate_thermal_expansion,
    calculate_thermal_resistance,
    compare_materials,
    simulate_temperature_variation,
)


def test_sensible_heat_heating_and_power():
    """Verifica cálculo de aquecimento e potência térmica média."""
    res = calculate_sensible_heat(
        mass=10.0,
        specific_heat=500.0,
        temp_initial=20.0,
        temp_final=120.0,
        time_seconds=50.0,
    )
    assert res["delta_t_c"] == pytest.approx(100.0)
    assert res["heat_j"] == pytest.approx(500_000.0)
    assert res["heat_kj"] == pytest.approx(500.0)
    assert res["power_watts"] == pytest.approx(10_000.0)
    assert res["power_kw"] == pytest.approx(10.0)
    assert "Aquecimento" in res["process_type"]
    assert len(res["temps_curve"]) == 25
    assert len(res["q_curve_kj"]) == 25


def test_sensible_heat_cooling_and_validation():
    """Verifica cálculo de resfriamento (Q < 0) e erro para massa <= 0."""
    res = calculate_sensible_heat(mass=2.0, specific_heat=4184.0, temp_initial=80.0, temp_final=30.0)
    assert res["delta_t_c"] == pytest.approx(-50.0)
    assert res["heat_j"] < 0
    assert "Resfriamento" in res["process_type"]

    with pytest.raises(ValueError, match="Massa"):
        calculate_sensible_heat(mass=0.0, specific_heat=500.0, temp_initial=20.0, temp_final=50.0)

    with pytest.raises(ValueError, match="Calor Específico"):
        calculate_sensible_heat(mass=5.0, specific_heat=-100.0, temp_initial=20.0, temp_final=50.0)


def test_thermal_expansion_modes_and_max_temp_alert():
    """Verifica dilatação 1D, 2D (2α), 3D (3α) e alerta de T_máx."""
    lin = calculate_thermal_expansion(
        initial_measure=2.0,
        alpha=12e-6,
        temp_initial=20.0,
        temp_final=120.0,
        mode="linear",
        max_temp=500.0,
    )
    assert lin["delta_measure"] == pytest.approx(2.0 * 12e-6 * 100.0)
    assert lin["delta_sub_measure"] == pytest.approx(2.4)
    assert lin["exceeds_max_temp"] is False

    sup = calculate_thermal_expansion(
        initial_measure=1.5,
        alpha=12e-6,
        temp_initial=20.0,
        temp_final=120.0,
        mode="superficial",
    )
    assert sup["alpha_effective"] == pytest.approx(24e-6)
    assert sup["delta_measure"] == pytest.approx(1.5 * 24e-6 * 100.0)

    vol = calculate_thermal_expansion(
        initial_measure=1.0,
        alpha=10e-6,
        temp_initial=25.0,
        temp_final=625.0,
        mode="volumetrica",
        max_temp=580.0,
    )
    assert vol["alpha_effective"] == pytest.approx(30e-6)
    assert vol["exceeds_max_temp"] is True

    with pytest.raises(ValueError, match="Medida Inicial"):
        calculate_thermal_expansion(initial_measure=-1.0, alpha=1e-5, temp_initial=20, temp_final=50)


def test_thermal_conduction_flat_and_cylindrical():
    """Verifica Lei de Fourier em parede plana e cilindro vazado."""
    flat = calculate_thermal_conduction(
        k=50.0,
        area=2.0,
        thickness=0.1,
        temp_hot=200.0,
        temp_cold=50.0,
        geometry="flat",
    )
    # Q_dot = (50 * 2 * 150) / 0.1 = 150000 W
    assert flat["heat_rate_w"] == pytest.approx(150_000.0)
    assert flat["thermal_resistance_kw"] == pytest.approx(0.001)
    assert len(flat["pos_curve"]) == 30

    cyl = calculate_thermal_conduction(
        k=40.0,
        area=1.0,
        thickness=1.0,
        temp_hot=150.0,
        temp_cold=50.0,
        geometry="cylindrical",
        r_inner=0.05,
        r_outer=0.10,
        length=2.0,
    )
    expected_q = (2.0 * math.pi * 40.0 * 2.0 * 100.0) / math.log(0.10 / 0.05)
    assert cyl["heat_rate_w"] == pytest.approx(expected_q, rel=1e-4)

    with pytest.raises(ValueError, match="raio externo"):
        calculate_thermal_conduction(
            k=40.0,
            area=1.0,
            thickness=1.0,
            temp_hot=100.0,
            temp_cold=30.0,
            geometry="cylindrical",
            r_inner=0.10,
            r_outer=0.05,
            length=1.0,
        )


def test_thermal_resistance_multilayer_series():
    """Verifica associação em série de camadas condutivas e convecção."""
    layers = [
        {"name": "Aço", "thickness": 0.02, "k": 50.0},
        {"name": "Isolante", "thickness": 0.10, "k": 0.05},
    ]
    res = calculate_thermal_resistance(
        layers=layers,
        area=2.0,
        temp_inner=400.0,
        temp_outer=25.0,
        h_inner=100.0,
        h_outer=25.0,
    )
    # R_conv_i = 1/(100*2)=0.005; R_aco = 0.02/(50*2)=0.0002; R_iso = 0.1/(0.05*2)=1.0; R_conv_e = 1/(25*2)=0.02
    expected_r_total = 0.005 + 0.0002 + 1.0 + 0.02
    assert res["r_total_kw"] == pytest.approx(expected_r_total, rel=1e-5)
    assert res["heat_rate_w"] == pytest.approx((400.0 - 25.0) / expected_r_total, rel=1e-4)
    assert res["interface_temps_c"][0] == pytest.approx(400.0)
    assert res["interface_temps_c"][-1] == pytest.approx(25.0)
    assert sum(item["share_percent"] for item in res["resistances"]) == pytest.approx(100.0, abs=0.1)


def test_compare_materials_and_simulation():
    """Verifica comparação de materiais com Pandas e simulação transiente (Biot/Newton)."""
    mats = [
        {
            "id": 1,
            "name": "Cobre",
            "category": "Metálico",
            "specific_heat": 385.0,
            "thermal_expansion": 16.5e-6,
            "thermal_conductivity": 388.0,
            "density": 8940.0,
            "max_temp": 1083.0,
        },
        {
            "id": 2,
            "name": "Lã de Rocha",
            "category": "Isolante",
            "specific_heat": 840.0,
            "thermal_expansion": 6.0e-6,
            "thermal_conductivity": 0.04,
            "density": 100.0,
            "max_temp": 750.0,
        },
    ]
    cmp_res = compare_materials(mats, mass=5.0, length=1.0, area=1.0, thickness=0.05, delta_t=100.0)
    assert cmp_res["highlights"]["best_conductor"]["name"] == "Cobre"
    assert cmp_res["highlights"]["best_insulator"]["name"] == "Lã de Rocha"
    assert cmp_res["highlights"]["highest_stability"]["name"] == "Lã de Rocha"
    assert len(cmp_res["rows"]) == 2

    sim_res = simulate_temperature_variation(
        material_dict=mats[0],
        temp_start=300.0,
        temp_end=25.0,
        steps=20,
        mass=2.0,
        length=1.0,
        area=0.5,
        thickness=0.02,
        h_conv=20.0,
        sim_time_max=400.0,
    )
    ind = sim_res["physical_indicators"]
    assert ind["lumped_valid"] is True
    assert ind["biot_number"] < 0.1
    assert ind["time_constant_s"] > 0
    assert len(sim_res["parametric_series"]["temps_c"]) == 20
    assert len(sim_res["transient_series"]["times_s"]) == 20
    # Temperatura inicial transiente deve igualar temp_start e decair em direção a temp_end
    assert sim_res["transient_series"]["temps_c"][0] == pytest.approx(300.0)
    assert sim_res["transient_series"]["temps_c"][-1] < 300.0
