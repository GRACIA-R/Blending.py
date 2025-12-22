import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from optimizer import WaterBlendOptimizer

# ======================================================
# OPERACIONES UNITARIAS (eficiencias aparentes)
# ======================================================
UNIT_OPERATIONS = {
    "Sin pretratamiento": {"As": 0.00, "Cl": 0.00},
    "Intercambio iónico": {"As": 0.85, "Cl": 0.10},
    "Adsorción": {"As": 0.70, "Cl": 0.05},
    "Electrocoagulación": {"As": 0.90, "Cl": 0.15},
    "Biodegradación": {"As": 0.10, "Cl": 0.00},
    "Precipitación química": {"As": 0.95, "Cl": 0.05},
    "Deionización capacitiva (CDI)": {"As": 0.75, "Cl": 0.05},
}

# ======================================================
# CONFIGURACIÓN DE PÁGINA
# ======================================================
st.set_page_config(
    page_title="Optimización del mezclado de agua",
    layout="wide"
)

# ======================================================
# FLOWSHEET
# ======================================================
st.image(
    "flowsheet.jpg",
    caption="Diagrama del proceso",
    use_container_width=True
)

# ======================================================
# ESTILOS CSS
# ======================================================
st.markdown(
    """
    <style>
    div[data-testid="metric-container"] {
        background-color: #f4fdf8;
        border: 3px solid #b6e2c8;
        padding: 25px;
        border-radius: 22px;
    }

    div[data-testid="metric-container"] > label {
        font-size: 24px !important;
        font-weight: bold;
    }

    div[data-testid="metric-container"] > div {
        font-size: 42px !important;
        font-weight: bold;
        color: #0a7d3b;
    }

    .dataframe tbody tr td {
        font-size: 28px;
        font-weight: bold;
    }

    .dataframe thead th {
        font-size: 28px;
        background-color: #e6f4ec;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ======================================================
# TÍTULO
# ======================================================
st.markdown(
    "<h1 style='color:#0a7d3b;'>💧 Optimización del mezclado de agua</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<b>Control de arsénico y cloruros mediante optimización matemática</b>",
    unsafe_allow_html=True
)

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.header("⚙️ Parámetros del Modelo")

w_Cl = st.sidebar.slider(
    "Peso Cloruros",
    min_value=0.0,
    max_value=1.0,
    value=0.7,
    step=0.05,
    help="Define la importancia de minimizar cloruros en la mezcla en comparación con el arsénico"
)

w_As = 1.0 - w_Cl

st.sidebar.markdown(f"**Peso Arsénico:** 🔒 **{w_As:.2f}**")

Demand = st.sidebar.number_input(
    "Demanda total (LPS)",
    min_value=0.0,
    max_value=150.0,
    value=50.0,
    step=1.0,
    help="Es la demanda de agua que se desea bombear desde los pozos"
)

st.sidebar.subheader("🧪 Operación unitaria")

unit_op = st.sidebar.selectbox(
    "Seleccione la operación entre pozos y RO:",
    list(UNIT_OPERATIONS.keys())
)

# ======================================================
# DATOS DE POZOS
# ======================================================
st.subheader("📊 Datos de los Pozos")

df = pd.DataFrame({
    "Pozo": ["Pozo 1", "Pozo 2", "Pozo 3", "Pozo 4", "Pozo 5"],
    "Qmax": [10, 50, 25, 50, 15],
    "As": [0.004, 0.037, 0.0453, 0.0273, 0.0331],
    "Cl": [272.3, 250.28, 226.25, 320.35, 188.21],
    "Disponible": [True, True, True, True, True]
}).set_index("Pozo")

df_edit = st.data_editor(df, use_container_width=True)
df_edit["avail"] = df_edit["Disponible"].astype(int)
df_edit = df_edit.drop(columns="Disponible")

# ======================================================
# OPTIMIZACIÓN
# ======================================================
if st.button("🚀 Ejecutar Optimización"):

    try:
        # ---------------------------
        # OPTIMIZACIÓN
        # ---------------------------
        opt = WaterBlendOptimizer(df_edit, w_As=w_As, w_Cl=w_Cl)
        Q_opt, As_f, Cl_f = opt.optimize(Demand)

        st.success("Optimización completada correctamente")

        # ---------------------------
        # RESULTADOS MEZCLA
        # ---------------------------
        st.subheader("📈 Resultados de la mezcla")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown(
                f"""
                <div>
                    <div class="big-metric-label">Arsénico mezcla (mg/L)</div>
                    <div class="big-metric-value">{As_f:.5f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )            

        with col2:
            st.markdown(
                f"""
                <div>
                    <div class="big-metric-label">Cloruros mezcla (mg/L)</div>
                    <div class="big-metric-value">{Cl_f:.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        # ---------------------------
        # CAUDALES ÓPTIMOS
        # ---------------------------
        st.subheader("💧 Caudales óptimos por pozo")

        df_Q = pd.DataFrame.from_dict(
            Q_opt, orient="index", columns=["Caudal (LPS)"]
        )
        df_Q = df_Q[df_Q["Caudal (LPS)"] > 1e-3]
        st.dataframe(df_Q, use_container_width=True)

        # ======================================================
        # OPERACIÓN UNITARIA
        # ======================================================
        eff = UNIT_OPERATIONS[unit_op]

        As_after_unit = As_f * (1 - eff["As"])
        Cl_after_unit = Cl_f * (1 - eff["Cl"])

        # ======================================================
        # OSMOSIS INVERSA (modelo simple)
        # ======================================================
        RO_REJECTION = {"As": 0.95, "Cl": 0.95}

        As_product = As_after_unit * (1 - RO_REJECTION["As"])
        Cl_product = Cl_after_unit * (1 - RO_REJECTION["Cl"])

        # ======================================================
        # RESULTADOS POR ETAPA
        # ======================================================
        st.subheader("🧪 Concentraciones por etapa")

        df_stages = pd.DataFrame({
            "Etapa": ["Mezcla de pozos", unit_op, "Ósmosis inversa"],
            "Arsénico (mg/L)": [As_f, As_after_unit, As_product],
            "Cloruros (mg/L)": [Cl_f, Cl_after_unit, Cl_product]
        })

        st.dataframe(df_stages, use_container_width=True)

        # ======================================================
        # MÉTRICAS FINALES
        # ======================================================
        st.subheader("✅ Calidad del agua producto")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Arsénico producto (mg/L)", f"{As_product:.5f}")
            st.success("Cumple NOM" if As_product <= 0.025 else "No cumple NOM")

        with col2:
            st.metric("Cloruros producto (mg/L)", f"{Cl_product:.2f}")
            st.success("Cumple estándar" if Cl_product <= 35 else "No cumple estándar")

    except Exception as e:
        st.error(f"Error en la optimización: {e}")
