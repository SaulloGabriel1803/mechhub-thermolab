"""Gerador de relatórios técnicos em PDF (ReportLab) e exportação CSV (Pandas)."""

from __future__ import annotations

import io
from datetime import datetime
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from modules.thermolab.charts import generate_matplotlib_summary_chart


def _format_result_summary(calc: dict[str, Any]) -> str:
    """Resume o dicionário de resultado de um cálculo para exibição tabular no PDF."""
    ctype = calc.get("calc_type", "")
    res = calc.get("result_data", {})
    if ctype == "calor_sensivel":
        return f"Q = {res.get('heat_kj', 0):.3f} kJ | ΔT = {res.get('delta_t_c', 0):.2f} °C"
    if ctype == "dilatacao":
        return (
            f"Δ = {res.get('delta_sub_measure', 0):.4f} {res.get('delta_sub_unit', '')} | "
            f"ε = {res.get('strain_percent', 0):.4f}%"
        )
    if ctype == "conducao":
        return f"Q̇ = {res.get('heat_rate_w', 0):.2f} W | R = {res.get('thermal_resistance_kw', 0):.4f} K/W"
    if ctype == "resistencia":
        return f"R_eq = {res.get('r_total_kw', 0):.4f} K/W | U = {res.get('u_overall_w_m2k', 0):.2f} W/m²K"
    if ctype == "comparacao":
        hl = res.get("highlights", {})
        best = hl.get("best_conductor", {}).get("name", "-")
        return f"{res.get('summary_stats', {}).get('count', 0)} materiais | Melhor condutor: {best}"
    if ctype == "simulacao":
        ind = res.get("physical_indicators", {})
        return f"Bi = {ind.get('biot_number', 0):.4f} | τ = {ind.get('time_constant_s', 0):.1f} s"
    return "-"


