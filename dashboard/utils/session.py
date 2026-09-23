"""Gestión centralizada del estado de sesión y cookies de la aplicación."""

import streamlit as st
from streamlit_cookies_manager_ext import EncryptedCookieManager


def inicializar_sesion(machine_configs):
    """Crea el administrador de cookies y prepara las claves de session_state."""
    cookies = EncryptedCookieManager(password=st.secrets["cookie_password"])

    if not cookies.ready():
        st.spinner("Cargando entorno seguro...")
        st.stop()

    defaults = {
        "authenticated": False,
        "user_role": None,
        "username": None,
        "machine_selected": next(iter(machine_configs), None),
        "estados_maquinas": {name: "Operativa" for name in machine_configs.keys()},
        "indice_carrusel": 0,
        "mapa_actual": None,
        "img_resultado": None,
        "recortes": {},
        "bloquear_refresco": False,
        "archivo_pdf_listo": None,
        "archivo_csv_listo": None,
        "mostrar_descargas": False,
        "odp_para_asignar": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Mantener el comportamiento existente: una cookie válida restaura
    # la sesión después de una recarga o interrupción de conexión.
    if cookies.get("authenticated") == "true":
        st.session_state.authenticated = True
        st.session_state.username = cookies.get("username")
        raw_role = cookies.get("role")
        st.session_state.user_role = str(raw_role).strip().lower() if raw_role else None

    return cookies


def reiniciar_modo_interaccion():
    """Reactiva el monitoreo automático desde el botón del sidebar."""
    st.session_state.bloquear_refresco = False
    st.session_state.editando_manual = False
    st.session_state.mostrar_descargas = False
    st.rerun()
