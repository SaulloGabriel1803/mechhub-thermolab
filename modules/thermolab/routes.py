"""Rotas Flask (Blueprint) do Módulo 04: ThermoLab - Análise Térmica."""

from __future__ import annotations

import json
from typing import Any

from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from extensions import db
from modules.thermolab.calculator import (
    calculate_sensible_heat,
    calculate_thermal_conduction,
    calculate_thermal_expansion,
    calculate_thermal_resistance,
    compare_materials,
    simulate_temperature_variation,
)
from modules.thermolab.charts import (
    build_comparison_charts,
    build_conduction_chart,
    build_expansion_chart,
    build_materials_overview_chart,
    build_resistance_chart,
    build_sensible_heat_chart,
    build_simulation_charts,
)
from modules.thermolab.models import ThermalCalculation, ThermalMaterial
from modules.thermolab.reports import (
    export_calculations_csv,
    export_materials_csv,
    generate_pdf_report,
)

thermolab_bp = Blueprint(
    "thermolab",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/thermolab",
)


def get_material_visual(name: str, category: str = "Metálico") -> dict[str, str]:
    """Retorna swatch visual (gradiente metálico/mineral e sigla) para reconhecimento rápido."""
    low = (name or "").lower()
    if "cobre" in low:
        return {"bg": "linear-gradient(135deg, #f59e0b, #b45309)", "code": "Cu"}
    if "latão" in low or "latao" in low or "bronze" in low:
        return {"bg": "linear-gradient(135deg, #fde047, #ca8a04)", "code": "Cz"}
    if "alumínio" in low or "aluminio" in low:
        return {"bg": "linear-gradient(135deg, #f4f4f5, #a1a1aa)", "code": "Al"}
    if "inox" in low:
        return {"bg": "linear-gradient(135deg, #e2e8f0, #64748b)", "code": "SS"}
    if "titânio" in low or "titanio" in low:
        return {"bg": "linear-gradient(135deg, #d4d4d8, #52525b)", "code": "Ti"}
    if "ferro" in low:
        return {"bg": "linear-gradient(135deg, #71717a, #27272a)", "code": "Fe"}
    if "aço" in low or "aco" in low:
        return {"bg": "linear-gradient(135deg, #94a3b8, #475569)", "code": "Ac"}
    if "lã" in low or "isolante" in (category or "").lower():
        return {"bg": "linear-gradient(135deg, #fef08a, #d97706)", "code": "Is"}

    cat_map = {
        "Metálico": {"bg": "linear-gradient(135deg, #cbd5e1, #64748b)", "code": "Mt"},
        "Polimérico": {"bg": "linear-gradient(135deg, #38bdf8, #0284c7)", "code": "Po"},
        "Cerâmico": {"bg": "linear-gradient(135deg, #fb7185, #be123c)", "code": "Ce"},
        "Compósito": {"bg": "linear-gradient(135deg, #34d399, #059669)", "code": "Cp"},
        "Isolante": {"bg": "linear-gradient(135deg, #fde047, #ca8a04)", "code": "Is"},
    }
    return cat_map.get(category or "Metálico", {"bg": "linear-gradient(135deg, #a1a1aa, #52525b)", "code": "Ma"})


@thermolab_bp.app_context_processor
def inject_thermolab_helpers():
    """Disponibiliza helpers visuais para todos os templates do módulo."""
    return {"mat_visual": get_material_visual}


def _parse_float(raw_value: Any, field_label: str, required: bool = True) -> float | None:
    """Converte entrada de formulário (aceitando vírgula ou ponto) para float."""
    if raw_value is None:
        if required:
            raise ValueError(f"O campo '{field_label}' é obrigatório.")
        return None
    text = str(raw_value).strip().replace(",", ".")
    if text == "":
        if required:
            raise ValueError(f"O campo '{field_label}' é obrigatório.")
        return None
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Valor numérico inválido para '{field_label}': '{raw_value}'.") from exc


def _save_calculation(
    calc_type: str,
    title: str,
    input_data: dict[str, Any],
    result_data: dict[str, Any],
    material_id: int | None = None,
) -> ThermalCalculation:
    """Persiste um cálculo ou simulação térmica na tabela ThermalCalculation."""
    # Remove séries extensas redundantes apenas se necessário ou mantém JSON completo
    record = ThermalCalculation(
        calc_type=calc_type,
        title=title[:150],
        material_id=material_id,
        input_data=json.dumps(input_data, ensure_ascii=False),
        result_data=json.dumps(result_data, ensure_ascii=False),
    )
    db.session.add(record)
    db.session.commit()
    return record


