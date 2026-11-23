"""Geradores de gráficos interativos (Plotly) e estáticos para PDF (Matplotlib)."""

from __future__ import annotations

import io
import json
import re
from typing import Any

import matplotlib
matplotlib.use("Agg")  # Backend não interativo obrigatório para servidor web
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.utils import PlotlyJSONEncoder


_DARK_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(18, 18, 21, 0.0)",
    plot_bgcolor="rgba(18, 18, 21, 0.65)",
    font=dict(family="JetBrains Mono, Plus Jakarta Sans, sans-serif", color="#e4e4e7", size=11.5),
    title_font=dict(family="Plus Jakarta Sans, sans-serif", size=13.5, color="#fafafa"),
    title_y=0.97,
    margin=dict(l=58, r=28, t=54, b=52),
    hovermode="x unified",
    hoverlabel=dict(
        bgcolor="#18181c",
        bordercolor="#3f3f46",
        font=dict(family="JetBrains Mono, sans-serif", size=11, color="#f4f4f5"),
    ),
    xaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.12)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.12)"),
)


def _short_name(name: str, max_len: int = 21) -> str:
    """Abrevia nomes longos de materiais para rótulos limpos de eixos."""
    clean = re.sub(r"\s*\([^)]*\)", "", str(name or "")).strip()
    replacements = {
        "Eletrolítico ": "",
        "Cinzento ": "",
        "Inoxidável ": "Inox ",
        "Liga de ": "",
        "Carbono ": "",
    }
    for old, new in replacements.items():
        clean = clean.replace(old, new)
    clean = re.sub(r"\s+", " ", clean).strip()
    if len(clean) > max_len:
        return clean[: max_len - 1].rstrip() + "…"
    return clean


def _to_json(fig: go.Figure) -> str:
    """Serializa uma figura Plotly para JSON pronto para Plotly.newPlot."""
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.12)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.06)", zerolinecolor="rgba(255,255,255,0.12)")
    return json.dumps(fig.to_plotly_json(), cls=PlotlyJSONEncoder)


def build_sensible_heat_chart(result: dict[str, Any]) -> str:
    """Gera gráfico Plotly de Calor Sensível Q (kJ) em função da temperatura."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=result["temps_curve"],
            y=result["q_curve_kj"],
            mode="lines+markers",
            name="Calor Sensível Q (kJ)",
            line=dict(color="#f97316", width=3),
            marker=dict(size=6, color="#fb923c"),
            fill="tozeroy",
            fillcolor="rgba(249, 115, 22, 0.14)",
        )
    )
    fig.update_layout(
        **_DARK_LAYOUT,
        title=f"Curva de Energia Térmica — Q = {result['heat_kj']:.3f} kJ",
        xaxis_title="Temperatura (°C)",
        yaxis_title="Calor Sensível Acumulado Q (kJ)",
    )
    return _to_json(fig)


def build_expansion_chart(result: dict[str, Any]) -> str:
    """Gera gráfico Plotly de Dilatação Térmica em função da temperatura."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=result["temps_curve"],
            y=result["delta_sub_curve"],
            mode="lines+markers",
            name=f"Variação ({result['delta_sub_unit']})",
            line=dict(color="#38bdf8", width=3),
            marker=dict(size=6, color="#7dd3fc"),
        )
    )
    fig.update_layout(
        **_DARK_LAYOUT,
        title=f"{result['mode_label']} — Δ = {result['delta_sub_measure']:.4f} {result['delta_sub_unit']}",
        xaxis_title="Temperatura (°C)",
        yaxis_title=f"Variação Dimensional ({result['delta_sub_unit']})",
    )
    return _to_json(fig)


def build_conduction_chart(result: dict[str, Any]) -> str:
    """Gera gráfico Plotly do perfil espacial de temperatura na condução térmica."""
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=result["pos_curve"],
            y=result["temp_curve"],
            mode="lines+markers",
            name="Perfil T(x)",
            line=dict(color="#ef4444", width=3),
            marker=dict(size=5, color="#fca5a5"),
        )
    )
    fig.update_layout(
        **_DARK_LAYOUT,
        title=f"Perfil Térmico — {result['geometry_label']} (Q̇ = {result['heat_rate_w']:.2f} W)",
        xaxis_title=result["position_label"],
        yaxis_title="Temperatura (°C)",
    )
    return _to_json(fig)


