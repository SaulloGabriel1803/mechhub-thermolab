# MechHub — Módulo 04: `ThermoLab` (Análise Térmica)

**Curso:** Engenharia Mecânica  
**Disciplina:** Linguagem de Programação (Python)  
**Dupla 3:** Saullo Gabriel Fonseca Souza e Otávio Silva Melo  

---

## 1. Visão Geral e Arquitetura Modular

O **ThermoLab (Módulo 04)** faz parte da plataforma SaaS **MechHub**, projetado como um **Flask Blueprint desacoplado** (`modules/thermolab`) para que possa ser acoplado diretamente ao monólito modular principal que o professor disponibilizará, ao mesmo tempo em que já inclui um host local (`app.py`) para execução, testes e demonstração imediatos.

> **Nota sobre nomenclatura:** No Python, pacotes importáveis não podem iniciar com dígito (`04_thermolab`). Por isso o pacote reside em `modules/thermolab/` (correspondente ao módulo `04_thermolab` da especificação), sendo importado via `from modules.thermolab import thermolab_bp, init_thermolab_db`.

### Estrutura do Projeto

```text
MechHub/
├── app.py                          # Host local Flask (redireciona / para /thermolab/)
├── config.py                       # Configurações SQLite e Flask
├── extensions.py                   # Instância compartilhada SQLAlchemy (db)
├── requirements.txt                # Dependências do projeto
├── pytest.ini                      # Configuração do Pytest
├── README.md                       # Documentação e guia de defesa
├── modules/
│   ├── __init__.py
│   └── thermolab/                  # Módulo 04: ThermoLab (Blueprint Flask)
│       ├── __init__.py             # Exporta thermolab_bp e init_thermolab_db
│       ├── models.py               # Tabelas ThermalMaterial e ThermalCalculation
│       ├── calculator.py           # Motor de cálculos térmicos (NumPy e Pandas)
│       ├── charts.py               # Gráficos interativos (Plotly) e PNG para PDF (Matplotlib)
│       ├── reports.py              # Relatório PDF (ReportLab) e CSV (Pandas)
│       ├── seed.py                 # 8 materiais reais de Engenharia Mecânica pré-cadastrados
│       ├── routes.py               # Rotas Web e API JSON (/thermolab/*)
│       ├── templates/thermolab/    # Telas Bootstrap 5
│       └── static/thermolab/       # CSS industrial customizado
└── tests/
    ├── test_calculator.py          # Testes unitários dos algoritmos físicos
    └── test_routes_and_db.py       # Testes de integração Flask, SQLite, PDF e CSV
```

---

## 2. Como Rodar Localmente e Executar os Testes

### Instalação das dependências
```powershell
cd "c:\Users\saull\OneDrive\Área de Trabalho\Faculdade\2° Semestre\Linguagem de Programação\MechHub"
python -m pip install -r requirements.txt
```

### Executar o servidor web local
```powershell
python app.py
```
Acesse no navegador: `http://127.0.0.1:5000` (redireciona automaticamente para `/thermolab/`).

### Executar os testes automatizados (Pytest)
```powershell
python -m pytest -v
```

---

## 3. As 8 Funcionalidades Implementadas e Fórmulas Físicas

1. **Cadastrar Materiais (`/thermolab/materials`):**
   - CRUD completo (`ThermalMaterial`) com nome, categoria, calor específico $c$ ($\text{J/kg}\cdot\text{K}$), coeficiente de dilatação linear $\alpha$ ($\text{K}^{-1}$), condutividade térmica $k$ ($\text{W/m}\cdot\text{K}$), densidade $\rho$ ($\text{kg/m}^3$) e temperatura máxima $T_{\max}$ ($^\circ\text{C}$).
   - Calcula automaticamente a difusividade térmica $\alpha_{\text{dif}} = \frac{k}{\rho \cdot c}$.

2. **Calcular Calor Sensível (`/thermolab/calculations?tab=calor_sensivel`):**
   - $$Q = m \cdot c \cdot (T_f - T_i)$$
   - Conversões automáticas para $\text{J}$, $\text{kJ}$, $\text{kcal}$ e $\text{kWh}$, além de potência térmica média $\dot{Q} = |Q| / \Delta t$ ($\text{W}$ e $\text{kW}$) quando o tempo é informado.

3. **Calcular Dilatação Térmica (`/thermolab/calculations?tab=dilatacao`):**
   - $$\Delta X = X_0 \cdot \alpha_{\text{ef}} \cdot (T_f - T_i)$$
   - Suporta dilatação **Linear (1D)** ($\alpha_{\text{ef}} = \alpha$), **Superficial (2D)** ($\alpha_{\text{ef}} = 2\alpha$) e **Volumétrica (3D)** ($\alpha_{\text{ef}} = 3\alpha$). Emite alerta estrutural caso $T_f > T_{\max}$.