@thermolab_bp.route("/")
def dashboard():
    """Página inicial do módulo ThermoLab com KPIs, atalhos e histórico recente."""
    materials = ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()
    recent_calcs = (
        ThermalCalculation.query.order_by(ThermalCalculation.created_at.desc())
        .limit(8)
        .all()
    )
    total_calcs = ThermalCalculation.query.count()

    # Contagens por tipo de cálculo
    type_counts_raw = (
        db.session.query(ThermalCalculation.calc_type, db.func.count(ThermalCalculation.id))
        .group_by(ThermalCalculation.calc_type)
        .all()
    )
    type_counts = {ctype: count for ctype, count in type_counts_raw}

    materials_dicts = [m.to_dict() for m in materials]
    overview_chart_json = build_materials_overview_chart(materials_dicts)

    best_conductor = (
        max(materials_dicts, key=lambda m: m["thermal_conductivity"])
        if materials_dicts
        else None
    )
    best_insulator = (
        min(materials_dicts, key=lambda m: m["thermal_conductivity"])
        if materials_dicts
        else None
    )
    max_k = max((m["thermal_conductivity"] for m in materials_dicts), default=1.0)
    max_alpha = max((m["thermal_expansion"] for m in materials_dicts), default=1e-5)

    return render_template(
        "thermolab/dashboard.html",
        active_page="dashboard",
        total_materials=len(materials),
        total_calculations=total_calcs,
        type_counts=type_counts,
        best_conductor=best_conductor,
        best_insulator=best_insulator,
        materials_showcase=materials_dicts,
        max_k=max_k,
        max_alpha=max_alpha,
        recent_calcs=[c.to_dict() for c in recent_calcs],
        overview_chart_json=overview_chart_json,
    )


@thermolab_bp.route("/materials", methods=["GET", "POST"])
def materials():
    """Funcionalidade 1: Cadastrar, listar, filtrar, editar e excluir materiais."""
    if request.method == "POST":
        try:
            name = (request.form.get("name") or "").strip()
            category = (request.form.get("category") or "Metálico").strip()
            if not name:
                raise ValueError("O nome do material é obrigatório.")

            if ThermalMaterial.query.filter(
                db.func.lower(ThermalMaterial.name) == name.lower()
            ).first():
                raise ValueError(f"Já existe um material cadastrado com o nome '{name}'.")

            specific_heat = _parse_float(request.form.get("specific_heat"), "Calor Específico c")
            # Aceita α em formato direto (ex: 11.7e-6) ou multiplicado por 1e-6 conforme flag
            alpha_raw = _parse_float(request.form.get("thermal_expansion"), "Coef. de Dilatação α")
            alpha_unit_scale = request.form.get("alpha_scale", "direct")
            if alpha_unit_scale == "1e-6":
                alpha_val = alpha_raw * 1e-6
            else:
                alpha_val = alpha_raw

            conductivity = _parse_float(
                request.form.get("thermal_conductivity"), "Condutividade Térmica k"
            )
            density = _parse_float(request.form.get("density"), "Densidade ρ")
            max_temp = _parse_float(
                request.form.get("max_temp"), "Temperatura Máxima", required=False
            )
            notes = (request.form.get("notes") or "").strip()

            for val, label in [
                (specific_heat, "Calor Específico"),
                (alpha_val, "Coeficiente de Dilatação"),
                (conductivity, "Condutividade Térmica"),
                (density, "Densidade"),
            ]:
                if val is None or val <= 0:
                    raise ValueError(f"{label} deve ser estritamente maior que zero.")

            new_mat = ThermalMaterial(
                name=name,
                category=category,
                specific_heat=specific_heat,
                thermal_expansion=alpha_val,
                thermal_conductivity=conductivity,
                density=density,
                max_temp=max_temp,
                notes=notes,
            )
            db.session.add(new_mat)
            db.session.commit()
            flash(f"Material '{name}' cadastrado com sucesso!", "success")
            return redirect(url_for("thermolab.materials"))
        except ValueError as err:
            flash(str(err), "danger")

    search_q = (request.args.get("q") or "").strip()
    filter_cat = (request.args.get("category") or "").strip()

    query = ThermalMaterial.query
    if search_q:
        query = query.filter(ThermalMaterial.name.ilike(f"%{search_q}%"))
    if filter_cat:
        query = query.filter(ThermalMaterial.category == filter_cat)

    materials_list = query.order_by(ThermalMaterial.name.asc()).all()
    categories = [
        row[0]
        for row in db.session.query(ThermalMaterial.category).distinct().order_by(ThermalMaterial.category).all()
    ]
    all_mats = ThermalMaterial.query.all()
    max_k = max((m.thermal_conductivity for m in all_mats), default=1.0)
    max_alpha = max((m.thermal_expansion for m in all_mats), default=1e-5)

    return render_template(
        "thermolab/materials.html",
        active_page="materials",
        materials=materials_list,
        categories=categories,
        search_q=search_q,
        filter_cat=filter_cat,
        max_k=max_k,
        max_alpha=max_alpha,
    )