def build_resistance_chart(result: dict[str, Any]) -> str:
    """Gera gráfico Plotly de perfil térmico multicamadas e distribuição de resistências."""
    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            "Perfil T(x) na Parede",
            "Participação na Resistência (%)",
        ),
        horizontal_spacing=0.14,
    )

    fig.add_trace(
        go.Scatter(
            x=result["profile_x_m"],
            y=result["profile_t_c"],
            mode="lines+markers+text",
            text=[f"{t:.0f}°C" for t in result["profile_t_c"]],
            textposition="top center",
            name="Temperatura (°C)",
            line=dict(color="#f59e0b", width=3),
            marker=dict(size=8, color="#fbbf24"),
        ),
        row=1,
        col=1,
    )

    for boundary in result.get("layer_boundaries", []):
        fig.add_vline(
            x=boundary["x_end"],
            line_width=1.2,
            line_dash="dash",
            line_color="rgba(161, 161, 170, 0.55)",
            annotation_text=_short_name(boundary["name"], 14),
            annotation_position="top left",
            row=1,
            col=1,
        )

    names = [_short_name(r["name"], 15) for r in result["resistances"]]
    shares = [r["share_percent"] for r in result["resistances"]]
    fig.add_trace(
        go.Bar(
            x=names,
            y=shares,
            text=[f"{s:.1f}%" for s in shares],
            textposition="outside",
            marker_color="#38bdf8",
            name="Participação (%)",
        ),
        row=1,
        col=2,
    )

    layout_cfg = {**_DARK_LAYOUT, "margin": dict(l=54, r=24, t=44, b=64)}
    fig.update_layout(**layout_cfg, showlegend=False, height=390)
    fig.update_annotations(font_size=12, font_color="#e4e4e7")
    fig.update_xaxes(title_text="Espessura (m)", row=1, col=1)
    fig.update_yaxes(title_text="Temperatura (°C)", row=1, col=1)
    fig.update_xaxes(tickangle=-18, row=1, col=2)
    fig.update_yaxes(title_text="Participação (%)", range=[0, 115], row=1, col=2)
    return _to_json(fig)


def build_comparison_charts(comparison_result: dict[str, Any]) -> str:
    """Gera gráfico Plotly comparando condutividade, calor específico e dilatação."""
    rows = comparison_result["rows"]
    short_names = [_short_name(r["name"], 15) for r in rows]
    full_names = [r["name"] for r in rows]

    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=(
            "Condutividade k (W/m·K)",
            "Calor Espec. c (J/kg·K)",
            "Dilatação ΔL (mm)",
        ),
        horizontal_spacing=0.10,
    )

    fig.add_trace(
        go.Bar(
            x=short_names,
            y=[r["thermal_conductivity"] for r in rows],
            hovertext=full_names,
            marker_color="#f97316",
            name="k",
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=short_names,
            y=[r["specific_heat"] for r in rows],
            hovertext=full_names,
            marker_color="#38bdf8",
            name="c",
        ),
        row=1,
        col=2,
    )
    fig.add_trace(
        go.Bar(
            x=short_names,
            y=[r["linear_expansion_mm"] for r in rows],
            hovertext=full_names,
            marker_color="#10b981",
            name="ΔL",
        ),
        row=1,
        col=3,
    )

    layout_cfg = {**_DARK_LAYOUT, "margin": dict(l=52, r=22, t=42, b=78)}
    fig.update_layout(**layout_cfg, showlegend=False, height=380)
    fig.update_annotations(font_size=12, font_color="#e4e4e7")
    fig.update_xaxes(tickangle=-25)
    return _to_json(fig)


