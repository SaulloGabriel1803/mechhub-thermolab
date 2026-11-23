"""Motor de cálculos e simulações de Engenharia Térmica (Módulo 04 - ThermoLab).

Implementa os algoritmos físicos em Python utilizando NumPy para computação vetorial
e Pandas para estruturação tabular e análises comparativas.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd


def _validate_positive(value: float, field_label: str) -> float:
    """Valida que um parâmetro físico é numérico, finito e estritamente positivo."""
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"O campo '{field_label}' deve ser um número válido.") from exc
    if not math.isfinite(num) or num <= 0.0:
        raise ValueError(f"O campo '{field_label}' deve ser maior que zero.")
    return num


def _validate_finite(value: float, field_label: str) -> float:
    """Valida que um parâmetro físico é numérico e finito (pode ser negativo ou zero)."""
    try:
        num = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"O campo '{field_label}' deve ser um número válido.") from exc
    if not math.isfinite(num):
        raise ValueError(f"O campo '{field_label}' deve ser um número finito.")
    return num


def calculate_sensible_heat(
    mass: float,
    specific_heat: float,
    temp_initial: float,
    temp_final: float,
    time_seconds: float | None = None,
) -> dict[str, Any]:
    """Calcula o calor sensível Q = m * c * ΔT e parâmetros energéticos associados.

    Args:
        mass: Massa do corpo [kg] (> 0).
        specific_heat: Calor específico c [J/(kg·K)] (> 0).
        temp_initial: Temperatura inicial T_i [°C].
        temp_final: Temperatura final T_f [°C].
        time_seconds: Intervalo de tempo opcional [s] (> 0) para potência térmica média.

    Returns:
        Dicionário com Q em J, kJ, kcal, kWh, ΔT, classificação do processo,
        potência térmica (se informada) e curva vetorial para plotagem.
    """
    m = _validate_positive(mass, "Massa (kg)")
    c = _validate_positive(specific_heat, "Calor Específico (J/kg·K)")
    t_i = _validate_finite(temp_initial, "Temperatura Inicial (°C)")
    t_f = _validate_finite(temp_final, "Temperatura Final (°C)")

    t_sec: float | None = None
    if time_seconds is not None and str(time_seconds).strip() != "":
        t_sec = _validate_positive(time_seconds, "Tempo de Processo (s)")

    delta_t = t_f - t_i
    q_joules = m * c * delta_t
    q_kj = q_joules / 1000.0
    q_kcal = q_joules / 4184.0
    q_kwh = q_joules / 3_600_000.0

    if delta_t > 0:
        process_type = "Aquecimento (Absorção de Calor)"
    elif delta_t < 0:
        process_type = "Resfriamento (Rejeição de Calor)"
    else:
        process_type = "Equilíbrio Térmico (ΔT = 0)"

    power_watts = abs(q_joules) / t_sec if t_sec else None
    power_kw = power_watts / 1000.0 if power_watts is not None else None

    temps_curve = np.linspace(t_i, t_f, 25)
    q_curve_kj = (m * c * (temps_curve - t_i)) / 1000.0

    return {
        "mass_kg": round(m, 6),
        "specific_heat_j_kgk": round(c, 4),
        "temp_initial_c": round(t_i, 4),
        "temp_final_c": round(t_f, 4),
        "delta_t_c": round(delta_t, 4),
        "heat_j": round(q_joules, 4),
        "heat_kj": round(q_kj, 6),
        "heat_kcal": round(q_kcal, 6),
        "heat_kwh": round(q_kwh, 8),
        "process_type": process_type,
        "time_seconds": round(t_sec, 4) if t_sec is not None else None,
        "power_watts": round(power_watts, 4) if power_watts is not None else None,
        "power_kw": round(power_kw, 6) if power_kw is not None else None,
        "temps_curve": [round(float(val), 4) for val in temps_curve],
        "q_curve_kj": [round(float(val), 6) for val in q_curve_kj],
    }


def calculate_thermal_expansion(
    initial_measure: float,
    alpha: float,
    temp_initial: float,
    temp_final: float,
    mode: str = "linear",
    max_temp: float | None = None,
) -> dict[str, Any]:
    """Calcula dilatação térmica linear (1D), superficial (2D) ou volumétrica (3D).

    Args:
        initial_measure: Medida inicial X_0 [m, m² ou m³] (> 0).
        alpha: Coeficiente de dilatação térmica linear α [K^-1] (> 0).
        temp_initial: Temperatura inicial T_i [°C].
        temp_final: Temperatura final T_f [°C].
        mode: Tipo de dilatação ('linear', 'superficial', 'volumetrica').
        max_temp: Temperatura limite operacional do material [°C] (opcional).

    Returns:
        Dicionário com variação dimensional ΔX, medida final X_f, deformação relativa ε_T,
        alerta de temperatura máxima e vetores para gráfico.
    """
    x0 = _validate_positive(initial_measure, "Medida Inicial")
    alpha_lin = _validate_positive(alpha, "Coeficiente de Dilatação Linear (α)")
    t_i = _validate_finite(temp_initial, "Temperatura Inicial (°C)")
    t_f = _validate_finite(temp_final, "Temperatura Final (°C)")

    mode_key = (mode or "linear").strip().lower()
    mode_config = {
        "linear": {
            "multiplier": 1.0,
            "label": "Dilatação Linear (1D)",
            "unit": "m",
            "delta_sub_unit": "mm",
            "sub_factor": 1000.0,
        },
        "superficial": {
            "multiplier": 2.0,
            "label": "Dilatação Superficial (2D)",
            "unit": "m²",
            "delta_sub_unit": "cm²",
            "sub_factor": 10_000.0,
        },
        "volumetrica": {
            "multiplier": 3.0,
            "label": "Dilatação Volumétrica (3D)",
            "unit": "m³",
            "delta_sub_unit": "cm³",
            "sub_factor": 1_000_000.0,
        },
    }
    if mode_key not in mode_config:
        raise ValueError(
            "Modo de dilatação inválido. Escolha 'linear', 'superficial' ou 'volumetrica'."
        )

    cfg = mode_config[mode_key]
    alpha_eff = cfg["multiplier"] * alpha_lin
    delta_t = t_f - t_i
    delta_x = x0 * alpha_eff * delta_t
    final_x = x0 + delta_x
    strain = delta_x / x0
    strain_percent = strain * 100.0
    mm_per_m = strain * 1000.0

    t_max_val: float | None = None
    exceeds_max = False
    if max_temp is not None and str(max_temp).strip() != "":
        t_max_val = _validate_finite(max_temp, "Temperatura Máxima Operacional (°C)")
        exceeds_max = bool(t_f > t_max_val or t_i > t_max_val)

    temps_curve = np.linspace(t_i, t_f, 25)
    delta_curve = x0 * alpha_eff * (temps_curve - t_i)
    measure_curve = x0 + delta_curve

    return {
        "mode": mode_key,
        "mode_label": cfg["label"],
        "unit": cfg["unit"],
        "delta_sub_unit": cfg["delta_sub_unit"],
        "initial_measure": round(x0, 6),
        "alpha_linear": alpha_lin,
        "alpha_effective": alpha_eff,
        "temp_initial_c": round(t_i, 4),
        "temp_final_c": round(t_f, 4),
        "delta_t_c": round(delta_t, 4),
        "delta_measure": round(delta_x, 9),
        "delta_sub_measure": round(delta_x * cfg["sub_factor"], 6),
        "final_measure": round(final_x, 9),
        "strain": round(strain, 9),
        "strain_percent": round(strain_percent, 6),
        "mm_per_m": round(mm_per_m, 6),
        "max_temp_c": t_max_val,
        "exceeds_max_temp": exceeds_max,
        "temps_curve": [round(float(v), 4) for v in temps_curve],
        "measure_curve": [round(float(v), 8) for v in measure_curve],
        "delta_sub_curve": [
            round(float(v * cfg["sub_factor"]), 6) for v in delta_curve
        ],
    }


def calculate_thermal_conduction(
    k: float,
    area: float,
    thickness: float,
    temp_hot: float,
    temp_cold: float,
    geometry: str = "flat",
    r_inner: float | None = None,
    r_outer: float | None = None,
    length: float | None = None,
) -> dict[str, Any]:
    """Calcula condução térmica em regime permanente (Lei de Fourier).

    Suporta parede plana (flat) e parede cilíndrica / tubulação (cylindrical).
    """
    k_val = _validate_positive(k, "Condutividade Térmica k (W/m·K)")
    t1 = _validate_finite(temp_hot, "Temperatura Face Quente T1 (°C)")
    t2 = _validate_finite(temp_cold, "Temperatura Face Fria T2 (°C)")
    geom = (geometry or "flat").strip().lower()

    if geom == "flat":
        a_val = _validate_positive(area, "Área de Troca Térmica (m²)")
        l_val = _validate_positive(thickness, "Espessura da Parede (m)")

        r_cond = l_val / (k_val * a_val)
        q_rate = (t1 - t2) / r_cond
        heat_flux = q_rate / a_val
        temp_gradient = (t2 - t1) / l_val

        pos_curve = np.linspace(0.0, l_val, 30)
        temp_curve = t1 + temp_gradient * pos_curve

        return {
            "geometry": "flat",
            "geometry_label": "Parede Plana (Condução Unidimensional)",
            "k_w_mk": round(k_val, 6),
            "area_m2": round(a_val, 6),
            "thickness_m": round(l_val, 6),
            "temp_hot_c": round(t1, 4),
            "temp_cold_c": round(t2, 4),
            "delta_t_c": round(t1 - t2, 4),
            "heat_rate_w": round(q_rate, 4),
            "heat_rate_kw": round(q_rate / 1000.0, 6),
            "heat_flux_w_m2": round(heat_flux, 4),
            "temp_gradient_c_m": round(temp_gradient, 4),
            "thermal_resistance_kw": round(r_cond, 6),
            "position_label": "Posição x (m)",
            "pos_curve": [round(float(v), 6) for v in pos_curve],
            "temp_curve": [round(float(v), 4) for v in temp_curve],
        }

    if geom == "cylindrical":
        r1 = _validate_positive(r_inner, "Raio Interno r1 (m)")
        r2 = _validate_positive(r_outer, "Raio Externo r2 (m)")
        tube_len = _validate_positive(length, "Comprimento da Tubulação L (m)")
        if r2 <= r1:
            raise ValueError(
                "O raio externo (r2) deve ser estritamente maior que o raio interno (r1)."
            )

        ln_ratio = math.log(r2 / r1)
        r_cond = ln_ratio / (2.0 * math.pi * k_val * tube_len)
        q_rate = (t1 - t2) / r_cond
        area_inner = 2.0 * math.pi * r1 * tube_len
        area_outer = 2.0 * math.pi * r2 * tube_len
        heat_flux_inner = q_rate / area_inner
        heat_flux_outer = q_rate / area_outer
        temp_gradient_avg = (t2 - t1) / (r2 - r1)

        r_curve = np.linspace(r1, r2, 30)
        temp_curve = t1 - (t1 - t2) * (np.log(r_curve / r1) / ln_ratio)

        return {
            "geometry": "cylindrical",
            "geometry_label": "Parede Cilíndrica / Tubulação Radial",
            "k_w_mk": round(k_val, 6),
            "r_inner_m": round(r1, 6),
            "r_outer_m": round(r2, 6),
            "length_m": round(tube_len, 6),
            "thickness_m": round(r2 - r1, 6),
            "area_m2": round(area_inner, 6),
            "temp_hot_c": round(t1, 4),
            "temp_cold_c": round(t2, 4),
            "delta_t_c": round(t1 - t2, 4),
            "heat_rate_w": round(q_rate, 4),
            "heat_rate_kw": round(q_rate / 1000.0, 6),
            "heat_flux_w_m2": round(heat_flux_inner, 4),
            "heat_flux_outer_w_m2": round(heat_flux_outer, 4),
            "temp_gradient_c_m": round(temp_gradient_avg, 4),
            "thermal_resistance_kw": round(r_cond, 6),
            "position_label": "Raio r (m)",
            "pos_curve": [round(float(v), 6) for v in r_curve],
            "temp_curve": [round(float(v), 4) for v in temp_curve],
        }

    raise ValueError("Geometria inválida. Utilize 'flat' ou 'cylindrical'.")


def calculate_thermal_resistance(
    layers: list[dict[str, Any]],
    area: float,
    temp_inner: float,
    temp_outer: float,
    h_inner: float | None = None,
    h_outer: float | None = None,
) -> dict[str, Any]:
    """Calcula a resistência térmica equivalente em série de paredes compostas.

    Inclui opcionalmente convecção interna e externa e determina as temperaturas exatas
    em todas as interfaces entre camadas.
    """
    a_val = _validate_positive(area, "Área Transversal (m²)")
    t_in = _validate_finite(temp_inner, "Temperatura Interna (°C)")
    t_out = _validate_finite(temp_outer, "Temperatura Externa (°C)")

    if not layers or len(layers) == 0:
        raise ValueError("Informe ao menos uma camada condutiva para a análise.")

    resistances: list[dict[str, Any]] = []

    if h_inner is not None and str(h_inner).strip() != "":
        h_in_val = _validate_positive(h_inner, "Coeficiente de Convecção Interno h_i")
        r_in = 1.0 / (h_in_val * a_val)
        resistances.append(
            {
                "name": "Convecção Interna",
                "type": "convecção",
                "thickness_m": 0.0,
                "k_or_h": h_in_val,
                "resistance_kw": r_in,
            }
        )

    for idx, layer in enumerate(layers, start=1):
        layer_name = str(layer.get("name") or f"Camada {idx}").strip()
        l_val = _validate_positive(
            layer.get("thickness"), f"Espessura da camada '{layer_name}' (m)"
        )
        k_val = _validate_positive(
            layer.get("k"), f"Condutividade k da camada '{layer_name}' (W/m·K)"
        )
        r_cond = l_val / (k_val * a_val)
        resistances.append(
            {
                "name": layer_name,
                "type": "condução",
                "thickness_m": l_val,
                "k_or_h": k_val,
                "resistance_kw": r_cond,
            }
        )

    if h_outer is not None and str(h_outer).strip() != "":
        h_out_val = _validate_positive(h_outer, "Coeficiente de Convecção Externo h_e")
        r_out = 1.0 / (h_out_val * a_val)
        resistances.append(
            {
                "name": "Convecção Externa",
                "type": "convecção",
                "thickness_m": 0.0,
                "k_or_h": h_out_val,
                "resistance_kw": r_out,
            }
        )

    r_array = np.array([item["resistance_kw"] for item in resistances], dtype=float)
    r_total = float(np.sum(r_array))
    u_overall = 1.0 / (r_total * a_val)
    q_rate = (t_in - t_out) / r_total
    heat_flux = q_rate / a_val

    # Calcula quedas de temperatura acumuladas com NumPy
    temp_drops = q_rate * r_array
    interface_temps = np.concatenate(
        ([t_in], t_in - np.cumsum(temp_drops))
    )

    cumulative_x = 0.0
    profile_x: list[float] = []
    profile_t: list[float] = []
    layer_boundaries: list[dict[str, Any]] = []

    for i, item in enumerate(resistances):
        t_start = float(interface_temps[i])
        t_end = float(interface_temps[i + 1])
        share_pct = (item["resistance_kw"] / r_total) * 100.0
        item["temp_start_c"] = round(t_start, 4)
        item["temp_end_c"] = round(t_end, 4)
        item["delta_t_c"] = round(t_start - t_end, 4)
        item["share_percent"] = round(share_pct, 2)
        item["resistance_kw"] = round(item["resistance_kw"], 6)

        if item["type"] == "condução":
            if not profile_x:
                profile_x.append(0.0)
                profile_t.append(round(t_start, 4))
            x_start = cumulative_x
            cumulative_x += item["thickness_m"]
            profile_x.append(round(cumulative_x, 6))
            profile_t.append(round(t_end, 4))
            layer_boundaries.append(
                {
                    "name": item["name"],
                    "x_start": round(x_start, 6),
                    "x_end": round(cumulative_x, 6),
                    "t_start": round(t_start, 4),
                    "t_end": round(t_end, 4),
                }
            )

    return {
        "area_m2": round(a_val, 6),
        "temp_inner_c": round(t_in, 4),
        "temp_outer_c": round(t_out, 4),
        "total_thickness_m": round(cumulative_x, 6),
        "r_total_kw": round(r_total, 6),
        "u_overall_w_m2k": round(u_overall, 4),
        "heat_rate_w": round(q_rate, 4),
        "heat_flux_w_m2": round(heat_flux, 4),
        "resistances": resistances,
        "interface_temps_c": [round(float(t), 4) for t in interface_temps],
        "profile_x_m": profile_x,
        "profile_t_c": profile_t,
        "layer_boundaries": layer_boundaries,
    }


def compare_materials(
    materials_list: list[dict[str, Any]],
    mass: float = 1.0,
    length: float = 1.0,
    area: float = 1.0,
    thickness: float = 0.05,
    delta_t: float = 100.0,
) -> dict[str, Any]:
    """Compara múltiplos materiais sob mesmas condições térmicas e geométricas via Pandas."""
    if not materials_list:
        raise ValueError("Selecione ao menos um material para comparação.")

    m = _validate_positive(mass, "Massa de Referência (kg)")
    l_comp = _validate_positive(length, "Comprimento de Referência (m)")
    a_val = _validate_positive(area, "Área de Referência (m²)")
    esp = _validate_positive(thickness, "Espessura de Referência (m)")
    dt = _validate_finite(delta_t, "Variação de Temperatura ΔT (°C)")

    records = []
    for mat in materials_list:
        name = str(mat.get("name", "Material"))
        c = _validate_positive(mat.get("specific_heat"), f"Calor específico de {name}")
        alpha = _validate_positive(mat.get("thermal_expansion"), f"Dilatação α de {name}")
        k = _validate_positive(mat.get("thermal_conductivity"), f"Condutividade k de {name}")
        rho = _validate_positive(mat.get("density"), f"Densidade ρ de {name}")

        q_kj = (m * c * dt) / 1000.0
        delta_l_mm = (l_comp * alpha * dt) * 1000.0
        q_dot_w = (k * a_val * dt) / esp
        r_cond = esp / (k * a_val)
        diffusivity_mm2s = (k / (rho * c)) * 1e6
        vol_cap = rho * c

        records.append(
            {
                "id": mat.get("id"),
                "name": name,
                "category": mat.get("category", "Geral"),
                "specific_heat": round(c, 2),
                "thermal_expansion_1e6": round(alpha * 1e6, 3),
                "thermal_conductivity": round(k, 4),
                "density": round(rho, 2),
                "max_temp": mat.get("max_temp"),
                "sensible_heat_kj": round(q_kj, 4),
                "linear_expansion_mm": round(delta_l_mm, 5),
                "conduction_rate_w": round(q_dot_w, 3),
                "thermal_resistance_kw": round(r_cond, 6),
                "thermal_diffusivity_mm2s": round(diffusivity_mm2s, 4),
                "volumetric_capacity_kj_m3k": round(vol_cap / 1000.0, 2),
            }
        )

    df = pd.DataFrame(records)

    best_conductor_row = df.loc[df["thermal_conductivity"].idxmax()]
    best_insulator_row = df.loc[df["thermal_conductivity"].idxmin()]
    highest_stability_row = df.loc[df["thermal_expansion_1e6"].idxmin()]
    highest_capacity_row = df.loc[df["volumetric_capacity_kj_m3k"].idxmax()]

    highlights = {
        "best_conductor": {
            "name": str(best_conductor_row["name"]),
            "value": float(best_conductor_row["thermal_conductivity"]),
            "unit": "W/(m·K)",
        },
        "best_insulator": {
            "name": str(best_insulator_row["name"]),
            "value": float(best_insulator_row["thermal_conductivity"]),
            "unit": "W/(m·K)",
        },
        "highest_stability": {
            "name": str(highest_stability_row["name"]),
            "value": float(highest_stability_row["thermal_expansion_1e6"]),
            "unit": "×10⁻⁶ K⁻¹",
        },
        "highest_volumetric_capacity": {
            "name": str(highest_capacity_row["name"]),
            "value": float(highest_capacity_row["volumetric_capacity_kj_m3k"]),
            "unit": "kJ/(m³·K)",
        },
    }

    summary_stats = {
        "count": int(len(df)),
        "mean_conductivity": round(float(df["thermal_conductivity"].mean()), 4),
        "max_conductivity": round(float(df["thermal_conductivity"].max()), 4),
        "min_conductivity": round(float(df["thermal_conductivity"].min()), 4),
        "mean_expansion_1e6": round(float(df["thermal_expansion_1e6"].mean()), 3),
        "mean_specific_heat": round(float(df["specific_heat"].mean()), 2),
    }

    return {
        "parameters": {
            "mass_kg": m,
            "length_m": l_comp,
            "area_m2": a_val,
            "thickness_m": esp,
            "delta_t_c": dt,
        },
        "rows": df.to_dict(orient="records"),
        "highlights": highlights,
        "summary_stats": summary_stats,
    }


def simulate_temperature_variation(
    material_dict: dict[str, Any],
    temp_start: float,
    temp_end: float,
    steps: int = 25,
    mass: float = 1.0,
    length: float = 1.0,
    area: float = 1.0,
    thickness: float = 0.05,
    h_conv: float = 25.0,
    sim_time_max: float = 600.0,
) -> dict[str, Any]:
    """Executa simulação paramétrica de temperatura e análise transiente (Newton / Biot).

    1) Simulação Paramétrica: avalia Q(T), ΔL(T) e Q̇_cond(T) em toda a faixa [T_start, T_end].
    2) Simulação Transiente: aplica o Método da Capacitância Global com cálculo do
       Número de Biot (Bi = h * Lc / k) e constante de tempo térmica (τ = m*c / (h*A)).
    """
    mat_name = str(material_dict.get("name", "Material Selecionado"))
    c = _validate_positive(material_dict.get("specific_heat"), f"Calor específico de {mat_name}")
    alpha = _validate_positive(material_dict.get("thermal_expansion"), f"Dilatação α de {mat_name}")
    k = _validate_positive(material_dict.get("thermal_conductivity"), f"Condutividade k de {mat_name}")
    rho = _validate_positive(material_dict.get("density"), f"Densidade ρ de {mat_name}")

    t_start = _validate_finite(temp_start, "Temperatura Inicial (°C)")
    t_end = _validate_finite(temp_end, "Temperatura Final / Ambiente (°C)")
    m = _validate_positive(mass, "Massa (kg)")
    l_comp = _validate_positive(length, "Comprimento Inicial (m)")
    a_surf = _validate_positive(area, "Área Superficial / Troca (m²)")
    esp = _validate_positive(thickness, "Espessura de Parede (m)")
    h = _validate_positive(h_conv, "Coeficiente de Convecção h (W/m²·K)")
    t_max_sim = _validate_positive(sim_time_max, "Tempo Máximo de Simulação (s)")

    try:
        n_steps = int(steps)
    except (TypeError, ValueError) as exc:
        raise ValueError("Número de pontos (steps) deve ser um inteiro.") from exc
    if n_steps < 2 or n_steps > 500:
        raise ValueError("O número de pontos da simulação deve estar entre 2 e 500.")

    # 1. Simulação Paramétrica Estacionária
    temps_vec = np.linspace(t_start, t_end, n_steps)
    dt_vec = temps_vec - t_start
    q_sensible_kj_vec = (m * c * dt_vec) / 1000.0
    delta_l_mm_vec = (l_comp * alpha * dt_vec) * 1000.0
    final_len_m_vec = l_comp + (l_comp * alpha * dt_vec)
    conduction_w_vec = (k * a_surf * dt_vec) / esp

    df_param = pd.DataFrame(
        {
            "step": np.arange(1, n_steps + 1),
            "temp_c": np.round(temps_vec, 2),
            "delta_t_c": np.round(dt_vec, 2),
            "heat_kj": np.round(q_sensible_kj_vec, 4),
            "delta_l_mm": np.round(delta_l_mm_vec, 5),
            "final_length_m": np.round(final_len_m_vec, 7),
            "conduction_w": np.round(conduction_w_vec, 3),
        }
    )

    # 2. Simulação Transiente (Lei de Resfriamento de Newton / Capacitância Global)
    volume_m3 = m / rho
    l_char_m = volume_m3 / a_surf
    biot_number = (h * l_char_m) / k
    lumped_valid = bool(biot_number < 0.1)
    time_constant_s = (m * c) / (h * a_surf)
    time_95_s = 3.0 * time_constant_s

    times_vec = np.linspace(0.0, t_max_sim, n_steps)
    temp_trans_vec = t_end + (t_start - t_end) * np.exp(-times_vec / time_constant_s)
    heat_rate_trans_vec = h * a_surf * (temp_trans_vec - t_end)

    df_trans = pd.DataFrame(
        {
            "step": np.arange(1, n_steps + 1),
            "time_s": np.round(times_vec, 2),
            "temp_c": np.round(temp_trans_vec, 3),
            "heat_rate_w": np.round(heat_rate_trans_vec, 3),
        }
    )

    max_temp_mat = material_dict.get("max_temp")
    exceeds_max_temp = False
    if max_temp_mat is not None:
        exceeds_max_temp = bool(max(t_start, t_end) > float(max_temp_mat))

    return {
        "material_name": mat_name,
        "parameters": {
            "temp_start_c": t_start,
            "temp_end_c": t_end,
            "steps": n_steps,
            "mass_kg": m,
            "length_m": l_comp,
            "area_m2": a_surf,
            "thickness_m": esp,
            "h_conv_w_m2k": h,
            "sim_time_max_s": t_max_sim,
        },
        "physical_indicators": {
            "volume_m3": round(volume_m3, 8),
            "characteristic_length_m": round(l_char_m, 6),
            "biot_number": round(biot_number, 6),
            "lumped_valid": lumped_valid,
            "time_constant_s": round(time_constant_s, 3),
            "time_95_percent_s": round(time_95_s, 3),
            "final_transient_temp_c": round(float(temp_trans_vec[-1]), 3),
            "exceeds_max_temp": exceeds_max_temp,
            "max_temp_c": max_temp_mat,
        },
        "parametric_series": {
            "temps_c": df_param["temp_c"].tolist(),
            "heat_kj": df_param["heat_kj"].tolist(),
            "delta_l_mm": df_param["delta_l_mm"].tolist(),
            "conduction_w": df_param["conduction_w"].tolist(),
        },
        "transient_series": {
            "times_s": df_trans["time_s"].tolist(),
            "temps_c": df_trans["temp_c"].tolist(),
            "heat_rate_w": df_trans["heat_rate_w"].tolist(),
        },
        "parametric_records": df_param.to_dict(orient="records"),
        "transient_records": df_trans.to_dict(orient="records"),
    }
