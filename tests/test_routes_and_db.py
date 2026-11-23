"""Testes de integração do Flask Blueprint, SQLite em memória, rotas e relatórios PDF/CSV."""

import pytest

from app import create_app
from extensions import db
from modules.thermolab.models import ThermalCalculation, ThermalMaterial


@pytest.fixture()
def client():
    """Cria instância de teste do Flask com banco SQLite isolado em memória."""
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "SECRET_KEY": "test-secret",
        }
    )
    with test_app.test_client() as test_client:
        with test_app.app_context():
            yield test_client
            db.session.remove()
            db.drop_all()


def test_seed_and_dashboard_route(client):
    """Verifica seed inicial dos 8 materiais e carregamento do painel."""
    assert ThermalMaterial.query.count() == 8
    resp = client.get("/thermolab/")
    assert resp.status_code == 200
    assert "ThermoLab" in resp.get_data(as_text=True)

    root_resp = client.get("/", follow_redirects=False)
    assert root_resp.status_code == 302
    assert "/thermolab/" in root_resp.headers["Location"]


def test_material_crud_and_api(client):
    """Verifica cadastro, edição, listagem API JSON e exclusão de material."""
    resp = client.post(
        "/thermolab/materials",
        data={
            "name": "Bronze Fosforoso Teste",
            "category": "Metálico",
            "specific_heat": "380",
            "thermal_expansion": "17.8",
            "alpha_scale": "1e-6",
            "thermal_conductivity": "62.0",
            "density": "8800",
            "max_temp": "950",
            "notes": "Teste automatizado",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert "Bronze Fosforoso Teste" in resp.get_data(as_text=True)

    created = ThermalMaterial.query.filter_by(name="Bronze Fosforoso Teste").first()
    assert created is not None
    assert created.thermal_expansion == pytest.approx(17.8e-6)

    api_resp = client.get("/thermolab/api/materials")
    assert api_resp.status_code == 200
    assert any(m["name"] == "Bronze Fosforoso Teste" for m in api_resp.get_json())

    edit_resp = client.post(
        f"/thermolab/materials/edit/{created.id}",
        data={
            "name": "Bronze Fosforoso Atualizado",
            "category": "Metálico",
            "specific_heat": "390",
            "thermal_expansion": "0.000018",
            "thermal_conductivity": "65.0",
            "density": "8850",
            "max_temp": "980",
            "notes": "Editado",
        },
        follow_redirects=True,
    )
    assert edit_resp.status_code == 200
    assert "Bronze Fosforoso Atualizado" in edit_resp.get_data(as_text=True)

    del_resp = client.post(
        f"/thermolab/materials/delete/{created.id}",
        follow_redirects=True,
    )
    assert del_resp.status_code == 200
    assert db.session.get(ThermalMaterial, created.id) is None


def test_calculations_persistence_and_all_workflows(client):
    """Verifica execução e persistência de todas as funcionalidades de cálculo/simulação."""
    mat = ThermalMaterial.query.first()
    assert mat is not None

    # 1. Calor Sensível
    r1 = client.post(
        "/thermolab/calculations",
        data={
            "calc_type": "calor_sensivel",
            "material_id": str(mat.id),
            "mass": "10",
            "specific_heat": str(mat.specific_heat),
            "temp_initial": "25",
            "temp_final": "125",
            "time_seconds": "60",
        },
    )
    assert r1.status_code == 200

    # 2. Dilatação Térmica
    r2 = client.post(
        "/thermolab/calculations",
        data={
            "calc_type": "dilatacao",
            "material_id": str(mat.id),
            "mode": "linear",
            "initial_measure": "3.0",
            "alpha": str(mat.thermal_expansion),
            "temp_initial": "20",
            "temp_final": "120",
        },
    )
    assert r2.status_code == 200

    # 3. Condução Térmica (Cilíndrica)
    r3 = client.post(
        "/thermolab/calculations",
        data={
            "calc_type": "conducao",
            "material_id": str(mat.id),
            "geometry": "cylindrical",
            "thermal_conductivity": str(mat.thermal_conductivity),
            "r_inner": "0.04",
            "r_outer": "0.07",
            "length": "2.5",
            "temp_hot": "250",
            "temp_cold": "40",
        },
    )
    assert r3.status_code == 200

    # 4. Resistência Térmica Multicamadas
    r4 = client.post(
        "/thermolab/calculations",
        data={
            "calc_type": "resistencia",
            "area": "2.0",
            "temp_inner": "500",
            "temp_outer": "30",
            "h_inner": "60",
            "h_outer": "15",
            "layer_name[]": ["Aço", "Isolante"],
            "layer_thickness[]": ["0.01", "0.08"],
            "layer_k[]": ["50", "0.04"],
        },
    )
    assert r4.status_code == 200

    # 5. Comparação de Materiais
    mats = ThermalMaterial.query.limit(3).all()
    r5 = client.post(
        "/thermolab/comparison",
        data={
            "material_ids": [str(m.id) for m in mats],
            "mass": "5",
            "length": "1.5",
            "area": "1.0",
            "thickness": "0.05",
            "delta_t": "80",
        },
    )
    assert r5.status_code == 200

    # 6. Simulação de Variação de Temperatura
    r6 = client.post(
        "/thermolab/simulation",
        data={
            "material_id": str(mat.id),
            "temp_start": "400",
            "temp_end": "25",
            "steps": "15",
            "mass": "2.0",
            "length": "1.0",
            "area": "0.5",
            "thickness": "0.02",
            "h_conv": "30",
            "sim_time_max": "500",
        },
    )
    assert r6.status_code == 200

    assert ThermalCalculation.query.count() == 6


def test_reports_pdf_and_csv_exports(client):
    """Verifica exportação do relatório PDF (ReportLab) e CSVs (Pandas)."""
    # Cria ao menos um registro de cálculo para o relatório
    client.post(
        "/thermolab/calculations",
        data={
            "calc_type": "calor_sensivel",
            "mass": "4",
            "specific_heat": "500",
            "temp_initial": "20",
            "temp_final": "90",
        },
    )

    rep_page = client.get("/thermolab/reports")
    assert rep_page.status_code == 200

    pdf_resp = client.get("/thermolab/reports/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.mimetype == "application/pdf"
    assert pdf_resp.data[:4] == b"%PDF"

    mat_csv = client.get("/thermolab/reports/materials.csv")
    assert mat_csv.status_code == 200
    assert "Aço Carbono AISI 1020" in mat_csv.get_data(as_text=True)

    calc_csv = client.get("/thermolab/reports/calculations.csv")
    assert calc_csv.status_code == 200
    assert "calor_sensivel" in calc_csv.get_data(as_text=True)

    clear_resp = client.post("/thermolab/calculations/clear", follow_redirects=True)
    assert clear_resp.status_code == 200
    assert ThermalCalculation.query.count() == 0
