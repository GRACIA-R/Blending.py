# app/main.py
import streamlit as st
from ui import render_ui

# --------------------------------------------------
# Configuración general de la app
# --------------------------------------------------
st.set_page_config(
    page_title="Water Blending Optimizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# Arranque
# --------------------------------------------------
def main():
    st.title("💧 Water Blending Optimizer")
    st.markdown(
        """
        **Optimización de mezcla de caudales de pozos**  
        Minimización de impacto por **arsénico y cloruros** bajo restricciones
        de disponibilidad y demanda.
        """
    )

    render_ui()


if __name__ == "__main__":
    main()