def generate_pdf_report(
    materials: list[dict[str, Any]],
    calculations: list[dict[str, Any]],
    summary_stats: dict[str, Any] | None = None,
) -> io.BytesIO:
    """Gera o Relatório Técnico de Análise Térmica em PDF utilizando ReportLab."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title="Relatório Técnico — MechHub Módulo 04: ThermoLab",
        author="Saullo Gabriel Fonseca Souza e Otávio Silva Melo",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MechHubTitle",
        parent=styles["Heading1"],
        fontSize=16,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "MechHubSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "MechHubSection",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#c2410c"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "MechHubBody",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#1e293b"),
    )

    elements: list[Any] = []

    # Cabeçalho oficial
    elements.append(
        Paragraph("MechHub — Plataforma SaaS Integrada para Engenharia Mecânica", title_style)
    )
    elements.append(
        Paragraph(
            "<b>Módulo 04: ThermoLab (Análise Térmica)</b> | "
            "Autores: <b>Saullo Gabriel Fonseca Souza e Otávio Silva Melo</b><br/>"
            f"Emissão do relatório: {datetime.now().strftime('%d/%m/%Y às %H:%M:%S')}",
            subtitle_style,
        )
    )

    # Seção 1: Resumo Executivo
    stats = summary_stats or {}
    total_mats = stats.get("total_materials", len(materials))
    total_calcs = stats.get("total_calculations", len(calculations))
    elements.append(Paragraph("1. Resumo Executivo e Indicadores do Módulo", section_style))
    elements.append(
        Paragraph(
            f"Este documento consolida os dados termofísicos cadastrados e o memorial de cálculos "
            f"executados no módulo <b>ThermoLab</b>. Atualmente a base conta com "
            f"<b>{total_mats}</b> materiais de engenharia cadastrados e "
            f"<b>{total_calcs}</b> registros de cálculos/simulações térmicas persistidos.",
            body_style,
        )
    )
    elements.append(Spacer(1, 0.35 * cm))

    # Seção 2: Catálogo de Materiais
    elements.append(Paragraph("2. Catálogo de Materiais Térmicos Cadastrados", section_style))
    if materials:
        mat_table_data = [
            ["Material", "Categoria", "c [J/kg·K]", "α [×10⁻⁶/K]", "k [W/m·K]", "ρ [kg/m³]", "T_máx [°C]"]
        ]
        for m in materials:
            t_max_str = f"{m['max_temp']:.0f}" if m.get("max_temp") is not None else "-"
            mat_table_data.append(
                [
                    Paragraph(str(m["name"]), body_style),
                    str(m.get("category", "-")),
                    f"{m['specific_heat']:.1f}",
                    f"{m['thermal_expansion'] * 1e6:.2f}",
                    f"{m['thermal_conductivity']:.3f}",
                    f"{m['density']:.0f}",
                    t_max_str,
                ]
            )
        mat_table = Table(
            mat_table_data,
            colWidths=[5.1 * cm, 2.3 * cm, 2.0 * cm, 2.2 * cm, 2.0 * cm, 2.0 * cm, 2.0 * cm],
            repeatRows=1,
        )
        mat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(mat_table)
    else:
        elements.append(Paragraph("Nenhum material cadastrado até o momento.", body_style))

    elements.append(Spacer(1, 0.4 * cm))

    # Seção 3: Gráfico Técnico Incorporado (Matplotlib)
    elements.append(Paragraph("3. Análise Gráfica Consolidada", section_style))
    chart_stream = generate_matplotlib_summary_chart(materials, calculations)
    chart_img = Image(chart_stream, width=17.4 * cm, height=6.7 * cm)
    elements.append(chart_img)
    elements.append(Spacer(1, 0.35 * cm))

    # Seção 4: Histórico de Cálculos e Simulações
    elements.append(Paragraph("4. Histórico de Cálculos e Simulações Realizadas", section_style))
    if calculations:
        calc_table_data = [["ID", "Tipo", "Descrição", "Material", "Principais Resultados", "Data"]]
        for c in calculations[:30]:
            calc_table_data.append(
                [
                    str(c.get("id", "")),
                    str(c.get("calc_type", "")),
                    Paragraph(str(c.get("title", "")), body_style),
                    Paragraph(str(c.get("material_name", "-")), body_style),
                    Paragraph(_format_result_summary(c), body_style),
                    str(c.get("created_at", "")),
                ]
            )
        calc_table = Table(
            calc_table_data,
            colWidths=[1.0 * cm, 2.3 * cm, 4.3 * cm, 3.0 * cm, 4.7 * cm, 2.5 * cm],
            repeatRows=1,
        )
        calc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#c2410c")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.8),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff7ed")]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(calc_table)
    else:
        elements.append(
            Paragraph("Nenhum cálculo térmico foi salvo no histórico até o momento.", body_style)
        )

    doc.build(elements)
    buffer.seek(0)
    return buffer


def export_materials_csv(materials: list[dict[str, Any]]) -> io.BytesIO:
    """Exporta a lista de materiais cadastrados para CSV UTF-8 com Pandas."""
    columns = [
        "id",
        "name",
        "category",
        "specific_heat",
        "thermal_expansion",
        "thermal_conductivity",
        "density",
        "max_temp",
        "thermal_diffusivity",
        "notes",
    ]
    df = pd.DataFrame(materials)
    if df.empty:
        df = pd.DataFrame(columns=columns)
    else:
        df = df[[col for col in columns if col in df.columns]]

    csv_text = df.to_csv(index=False, sep=";")
    buffer = io.BytesIO(csv_text.encode("utf-8-sig"))
    buffer.seek(0)
    return buffer


def export_calculations_csv(calculations: list[dict[str, Any]]) -> io.BytesIO:
    """Exporta o histórico de cálculos térmicos para CSV UTF-8 com Pandas."""
    rows = []
    for calc in calculations:
        rows.append(
            {
                "id": calc.get("id"),
                "calc_type": calc.get("calc_type"),
                "title": calc.get("title"),
                "material_name": calc.get("material_name"),
                "summary": _format_result_summary(calc),
                "created_at": calc.get("created_at"),
            }
        )
    df = pd.DataFrame(
        rows,
        columns=["id", "calc_type", "title", "material_name", "summary", "created_at"],
    )
    csv_text = df.to_csv(index=False, sep=";")
    buffer = io.BytesIO(csv_text.encode("utf-8-sig"))
    buffer.seek(0)
    return buffer