4. **Calcular Condução Térmica (`/thermolab/calculations?tab=conducao`):**
   - **Parede Plana (Lei de Fourier):** $\dot{Q} = \frac{k \cdot A \cdot (T_1 - T_2)}{L}$ e fluxo $q'' = \dot{Q} / A$.
   - **Cilindro Vazado / Tubulação:** $\dot{Q} = \frac{2\pi \cdot k \cdot L \cdot (T_1 - T_2)}{\ln(r_2 / r_1)}$.

5. **Calcular Resistência Térmica (`/thermolab/calculations?tab=resistencia`):**
   - Associação em série de múltiplas camadas condutivas ($R_i = \frac{L_i}{k_i \cdot A}$) e resistências convectivas interna/externa ($R_{\text{conv}} = \frac{1}{h \cdot A}$).
   - Calcula $R_{\text{eq}}$, coeficiente global $U = \frac{1}{R_{\text{eq}} \cdot A}$, fluxo $\dot{Q}$, participação percentual de cada camada e temperaturas exatas em cada interface com NumPy.

6. **Comparar Materiais (`/thermolab/comparison`):**
   - Utiliza `pandas.DataFrame` para comparar múltiplos materiais sob condições idênticas de massa, geometria e $\Delta T$, destacando automaticamente o melhor condutor, o melhor isolante, o de maior estabilidade dimensional e o de maior capacidade térmica volumétrica.

7. **Simular Variações de Temperatura (`/thermolab/simulation`):**
   - **Simulação Paramétrica:** Avalia vetorialmente $Q(T)$, $\Delta L(T)$ e $\dot{Q}_{\text{cond}}(T)$ ao longo de uma faixa de temperaturas usando `numpy.linspace`.
   - **Simulação Transiente (Capacitância Global / Lei de Newton):**
     $$T(t) = T_{\text{amb}} + (T_0 - T_{\text{amb}}) e^{-t / \tau}, \quad \tau = \frac{m \cdot c}{h \cdot A}, \quad \text{Bi} = \frac{h \cdot L_c}{k}$$

8. **Gerar Gráficos e Relatórios (`/thermolab/reports`):**
   - Gráficos interativos via **Plotly** em todas as telas de análise.
   - Exportação de **Relatório Técnico em PDF** com **ReportLab** + gráfico estático em PNG gerado com **Matplotlib**, além de exportação de planilhas **CSV** com **Pandas**.

---

## 4. Como Integrar ao Repositório Central do Professor

Quando o professor disponibilizar o repositório oficial do `MechHub`:
1. Copie a pasta `modules/thermolab/` para dentro de `modules/` (ou `04_thermolab` conforme padrão do professor).
2. Garanta que `modules/thermolab/models.py` e `modules/thermolab/__init__.py` importem a instância compartilhada `db` do projeto central (atualmente `from extensions import db`).
3. No `app.py` central, registre o Blueprint:
   ```python
   from modules.thermolab import thermolab_bp, init_thermolab_db
   app.register_blueprint(thermolab_bp)
   init_thermolab_db(app)
   ```

---

## 5. Guia Rápido de Defesa do Código (Para Apresentação)

- **Por que usar Blueprint?** Permite que cada equipe desenvolva seu módulo (rotas, modelos, templates e estáticos) isoladamente sem conflitos, integrando tudo em um único servidor Flask.
- **Onde entram NumPy e Pandas?** O `NumPy` gera curvas vetoriais (`np.linspace`, `np.exp`, `np.log`, `np.cumsum` nas interfaces térmicas) sem laços `for` lentos; o `Pandas` estrutura matrizes comparativas, estatísticas (`idxmax`, `idxmin`, `mean`) e exportação CSV.
- **Como funciona a persistência?** Os materiais ficam em `thermolab_materials` e cada cálculo/simulação é serializado em JSON dentro de `thermolab_calculations` via SQLAlchemy + SQLite.
- **Como funciona o tratamento de erros?** Todas as funções de `calculator.py` validam parâmetros físicos estritamente positivos ($m, c, k, \alpha, \rho, L, A > 0$ e $r_2 > r_1$) e lançam `ValueError`, que as rotas Flask capturam para exibir alertas amigáveis na interface sem derrubar o servidor.

---

## 6. Deploy Online (Render Free `*.onrender.com` + Domínio `.com` Próprio)

Este repositório já inclui `Procfile`, `render.yaml` e `gunicorn` em `requirements.txt` prontos para publicação no **Render**:

1. Acesse [render.com](https://render.com) e entre com sua conta do **GitHub**.
2. Clique em **New + → Blueprint** (ou **Web Service**) e selecione o repositório `SaulloGabriel1803/mechhub-thermolab`.
3. O Render lerá automaticamente o arquivo `render.yaml` (Python 3.12, `pip install -r requirements.txt` e `gunicorn app:app`).
4. Em poucos minutos seu SaaS estará no ar em uma URL pública gratuita `https://mechhub-thermolab.onrender.com`.
5. **Para usar um domínio `.com` próprio (opcional):** após registrar seu domínio (ex.: no Cloudflare Registrar ou Namecheap), acesse no painel do Render **Settings → Custom Domains → Add Custom Domain** e configure os registros DNS (`CNAME`/`A`) indicados pelo Render.
