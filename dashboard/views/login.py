"""Vista de acceso y encabezado principal del dashboard."""
import base64
import os
import time
import streamlit as st


def render_login(cookies, check_password):
    """Renderiza el formulario de acceso y detiene la app mientras no haya sesión."""
    if st.session_state.get("authenticated", False):
        return

    st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at 30% 30%, #1b263b 0%, #0b132b 60%, #000814 100%) !important;
    }
    .stApp::before {
        content: ""; position: fixed; width: 400px; height: 400px;
        background: rgba(65, 90, 119, 0.2); filter: blur(120px);
        top: 20%; left: 10%; z-index: 0;
    }
    section.main > div { animation: fadeIn 0.8s ease-in-out; }
    @keyframes fadeIn { from {opacity: 0; transform: translateY(30px);} to {opacity: 1; transform: translateY(0);} }
    h1 { animation: glowText 2s ease-in-out infinite alternate; }
    @keyframes glowText { from { text-shadow: 0 0 5px rgba(119,141,169,0.3); } to { text-shadow: 0 0 20px rgba(119,141,169,0.8); } }
    div[data-testid="stTextInput"] input, div[data-testid="stPasswordInput"] input {
        background-color: transparent !important; border: none !important;
        border-bottom: 2px solid #415a77 !important; color: #ffffff !important;
        border-radius: 0px !important; transition: all 0.3s ease !important;
    }
    div[data-testid="stTextInput"] input:focus, div[data-testid="stPasswordInput"] input:focus {
        border-bottom: 2px solid #00b4d8 !important; box-shadow: 0 5px 15px rgba(0,180,216,0.2);
    }
    div[data-testid="stFormSubmitButton"] { display: flex !important; justify-content: center !important; margin-top: 2rem !important; }
    div[data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(90deg, #415a77, #1b263b) !important; border: 1px solid #778da9 !important;
        width: 220px !important; height: 45px !important; border-radius: 10px !important;
        color: white !important; font-weight: 700 !important; font-size: 0.9rem !important;
        letter-spacing: 1px !important; box-shadow: 0 5px 20px rgba(0,0,0,0.4); transition: all 0.25s ease !important;
    }
    div[data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-2px) scale(1.12); box-shadow: 0 10px 25px rgba(0,180,216,0.4), inset 0 0 15px rgba(255,255,255,0.1);
        border: 1px solid #00b4d8 !important;
    }
    div[data-testid="stFormSubmitButton"] > button:active { transform: scale(0.95); }
    label { color: #a8dadc !important; font-size: 0.85rem !important; letter-spacing: 1px; }
    header, footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

    _, central_col, _ = st.columns([1, 1.5, 1])
    with central_col:
        st.markdown("<h1 style='text-align: center; color: white; margin-top: 80px; font-weight: 800;'>🔐ACCESO</h1>", unsafe_allow_html=True)
        with st.form("login_form", clear_on_submit=False):
            user_input = st.text_input("Usuario", placeholder="Ingresa tu usuario", key="u_field")
            pass_input = st.text_input("Contraseña", type="password", placeholder="Ingresa tu contraseña", key="p_field")
            btn_entrar = st.form_submit_button("ENTRAR")
            if btn_entrar:
                if user_input and pass_input:
                    user = check_password(user_input, pass_input)
                    if user:
                        st.session_state.update({
                            "authenticated": True,
                            "user_role": user.role.strip().lower(),
                            "username": user.username,
                        })
                        cookies["authenticated"] = "true"
                        cookies["username"] = user.username
                        cookies["role"] = user.role
                        cookies.save()
                        st.success("Acceso concedido")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Credenciales incorrectas")
                else:
                    st.warning("Complete los campos")
    st.stop()


def render_header(current_dir):
    """Renderiza el encabezado principal conservando el diseño existente."""
    posibles_rutas = [
        os.path.join(os.getcwd(), "assets", "logo.png"),
        os.path.join(current_dir, "assets", "logo.png"),
        os.path.join(os.path.dirname(current_dir), "assets", "logo.png"),
    ]
    ruta_logo = next((r for r in posibles_rutas if os.path.exists(r)), None)

    if ruta_logo:
        with open(ruta_logo, "rb") as f:
            bin_str = base64.b64encode(f.read()).decode()
        st.markdown(f"""
            <div style="display: flex; align-items: center; gap: 15px; margin-bottom: 10px;">
                <img src="data:image/png;base64,{bin_str}" width="100" style="object-fit: contain;">
                <h1 style="font-size: 35px; color: #FFFFFF; margin: 0; font-family: sans-serif; font-weight: 700;">
                    Panorama Estatus de impresoras 🖨️
                </h1>
            </div>
        """, unsafe_allow_html=True)
    else:
        print(f"DEBUG: Logo no encontrado. Intenté en: {posibles_rutas}")
        st.title("Panorama Estatus de impresoras 🖨️")