def build_simulation_charts(simulation_result: dict[str, Any]) -> str:
    """Gera gráfico duplo Plotly: resposta transiente T(t) e curva paramétrica Q(T)/ΔL(T)."""
    trans = simulation_result["transient_series"]
    param = simulation_result["parametric_series"]
    ind = simulation_result["physical_indicators"]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"Transiente T(t) • τ={ind['time_constant_s']:.0f}s",
            "Paramétrica: Calor Q & Dilatação ΔL",
        ),
        specs=[[{"secondary_y": False}, {"secondary_y": True}]],
        horizontal_spacing=0.14,
    )

    fig.add_trace(
        go.Scatter(
            x=trans["times_s"],
            y=trans["temps_c"],
            mode="lines+markers",
            name="T(t) [°C]",
            line=dict(color="#f97316", width=3),
            marker=dict(size=4),
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Scatter(
            x=param["temps_c"],
            y=param["heat_kj"],
            mode="lines",
            name="Calor Q (kJ)",
            line=dict(color="#38bdf8", width=3),
        ),
        row=1,
        col=2,
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=param["temps_c"],
            y=param["delta_l_mm"],
            mode="lines",
            name="Dilatação ΔL (mm)",
            line=dict(color="#10b981", width=2.5, dash="dot"),
        ),
        row=1,
        col=2,
        secondary_y=True,
    )

    layout_cfg = {**_DARK_LAYOUT, "margin": dict(l=54, r=54, t=44, b=66)}
    fig.update_layout(
        **layout_cfg,
        height=395,
        legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
    )
    fig.update_annotations(font_size=12, font_color="#e4e4e7")
    fig.update_xaxes(title_text="Tempo t (s)", row=1, col=1)
    fig.update_yaxes(title_text="Temperatura (°C)", row=1, col=1)
    fig.update_xaxes(title_text="Temperatura T (°C)", row=1, col=2)
    fig.update_yaxes(title_text="Calor Q (kJ)", row=1, col=2, secondary_y=False)
    fig.update_yaxes(title_text="Dilatação ΔL (mm)", row=1, col=2, secondary_y=True)
    return _to_json(fig)


def build_materials_overview_chart(materials: list[dict[str, Any]]) -> str:
    """Gera ranking horizontal limpo e alternável (k, α, c) sem sobrecarga visual."""
    if not materials:
        fig = go.Figure()
        fig.update_layout(**_DARK_LAYOUT, title="Nenhum material cadastrado")
        return _to_json(fig)

    # Ordena por condutividade térmica crescente (maior fica no topo no barh do Plotly)
    ordered = sorted(materials, key=lambda m: m["thermal_conductivity"])
    short_names = [_short_name(m["name"], 22) for m in ordered]
    full_names = [m["name"] for m in ordered]

    k_vals = [round(m["thermal_conductivity"], 3) for m in ordered]
    alpha_vals = [round(m["thermal_expansion"] * 1e6, 2) for m in ordered]
    c_vals = [round(m["specific_heat"], 1) for m in ordered]

    fig = go.Figure()

    # Trace 0: Condutividade Térmica k (visível por padrão)
    fig.add_trace(
        go.Bar(
            y=short_names,
            x=k_vals,
            orientation="h",
            visible=True,
            name="k [W/(m·K)]",
            text=[f"{v:.2f}" if v < 10 else f"{v:.1f}" for v in k_vals],
            textposition="outside",
            cliponaxis=False,
            hovertext=full_names,
            hovertemplate="<b>%{hovertext}</b><br>k = %{x} W/(m·K)<extra></extra>",
            marker=dict(color="#f97316", line=dict(color="rgba(255,255,255,0.12)", width=1)),
        )
    )

    # Trace 1: Coeficiente de Dilatação α
    fig.add_trace(
        go.Bar(
            y=short_names,
            x=alpha_vals,
            orientation="h",
            visible=False,
            name="α [×10⁻⁶ K⁻¹]",
            text=[f"{v:.1f}" for v in alpha_vals],
            textposition="outside",
            cliponaxis=False,
            hovertext=full_names,
            hovertemplate="<b>%{hovertext}</b><br>α = %{x} ×10⁻⁶ K⁻¹<extra></extra>",
            marker=dict(color="#38bdf8", line=dict(color="rgba(255,255,255,0.12)", width=1)),
        )
    )

    # Trace 2: Calor Específico c
    fig.add_trace(
        go.Bar(
            y=short_names,
            x=c_vals,
            orientation="h",
            visible=False,
            name="c [J/(kg·K)]",
            text=[f"{v:.0f}" for v in c_vals],
            textposition="outside",
            cliponaxis=False,
            hovertext=full_names,
            hovertemplate="<b>%{hovertext}</b><br>c = %{x} J/(kg·K)<extra></extra>",
            marker=dict(color="#10b981", line=dict(color="rgba(255,255,255,0.12)", width=1)),
        )
    )

    max_k = max(k_vals) if k_vals else 100
    layout_cfg = {
        **_DARK_LAYOUT,
        "margin": dict(l=148, r=58, t=18, b=42),
        "hovermode": "closest",
        "yaxis": dict(
            gridcolor="rgba(255,255,255,0.03)",
            automargin=True,
        ),
    }
    fig.update_layout(
        **layout_cfg,
        showlegend=False,
        height=385,
        xaxis_title="Condutividade Térmica k [W/(m·K)]",
        xaxis_range=[0, max_k * 1.16],
    )
    return _to_json(fig)