@thermolab_bp.route("/materials/edit/<int:material_id>", methods=["POST"])
def edit_material(material_id: int):
    """Atualiza os parâmetros termofísicos de um material existente."""
    mat = db.session.get(ThermalMaterial, material_id)
    if mat is None:
        flash("Material não encontrado.", "warning")
        return redirect(url_for("thermolab.materials"))

    try:
        name = (request.form.get("name") or "").strip()
        if not name:
            raise ValueError("O nome do material é obrigatório.")

        duplicate = ThermalMaterial.query.filter(
            db.func.lower(ThermalMaterial.name) == name.lower(),
            ThermalMaterial.id != material_id,
        ).first()
        if duplicate:
            raise ValueError(f"Outro material já utiliza o nome '{name}'.")

        specific_heat = _parse_float(request.form.get("specific_heat"), "Calor Específico c")
        thermal_expansion = _parse_float(request.form.get("thermal_expansion"), "Dilatação α")
        thermal_conductivity = _parse_float(
            request.form.get("thermal_conductivity"), "Condutividade k"
        )
        density = _parse_float(request.form.get("density"), "Densidade ρ")
        max_temp = _parse_float(
            request.form.get("max_temp"), "Temperatura Máxima", required=False
        )

        for val, label in [
            (specific_heat, "Calor Específico"),
            (thermal_expansion, "Coeficiente de Dilatação"),
            (thermal_conductivity, "Condutividade Térmica"),
            (density, "Densidade"),
        ]:
            if val is None or val <= 0:
                raise ValueError(f"{label} deve ser maior que zero.")

        mat.name = name
        mat.category = (request.form.get("category") or mat.category).strip()
        mat.specific_heat = specific_heat
        mat.thermal_expansion = thermal_expansion
        mat.thermal_conductivity = thermal_conductivity
        mat.density = density
        mat.max_temp = max_temp
        mat.notes = (request.form.get("notes") or "").strip()
        db.session.commit()
        flash(f"Material '{mat.name}' atualizado com sucesso!", "success")
    except ValueError as err:
        flash(str(err), "danger")

    return redirect(url_for("thermolab.materials"))


@thermolab_bp.route("/materials/delete/<int:material_id>", methods=["POST"])
def delete_material(material_id: int):
    """Remove um material do banco de dados."""
    mat = db.session.get(ThermalMaterial, material_id)
    if mat is None:
        flash("Material não encontrado.", "warning")
    else:
        mat_name = mat.name
        db.session.delete(mat)
        db.session.commit()
        flash(f"Material '{mat_name}' excluído do catálogo.", "info")
    return redirect(url_for("thermolab.materials"))


@thermolab_bp.route("/api/materials", methods=["GET"])
def api_list_materials():
    """Endpoint JSON público do módulo para integração futura com outros módulos do MechHub."""
    mats = ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()
    return jsonify([m.to_dict() for m in mats])


