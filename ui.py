# app/ui.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from pulp import (
    LpProblem, LpVariable, LpMinimize,
    lpSum, PULP_CBC_CMD
)


# ==================================================
# DICCIONARIO DE OPERACIONES UNITARIAS
# ==================================================
# --- Eficiencias aparentes por operación unitaria ---
UNIT_OPERATIONS = {
    "Sin pretratamiento": {"As": 0.00, "Cl": 0.00},
    "Adsorción":       {"As": 0.70, "Cl": 0.10},
    "Intercambio iónico": {"As": 0.90, "Cl": 0.30},
    "Precipitación química": {"As": 0.98, "Cl": 0.95},
    "Biodegradación":  {"As": 0.15, "Cl": 0.05},
    "Deionización capacitiva": {"As": 0.50, "Cl": 0.60},
    "Electrocoagulación": {"As": 0.50, "Cl": 0.60},
}

# ==================================================
# OPTIMIZADOR DE BLENDING
# ==================================================
def optimize_blending(df, demand, w_as=0.2, w_cl=0.8,
                      As_ref=0.025, Cl_ref=35):

    df = df.copy()

    # Score tipo Aspen-like
    df["score"] = (
        w_as * (df["As"] / As_ref) +
        w_cl * (df["Cl"] / Cl_ref)
    ) / (df["avail"] + 1e-6)

    Qmax_available = (df["Qmax"] * df["avail"]).sum()
    if demand > Qmax_available:
        raise ValueError("La demanda supera la capacidad disponible")

    prob = LpProblem("WaterBlending", LpMinimize)

    Q = {
        p: LpVariable(
            f"Q_{p}",
            lowBound=0,
            upBound=df.loc[p, "Qmax"] * df.loc[p, "avail"]
        )
        for p in df.index
    }

    # Objetivo
    prob += lpSum(Q[p] * df.loc[p, "score"] for p in df.index)

    # Restricción de demanda
    prob += lpSum(Q[p] for p in df.index) == demand

    prob.solve(PULP_CBC_CMD(msg=False))

    Q_opt = {p: Q[p].value() for p in df.index}

    Qt = sum(Q_opt.values())
    As_final = sum(Q_opt[p] * df.loc[p, "As"] for p in df.index) / Qt
    Cl_final = sum(Q_opt[p] * df.loc[p, "Cl"] for p in df.index) / Qt

    return Q_opt, As_final, Cl_final


# ==================================================
# INTERFAZ
# ==================================================
def render_ui():

    st.subheader("🧩 Flowsheet del proceso")

    st.image(
        "main/flowsheet.png",
        caption="Esquema conceptual del sistema de tratamiento",
        use_container_width=True
    )

    
    # ---------------------------
    # Datos base
    # ---------------------------
    data = {
        "Pozo": ["Pozo 1", "Pozo 2", "Pozo 3", "Pozo 4", "Pozo 5"],
        "Qmax": [10, 50, 25, 50, 15],
        "As": [0.004, 0.037, 0.0453, 0.0273, 0.0331],
        "Cl": [272.3, 250.28, 226.25, 320.35, 188.21],
        "avail": [1, 1, 1, 1, 1]
    }

    df = pd.DataFrame(data).set_index("Pozo")

    # ---------------------------
    # SIDEBAR – Inputs
    # ---------------------------
    st.sidebar.header("⚙️ Configuración")

    demand = st.sidebar.number_input(
        "Demanda total (L/s)",
        min_value=1.0,
        max_value=200.0,
        value=50.0,
        step=1.0
    )

    st.sidebar.subheader("Disponibilidad de pozos")

    for p in df.index:
        df.loc[p, "avail"] = st.sidebar.checkbox(
            p, value=True
        )

    # ---------------------------
    # Tabla editable
    # ---------------------------
    st.subheader("📋 Datos de los pozos")

    edited_df = st.data_editor(
        df,
        use_container_width=True,
        num_rows="fixed"
    )

    # ---------------------------
    # Optimización
    # ---------------------------
    if st.button("🚀 Ejecutar optimización"):

        try:
            Q_opt, As_f, Cl_f = optimize_blending(
                edited_df, demand
            )

            # -----------------------
            # Resultados numéricos
            # -----------------------
            st.success("Optimización exitosa")

            col1, col2, col3 = st.columns(3)
            col1.metric("Arsénico final", f"{As_f:.5f} mg/L")
            col2.metric("Cloruros finales", f"{Cl_f:.2f} mg/L")
            col3.metric("Demanda", f"{demand:.1f} L/s")

            # -----------------------
            # Tabla de caudales
            # -----------------------
            st.subheader("📊 Caudales óptimos")

            result_df = pd.DataFrame.from_dict(
                Q_opt, orient="index", columns=["Q óptimo (L/s)"]
            )

            st.dataframe(result_df, use_container_width=True)

            # -----------------------
            # Gráfica tipo Aspen
            # -----------------------
            st.subheader("📈 Tendencia de concentraciones")

            Ds = np.arange(10, int(edited_df["Qmax"].sum()), 2)
            As_list, Cl_list = [], []

            for d in Ds:
                try:
                    _, A, C = optimize_blending(edited_df, d)
                    As_list.append(A)
                    Cl_list.append(C)
                except:
                    pass

            fig, ax1 = plt.subplots()
            ax2 = ax1.twinx()

            ax1.plot(Ds[:len(As_list)], As_list, label="As")
            ax2.plot(Ds[:len(Cl_list)], Cl_list, "r--", label="Cl")

            ax1.set_xlabel("Demanda (L/s)")
            ax1.set_ylabel("Arsénico (mg/L)")
            ax2.set_ylabel("Cloruros (mg/L)")

            fig.tight_layout()
            st.pyplot(fig)

        except Exception as e:
            st.error(str(e))
