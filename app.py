# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from optimizer import WaterBlendOptimizer

# -----------------------------------------
st.set_page_config(
    page_title="Water Blending Optimizer",
    layout="wide"
)

st.markdown(
    "<h1 style='color:#0a7d3b;'>💧 Water Blending Optimizer</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<b>Optimización del mezclado de agua para control de arsénico y cloruros</b>",
    unsafe_allow_html=True
)

# -----------------------------------------
# SIDEBAR
# -----------------------------------------
st.sidebar.header("⚙️ Parámetros del Modelo")

w_As = st.sidebar.slider("Peso Arsénico", 0.0, 1.0, 0.2)
w_Cl = st.sidebar.slider("Peso Cloruros", 0.0, 1.0, 0.8)

Demand = st.sidebar.number_input(
    "Demanda (LPS)", min_value=1.0, max_value=200.0, value=50.0
)

# -----------------------------------------
# DATOS DE POZOS
# -----------------------------------------
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

# -----------------------------------------
# OPTIMIZACIÓN
# -----------------------------------------
if st.button("🚀 Ejecutar Optimización"):

    try:
        opt = WaterBlendOptimizer(
            df_edit,
            w_As=w_As,
            w_Cl=w_Cl
        )

        Q_opt, As_f, Cl_f = opt.optimize(Demand)

        st.success("Optimización completada correctamente")

        # ---------------------------
        st.subheader("📈 Resultados")

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Arsénico final (mg/L)", f"{As_f:.5f}")

        with col2:
            st.metric("Cloruros finales (mg/L)", f"{Cl_f:.2f}")

        # ---------------------------
        st.subheader("💧 Caudales Óptimos")

        df_Q = pd.DataFrame.from_dict(
            Q_opt, orient="index", columns=["Caudal (LPS)"]
        )

        df_Q = df_Q[df_Q["Caudal (LPS)"] > 1e-3]
        st.dataframe(df_Q, use_container_width=True)

        # ---------------------------
        st.subheader("📉 Sensibilidad con la Demanda")

        Ds = np.arange(10, int(df_edit["Qmax"].sum()), 2)
        As_list, Cl_list = [], []

        for d in Ds:
            try:
                _, A, C = opt.optimize(d)
                As_list.append(A)
                Cl_list.append(C)
            except:
                pass

        fig, ax1 = plt.subplots(figsize=(8,4))
        ax2 = ax1.twinx()

        ax1.plot(Ds[:len(As_list)], As_list, label="As", linewidth=2)
        ax2.plot(Ds[:len(Cl_list)], Cl_list, "r--", label="Cl", linewidth=2)

        ax1.set_xlabel("Demanda (LPS)")
        ax1.set_ylabel("Arsénico (mg/L)")
        ax2.set_ylabel("Cloruros (mg/L)")

        fig.tight_layout()
        st.pyplot(fig)

    except Exception as e:
        st.error(str(e))