@thermolab_bp.route("/calculations", methods=["GET", "POST"])
def calculations():
    """Funcionalidades 2, 3, 4 e 5: Calor Sensível, Dilatação, Condução e Resistência Térmica."""
    all_materials = ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()
    materials_json = [m.to_dict() for m in all_materials]

    active_tab = request.args.get("tab") or request.form.get("calc_type") or "calor_sensivel"
    mat_query_id = request.args.get("material_id") or request.form.get("material_id")
    selected_material_id = (
        int(mat_query_id) if mat_query_id and str(mat_query_id).isdigit() else None
    )
    calc_result: dict[str, Any] | None = None
    chart_json: str | None = None

    if request.method == "POST":
        calc_type = (request.form.get("calc_type") or "calor_sensivel").strip()
        active_tab = calc_type
        mat_id_raw = request.form.get("material_id")
        material_id = int(mat_id_raw) if mat_id_raw and mat_id_raw.isdigit() else None
        mat_obj = db.session.get(ThermalMaterial, material_id) if material_id else None

        try:
            if calc_type == "calor_sensivel":
                mass = _parse_float(request.form.get("mass"), "Massa (kg)")
                c_val = _parse_float(request.form.get("specific_heat"), "Calor Específico c")
                t_i = _parse_float(request.form.get("temp_initial"), "Temperatura Inicial")
                t_f = _parse_float(request.form.get("temp_final"), "Temperatura Final")
                t_sec = _parse_float(
                    request.form.get("time_seconds"), "Tempo de Processo", required=False
                )

                calc_result = calculate_sensible_heat(mass, c_val, t_i, t_f, t_sec)
                chart_json = build_sensible_heat_chart(calc_result)
                mat_label = mat_obj.name if mat_obj else "Entrada Manual"
                title = f"Calor Sensível ({mat_label}: {t_i:.0f}°C → {t_f:.0f}°C)"
                _save_calculation(
                    calc_type="calor_sensivel",
                    title=title,
                    input_data={
                        "mass": mass,
                        "specific_heat": c_val,
                        "temp_initial": t_i,
                        "temp_final": t_f,
                        "time_seconds": t_sec,
                    },
                    result_data=calc_result,
                    material_id=material_id,
                )
                flash("Cálculo de Calor Sensível executado e salvo no histórico!", "success")

            elif calc_type == "dilatacao":
                x0 = _parse_float(request.form.get("initial_measure"), "Medida Inicial")
                alpha = _parse_float(request.form.get("alpha"), "Coeficiente α")
                t_i = _parse_float(request.form.get("temp_initial"), "Temperatura Inicial")
                t_f = _parse_float(request.form.get("temp_final"), "Temperatura Final")
                mode = (request.form.get("mode") or "linear").strip()
                max_t = _parse_float(
                    request.form.get("max_temp"), "Temperatura Máxima", required=False
                )
                if max_t is None and mat_obj is not None:
                    max_t = mat_obj.max_temp

                calc_result = calculate_thermal_expansion(
                    x0, alpha, t_i, t_f, mode=mode, max_temp=max_t
                )
                chart_json = build_expansion_chart(calc_result)
                mat_label = mat_obj.name if mat_obj else "Entrada Manual"
                title = f"Dilatação {mode.capitalize()} ({mat_label}: ΔT={t_f - t_i:.1f}°C)"
                _save_calculation(
                    calc_type="dilatacao",
                    title=title,
                    input_data={
                        "initial_measure": x0,
                        "alpha": alpha,
                        "temp_initial": t_i,
                        "temp_final": t_f,
                        "mode": mode,
                        "max_temp": max_t,
                    },
                    result_data=calc_result,
                    material_id=material_id,
                )
                flash("Cálculo de Dilatação Térmica executado e salvo no histórico!", "success")

            elif calc_type == "conducao":
                geometry = (request.form.get("geometry") or "flat").strip()
                k_val = _parse_float(request.form.get("thermal_conductivity"), "Condutividade k")
                t1 = _parse_float(request.form.get("temp_hot"), "Temperatura Face Quente T1")
                t2 = _parse_float(request.form.get("temp_cold"), "Temperatura Face Fria T2")

                if geometry == "cylindrical":
                    r1 = _parse_float(request.form.get("r_inner"), "Raio Interno r1")
                    r2 = _parse_float(request.form.get("r_outer"), "Raio Externo r2")
                    tube_len = _parse_float(request.form.get("length"), "Comprimento do Tubo L")
                    calc_result = calculate_thermal_conduction(
                        k=k_val,
                        area=1.0,
                        thickness=1.0,
                        temp_hot=t1,
                        temp_cold=t2,
                        geometry="cylindrical",
                        r_inner=r1,
                        r_outer=r2,
                        length=tube_len,
                    )
                    input_payload = {
                        "geometry": "cylindrical",
                        "k": k_val,
                        "r_inner": r1,
                        "r_outer": r2,
                        "length": tube_len,
                        "temp_hot": t1,
                        "temp_cold": t2,
                    }
                else:
                    area = _parse_float(request.form.get("area"), "Área de Troca (m²)")
                    thickness = _parse_float(request.form.get("thickness"), "Espessura (m)")
                    calc_result = calculate_thermal_conduction(
                        k=k_val,
                        area=area,
                        thickness=thickness,
                        temp_hot=t1,
                        temp_cold=t2,
                        geometry="flat",
                    )
                    input_payload = {
                        "geometry": "flat",
                        "k": k_val,
                        "area": area,
                        "thickness": thickness,
                        "temp_hot": t1,
                        "temp_cold": t2,
                    }

                chart_json = build_conduction_chart(calc_result)
                mat_label = mat_obj.name if mat_obj else "Entrada Manual"
                title = f"Condução ({geometry}, {mat_label}: {t1:.0f}°C → {t2:.0f}°C)"
                _save_calculation(
                    calc_type="conducao",
                    title=title,
                    input_data=input_payload,
                    result_data=calc_result,
                    material_id=material_id,
                )
                flash("Cálculo de Condução Térmica executado e salvo no histórico!", "success")

            elif calc_type == "resistencia":
                area = _parse_float(request.form.get("area"), "Área Transversal (m²)")
                t_in = _parse_float(request.form.get("temp_inner"), "Temperatura Interna (°C)")
                t_out = _parse_float(request.form.get("temp_outer"), "Temperatura Externa (°C)")
                h_in = _parse_float(request.form.get("h_inner"), "Convecção Interna h_i", required=False)
                h_out = _parse_float(request.form.get("h_outer"), "Convecção Externa h_e", required=False)

                names = request.form.getlist("layer_name[]")
                thicknesses = request.form.getlist("layer_thickness[]")
                ks = request.form.getlist("layer_k[]")

                layers_payload = []
                for idx, (lname, lthick, lk) in enumerate(zip(names, thicknesses, ks), start=1):
                    if str(lthick).strip() == "" and str(lk).strip() == "":
                        continue
                    layers_payload.append(
                        {
                            "name": (lname or f"Camada {idx}").strip(),
                            "thickness": _parse_float(lthick, f"Espessura da Camada {idx}"),
                            "k": _parse_float(lk, f"Condutividade k da Camada {idx}"),
                        }
                    )

                calc_result = calculate_thermal_resistance(
                    layers=layers_payload,
                    area=area,
                    temp_inner=t_in,
                    temp_outer=t_out,
                    h_inner=h_in,
                    h_outer=h_out,
                )
                chart_json = build_resistance_chart(calc_result)
                title = f"Resistência Multicamadas ({len(layers_payload)} camadas, {t_in:.0f}°C → {t_out:.0f}°C)"
                _save_calculation(
                    calc_type="resistencia",
                    title=title,
                    input_data={
                        "area": area,
                        "temp_inner": t_in,
                        "temp_outer": t_out,
                        "h_inner": h_in,
                        "h_outer": h_out,
                        "layers": layers_payload,
                    },
                    result_data=calc_result,
                    material_id=None,
                )
                flash("Análise de Resistência Térmica executada e salva no histórico!", "success")
            else:
                raise ValueError(f"Tipo de cálculo '{calc_type}' não reconhecido.")

        except ValueError as err:
            flash(str(err), "danger")

    recent_calcs = (
        ThermalCalculation.query.filter(
            ThermalCalculation.calc_type.in_(
                ["calor_sensivel", "dilatacao", "conducao", "resistencia"]
            )
        )
        .order_by(ThermalCalculation.created_at.desc())
        .limit(6)
        .all()
    )

    return render_template(
        "thermolab/calculations.html",
        active_page="calculations",
        active_tab=active_tab,
        materials=all_materials,
        materials_json=materials_json,
        selected_material_id=selected_material_id,
        calc_result=calc_result,
        chart_json=chart_json,
        recent_calcs=[c.to_dict() for c in recent_calcs],
    )


