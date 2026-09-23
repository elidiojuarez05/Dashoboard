"""Utilidades pequeñas de interfaz compartidas por las vistas Streamlit."""

import textwrap
from html import escape

import streamlit as st


def ui_escape(valor):
    """Convierte un valor a texto seguro para interpolarlo en HTML."""
    return escape("" if valor is None else str(valor))


def render_html(contenido):
    """Renderiza HTML usando st.html cuando está disponible."""
    contenido = textwrap.dedent(str(contenido)).strip()
    if hasattr(st, "html"):
        st.html(contenido)
    else:
        st.markdown(contenido, unsafe_allow_html=True)
