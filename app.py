import streamlit as st
import pandas as pd
import numpy as np

from optimizer import WaterBlendOptimizer

# ======================================================
# OPERACIONES UNITARIAS (eficiencias aparentes)
# ======================================================
UNIT_OPERATIONS = {
    "Sin pretratamiento": {"As": 0.00, "Cl": 0.00},
    "Intercambio iónico": {"As": 0.90, "Cl": 0.20},
    "Adsorción": {"As": 0.80, "Cl": 0.50},
    "Electrocoagulación": {"As": 0.90, "Cl": 0.20},
    "Biodegradación": {"As": 0.40, "Cl": 0.10},
    "Precipitación química": {"As": 0.90, "Cl": 0.80},
    "Deionización capacitiva (CDI)": {"As": 0.80, "Cl": 0.60},
}

# ======================================================
# CONFIGURACIÓN DE PÁGINA
# ======================================================
st.set_page_config(
    page_title="Optimización del mezclado de agua",
    layout="wide"
)

# ======================================================
# FLOWSHEET (SEGURO)
# ======================================================
try:
    st.image(
        "flowsheet.jpg",
        caption="Diagrama conceptual del proceso (estilo Aspen / DWSIM)",
        use_container_width=True
    )
except Exception:
    st.warning("⚠️ No se pudo cargar la imagen del flowsheet")

# ======================================================
# ESTILOS CSS
# ======================================================
st.markdown(
    """
    <style>

    /* ===== TABLAS ===== */
    .dataframe tbody tr td {
        font-size: 26px !important;
        font-weight: bold;
        text-align: center;
    }

    .dataframe thead th {
        font-size: 24px !important;
        font-weight: bold;
        background-color: #e6f4ec;
        text-align: center;
    }

    /* ===== MÉTRICAS PERSONALIZADAS ===== */
    .metric-ok {
        background-color: #e8f7ee;
        border: 3px solid #3cb371;
        padding: 25px;
        border-radius: 22px;
    }

    .metric-bad {
        background-color: #fdecea;
        border: 3px solid #e74c3c;
        padding: 25px;
        border-radius: 22px;
    }

    .metric-label {
        font-size: 26px;
        font-weight: bold;
    }

    .metric-value {
        font-size: 56px;
        font-weight: bold;
    }

    .ok-text {
        color: #0a7d3b;
    }

    .bad-text {
        color: #c0392b;
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
    "<b>Control de arsénico y cloruros mediante optimización matemática y gemelos digitales</b>",
    unsafe_allow_html=True
)

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.header("⚙️ Parámetros del Modelo")

w_Cl = st.sidebar.slider(
    "Peso Cloruros",
    0.0, 1.0, 0.7, 0.05,
    help="Prioridad de minimización de cloruros"
)

w_As = 1.0 - w_Cl
st.sidebar.markdown(f"**Peso Arsénico:** 🔒 **{w_As:.2f}**")

Demand = st.sidebar.number_input(
    "Demanda total (LPS)",
    0.0, 150.0, 50.0, 1.0
)

st.sidebar.subheader("🧪 Operación unitaria")
unit_op = st.sidebar.selectbox(
    "Operación entre pozos y RO:",
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
        # MEZCLA ÓPTIMA
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
                <div class="metric-ok">
                    <div class="metric-label ok-text">Arsénico mezcla (mg/L)</div>
                    <div class="metric-value ok-text">{As_f:.5f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col2:
            st.markdown(
                f"""
                <div class="metric-ok">
                    <div class="metric-label ok-text">Cloruros mezcla (mg/L)</div>
                    <div class="metric-value ok-text">{Cl_f:.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        # ---------------------------
        # CAUDALES ÓPTIMOS
        # ---------------------------
        st.subheader("💧 Caudales óptimos por pozo")

        df_Q = pd.DataFrame.from_dict(Q_opt, orient="index", columns=["Caudal (LPS)"])
        df_Q = df_Q[df_Q["Caudal (LPS)"] > 1e-3]
        st.dataframe(df_Q, use_container_width=True)

        # ======================================================
        # OPERACIÓN UNITARIA
        # ======================================================
        eff = UNIT_OPERATIONS[unit_op]
        As_after_unit = As_f * (1 - eff["As"])
        Cl_after_unit = Cl_f * (1 - eff["Cl"])

        # ======================================================
        # ÓSMOSIS INVERSA
        # ======================================================
        RO_REJECTION = {"As": 0.90, "Cl": 0.80}
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
        # MÉTRICAS FINALES (DINÁMICAS)
        # ======================================================
        st.subheader("✅ Calidad del agua producto")

        col1, col2 = st.columns(2)

        # ---- Arsénico ----
        as_ok = As_product <= 0.025
        as_class = "metric-ok" if as_ok else "metric-bad"
        as_text = "ok-text" if as_ok else "bad-text"

        with col1:
            st.markdown(
                f"""
                <div class="{as_class}">
                    <div class="metric-label {as_text}">
                        Arsénico producto (mg/L)
                    </div>
                    <div class="metric-value {as_text}">
                        {As_product:.5f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.success("Cumple NOM") if as_ok else st.error("No cumple NOM")

        # ---- Cloruros ----
        cl_ok = Cl_product <= 35
        cl_class = "metric-ok" if cl_ok else "metric-bad"
        cl_text = "ok-text" if cl_ok else "bad-text"

        with col2:
            st.markdown(
                f"""
                <div class="{cl_class}">
                    <div class="metric-label {cl_text}">
                        Cloruros producto (mg/L)
                    </div>
                    <div class="metric-value {cl_text}">
                        {Cl_product:.2f}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            st.success("Cumple estándar") if cl_ok else st.error("No cumple estándar")

    except Exception as e:
        st.error(f"❌ Error en la optimización: {e}")