@thermolab_bp.route("/comparison", methods=["GET", "POST"])
def comparison():
    """Funcionalidade 6: Comparação termofísica entre múltiplos materiais."""
    all_materials = ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()
    comparison_result: dict[str, Any] | None = None
    chart_json: str | None = None

    selected_ids: list[int] = []
    params = {
        "mass": 10.0,
        "length": 2.0,
        "area": 1.0,
        "thickness": 0.05,
        "delta_t": 100.0,
    }

    if request.method == "POST":
        try:
            raw_ids = request.form.getlist("material_ids")
            selected_ids = [int(i) for i in raw_ids if i.isdigit()]
            if len(selected_ids) < 2:
                raise ValueError("Selecione pelo menos 2 materiais para comparação.")

            params["mass"] = _parse_float(request.form.get("mass"), "Massa (kg)") or 10.0
            params["length"] = _parse_float(request.form.get("length"), "Comprimento (m)") or 2.0
            params["area"] = _parse_float(request.form.get("area"), "Área (m²)") or 1.0
            params["thickness"] = _parse_float(request.form.get("thickness"), "Espessura (m)") or 0.05
            params["delta_t"] = _parse_float(request.form.get("delta_t"), "Variação ΔT (°C)") or 100.0

            chosen_mats = ThermalMaterial.query.filter(ThermalMaterial.id.in_(selected_ids)).all()
            comparison_result = compare_materials(
                [m.to_dict() for m in chosen_mats],
                mass=params["mass"],
                length=params["length"],
                area=params["area"],
                thickness=params["thickness"],
                delta_t=params["delta_t"],
            )
            chart_json = build_comparison_charts(comparison_result)

            _save_calculation(
                calc_type="comparacao",
                title=f"Comparação de {len(chosen_mats)} materiais (ΔT={params['delta_t']:.0f}°C)",
                input_data={"material_ids": selected_ids, **params},
                result_data=comparison_result,
                material_id=None,
            )
            flash("Comparação entre materiais concluída e salva no histórico!", "success")
        except ValueError as err:
            flash(str(err), "danger")
    else:
        # Pré-seleciona até 4 materiais na carga inicial para facilitar a experiência
        if all_materials:
            selected_ids = [m.id for m in all_materials[:4]]
            comparison_result = compare_materials(
                [m.to_dict() for m in all_materials[:4]],
                **params,
            )
            chart_json = build_comparison_charts(comparison_result)

    return render_template(
        "thermolab/comparison.html",
        active_page="comparison",
        materials=all_materials,
        selected_ids=selected_ids,
        params=params,
        comparison_result=comparison_result,
        chart_json=chart_json,
    )