def generate_matplotlib_summary_chart(
    materials_data: list[dict[str, Any]],
    history_data: list[dict[str, Any]],
) -> io.BytesIO:
    """Gera imagem PNG em memória (BytesIO) via Matplotlib para incorporação no PDF."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.0), dpi=160)
    fig.patch.set_facecolor("#ffffff")

    # Subplot 1: Condutividade térmica dos materiais
    ax1 = axes[0]
    if materials_data:
        names = [_short_name(m["name"], 18) for m in materials_data[:8]]
        k_vals = [m["thermal_conductivity"] for m in materials_data[:8]]
        bars = ax1.barh(names, k_vals, color="#ea580c", edgecolor="#9a3412")
        ax1.invert_yaxis()
        ax1.set_title("Condutividade Térmica k [W/(m·K)]", fontsize=10, fontweight="bold")
        ax1.set_xlabel("W/(m·K)", fontsize=9)
        ax1.grid(axis="x", linestyle="--", alpha=0.4)
        for bar, val in zip(bars, k_vals):
            ax1.text(
                bar.get_width() + max(k_vals) * 0.015,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}",
                va="center",
                fontsize=7.5,
            )
    else:
        ax1.text(0.5, 0.5, "Sem materiais cadastrados", ha="center", va="center")
        ax1.set_title("Condutividade Térmica")

    # Subplot 2: Distribuição de cálculos por tipo
    ax2 = axes[1]
    if history_data:
        counts: dict[str, int] = {}
        label_map = {
            "calor_sensivel": "Calor Sensível",
            "dilatacao": "Dilatação",
            "conducao": "Condução",
            "resistencia": "Resistência",
            "comparacao": "Comparação",
            "simulacao": "Simulação",
        }
        for item in history_data:
            key = label_map.get(item.get("calc_type", ""), item.get("calc_type", "Outro"))
            counts[key] = counts.get(key, 0) + 1

        labels = list(counts.keys())
        values = list(counts.values())
        ax2.bar(labels, values, color="#0284c7", edgecolor="#075985")
        ax2.set_title("Análises Realizadas por Categoria", fontsize=10, fontweight="bold")
        ax2.set_ylabel("Quantidade de Registros", fontsize=9)
        ax2.tick_params(axis="x", rotation=25, labelsize=8)
        ax2.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
        ax2.grid(axis="y", linestyle="--", alpha=0.4)
    else:
        ax2.text(0.5, 0.5, "Sem cálculos registrados", ha="center", va="center")
        ax2.set_title("Análises Realizadas por Categoria")

    plt.tight_layout()
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return buffer
