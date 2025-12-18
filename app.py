import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from optimizer import WaterBlendOptimizer

# ======================================================
# CONFIGURACIÓN DE PÁGINA
# ======================================================
st.set_page_config(
    page_title="Optimización del mezclado de agua",
    layout="wide"
)

# ======================================================
# ESTILOS CSS (RESULTADOS GRANDES Y CLAROS)
# ======================================================
st.markdown(
    """
    <style>
    /* ===== MÉTRICAS MUY GRANDES ===== */
    div[data-testid="metric-container"] {
        background-color: #f4fdf8;
        border: 2px solid #b6e2c8;
        padding: 25px;
        border-radius: 12px;
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

    /* ===== TABLAS GRANDES ===== */
    .dataframe tbody tr td {
        font-size: 20px;
        font-weight: bold;
    }

    .dataframe thead th {
        font-size: 18px;
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
    "<b>Optimización del mezclado de agua para control de arsénico y cloruros</b>",
    unsafe_allow_html=True
)

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.header("⚙️ Parámetros del Modelo")

w_As = st.sidebar.slider(
    "Peso Arsénico",
    0.0, 1.0, 0.3,
    help="Mayor valor → mayor prioridad a reducir arsénico"
)

w_Cl = st.sidebar.slider(
    "Peso Cloruros",
    0.0, 1.0, 0.7,
    help="Mayor valor → mayor prioridad a reducir cloruros"
)

Demand = st.sidebar.number_input(
    "Demanda (LPS)",
    min_value=0.0,
    max_value=150.0,
    value=50.0,
    step=1.0,
    help="Caudal total requerido del sistema"
)

# ------------------------------------------------------
# DESCRIPCIÓN DEL MODELO (SIDEBAR)
# ------------------------------------------------------
st.sidebar.markdown(
    """
    ---
    ### 🧠 ¿Cómo funciona el modelo?

    El modelo determina la **combinación óptima de caudales**
    de los pozos disponibles para cumplir la **demanda total**
    minimizando la concentración final de contaminantes.

    **⚖️ Pesos del modelo**
    - **Peso Arsénico:** prioriza reducir As.
    - **Peso Cloruros:** prioriza reducir Cl.
    > Subir un peso puede aumentar el otro contaminante.

    **💧 Demanda**
    - Rango operativo: **0 – 150 LPS**
    - Demandas altas pueden forzar el uso de pozos de peor calidad.

    **📏 Límites normativos**
    - Arsénico: **0.025 mg/L**
    - Cloruros: **35 mg/L**
    """
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

df_edit = st.data_editor(
    df,
    use_container_width=True,
    num_rows="fixed"
)

df_edit["avail"] = df_edit["Disponible"].astype(int)
df_edit = df_edit.drop(columns="Disponible")

# ======================================================
# OPTIMIZACIÓN
# ======================================================
if st.button("🚀 Ejecutar Optimización"):

    try:
        opt = WaterBlendOptimizer(
            df_edit,
            w_As=w_As,
            w_Cl=w_Cl
        )

        Q_opt, As_f, Cl_f = opt.optimize(Demand)

        st.success("Optimización completada correctamente")

        # --------------------------------------------------
        # RESULTADOS (MUY GRANDES)
        # --------------------------------------------------
        st.subheader("📈 Resultados")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Arsénico final (mg/L)", f"{As_f:.5f}")
            if As_f > 0.025:
                st.error("⚠️ Supera límite normativo (0.025 mg/L)")
            else:
                st.success("✅ Cumple norma")

        with col2:
            st.metric("Cloruros finales (mg/L)", f"{Cl_f:.2f}")
            if Cl_f > 35:
                st.error("⚠️ Supera límite normativo (35 mg/L)")
            else:
                st.success("✅ Cumple norma")

        # --------------------------------------------------
        # CAUDALES ÓPTIMOS
        # --------------------------------------------------
        st.markdown(
            "<h2 style='color:#0a7d3b;'>💧 Caudales Óptimos (LPS)</h2>",
            unsafe_allow_html=True
        )

        df_Q = pd.DataFrame.from_dict(
            Q_opt, orient="index", columns=["Caudal (LPS)"]
        )

        df_Q = df_Q[df_Q["Caudal (LPS)"] > 1e-3]
        st.dataframe(df_Q, use_container_width=True)

        # --------------------------------------------------
        # SENSIBILIDAD CON DEMANDA
        # --------------------------------------------------
        st.subheader("📉 Sensibilidad con la Demanda")

        Ds = np.arange(5, int(df_edit["Qmax"].sum()), 2)
        As_list, Cl_list = [], []

        for d in Ds:
            try:
                _, A, C = opt.optimize(d)
                As_list.append(A)
                Cl_list.append(C)
            except:
                pass

        fig, ax1 = plt.subplots(figsize=(9, 4))
        ax2 = ax1.twinx()

        ax1.plot(Ds[:len(As_list)], As_list, linewidth=2)
        ax2.plot(Ds[:len(Cl_list)], Cl_list, "r--", linewidth=2)

        # Límites normativos
        ax1.axhline(0.025, color="red", linestyle=":", linewidth=2)
        ax2.axhline(35, color="darkred", linestyle=":", linewidth=2)

        ax1.set_xlabel("Demanda (LPS)")
        ax1.set_ylabel("Arsénico (mg/L)")
        ax2.set_ylabel("Cloruros (mg/L)")

        fig.tight_layout()
        st.pyplot(fig)

    except Exception as e:
        st.error(str(e))