@thermolab_bp.route("/simulation", methods=["GET", "POST"])
def simulation():
    """Funcionalidade 7: Simulação paramétrica de temperatura e resposta transiente (Newton/Biot)."""
    all_materials = ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()
    sim_result: dict[str, Any] | None = None
    chart_json: str | None = None

    sim_mat_query = request.args.get("material_id")
    if sim_mat_query and sim_mat_query.isdigit():
        selected_material_id = int(sim_mat_query)
    else:
        selected_material_id = all_materials[0].id if all_materials else None
    materials_json = [m.to_dict() for m in all_materials]
    form_params = {
        "temp_start": 450.0,
        "temp_end": 25.0,
        "steps": 25,
        "mass": 2.5,
        "length": 1.0,
        "area": 0.45,
        "thickness": 0.02,
        "h_conv": 35.0,
        "sim_time_max": 900.0,
    }

    if request.method == "POST":
        try:
            mat_id_raw = request.form.get("material_id")
            if not mat_id_raw or not mat_id_raw.isdigit():
                raise ValueError("Selecione um material válido para a simulação.")
            selected_material_id = int(mat_id_raw)
            mat_obj = db.session.get(ThermalMaterial, selected_material_id)
            if mat_obj is None:
                raise ValueError("Material selecionado não encontrado no banco.")

            form_params["temp_start"] = _parse_float(request.form.get("temp_start"), "Temperatura Inicial")
            form_params["temp_end"] = _parse_float(request.form.get("temp_end"), "Temperatura Final")
            form_params["steps"] = int(float(str(request.form.get("steps") or 25).replace(",", ".")))
            form_params["mass"] = _parse_float(request.form.get("mass"), "Massa (kg)")
            form_params["length"] = _parse_float(request.form.get("length"), "Comprimento (m)")
            form_params["area"] = _parse_float(request.form.get("area"), "Área Superficial (m²)")
            form_params["thickness"] = _parse_float(request.form.get("thickness"), "Espessura (m)")
            form_params["h_conv"] = _parse_float(request.form.get("h_conv"), "Coef. de Convecção h")
            form_params["sim_time_max"] = _parse_float(request.form.get("sim_time_max"), "Tempo Máximo (s)")

            sim_result = simulate_temperature_variation(
                material_dict=mat_obj.to_dict(),
                **form_params,
            )
            chart_json = build_simulation_charts(sim_result)

            _save_calculation(
                calc_type="simulacao",
                title=(
                    f"Simulação {mat_obj.name} "
                    f"({form_params['temp_start']:.0f}°C → {form_params['temp_end']:.0f}°C)"
                ),
                input_data={"material_id": selected_material_id, **form_params},
                result_data=sim_result,
                material_id=selected_material_id,
            )
            flash("Simulação térmica paramétrica e transiente executada e salva!", "success")
        except ValueError as err:
            flash(str(err), "danger")

    return render_template(
        "thermolab/simulation.html",
        active_page="simulation",
        materials=all_materials,
        materials_json=materials_json,
        selected_material_id=selected_material_id,
        form_params=form_params,
        sim_result=sim_result,
        chart_json=chart_json,
    )


