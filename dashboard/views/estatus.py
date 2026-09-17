"""Vista Render Estatus. Extraída del dashboard sin cambiar su lógica."""

import base64
import streamlit as st


def render_estatus(tab, *, fecha_consulta, interactuando, lista_maquinas, render_machine_card):
    """Renderiza la vista de estatus usando las dependencias del controlador."""
    with tab:
        ruta_confirmada = "/mount/src/monitor-cabezales/dashboard/assets/video.mp4"
        def get_video_base64(path):
            try:
                with open(path, "rb") as f: data = f.read()
                return base64.b64encode(data).decode()
            except:
                return None
        
        video_b64 = get_video_base64(ruta_confirmada)
        if video_b64:
            st.markdown(f"""
                <style>
                #video-fondo-carrusel {{
                    position: fixed; right: 0; bottom: 0; min-width: 100%; min-height: 100%;
                    z-index: -1; opacity: 0.13; object-fit: cover; pointer-events: none;
                }}
                .stApp {{ background-color: rgba(0,0,0,0); }}
                </style>
                <video autoplay muted loop playsinline id="video-fondo-carrusel">
                    <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
                </video>
            """, unsafe_allow_html=True)
        
        @st.fragment(run_every="15s")
        def render_carrusel_vivo():
            if interactuando:
                st.info("⏸️ Carrusel en pausa para no interrumpir tu trabajo actual.")
                avanzar = False
            else:
                avanzar = True
            idx = st.session_state.indice_carrusel
            cols_car = st.columns(2)
            for i, m_name in enumerate(lista_maquinas[idx : idx + 2]):
                with cols_car[i]: 
                    render_machine_card(m_name, fecha_consulta, suffix=f"car_{idx}_{i}")
            if avanzar:
                st.session_state.indice_carrusel = (idx + 2) % len(lista_maquinas) if lista_maquinas else 0
        render_carrusel_vivo()