@thermolab_bp.route("/reports", methods=["GET"])
def reports():
    """Funcionalidade 8: Central de gráficos, histórico e exportação de relatórios PDF/CSV."""
    materials = ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()
    calculations = ThermalCalculation.query.order_by(ThermalCalculation.created_at.desc()).all()

    materials_dicts = [m.to_dict() for m in materials]
    calcs_dicts = [c.to_dict() for c in calculations]
    overview_chart_json = build_materials_overview_chart(materials_dicts)

    return render_template(
        "thermolab/reports.html",
        active_page="reports",
        materials=materials_dicts,
        calculations=calcs_dicts,
        overview_chart_json=overview_chart_json,
    )


@thermolab_bp.route("/reports/pdf", methods=["GET"])
def download_pdf_report():
    """Gera e envia o Relatório Técnico completo em formato PDF via ReportLab."""
    materials = [m.to_dict() for m in ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()]
    calculations = [
        c.to_dict() for c in ThermalCalculation.query.order_by(ThermalCalculation.created_at.desc()).all()
    ]
    stats = {
        "total_materials": len(materials),
        "total_calculations": len(calculations),
    }
    pdf_buffer = generate_pdf_report(materials, calculations, stats)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="MechHub_ThermoLab_Relatorio_Tecnico.pdf",
    )


@thermolab_bp.route("/reports/materials.csv", methods=["GET"])
def download_materials_csv():
    """Exporta o catálogo de materiais térmicos em arquivo CSV."""
    materials = [m.to_dict() for m in ThermalMaterial.query.order_by(ThermalMaterial.name.asc()).all()]
    csv_buffer = export_materials_csv(materials)
    return send_file(
        csv_buffer,
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name="thermolab_materiais.csv",
    )


@thermolab_bp.route("/reports/calculations.csv", methods=["GET"])
def download_calculations_csv():
    """Exporta o histórico de cálculos térmicos em arquivo CSV."""
    calculations = [
        c.to_dict() for c in ThermalCalculation.query.order_by(ThermalCalculation.created_at.desc()).all()
    ]
    csv_buffer = export_calculations_csv(calculations)
    return send_file(
        csv_buffer,
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name="thermolab_historico_calculos.csv",
    )


@thermolab_bp.route("/calculations/clear", methods=["POST"])
def clear_calculations():
    """Limpa todo o histórico de cálculos salvos do módulo ThermoLab."""
    deleted = ThermalCalculation.query.delete()
    db.session.commit()
    flash(f"Histórico limpo ({deleted} registro(s) removido(s)).", "info")
    return redirect(url_for("thermolab.reports"))
