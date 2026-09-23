# =========================================================
# 1. IMPORTACIONES Y DEPENDENCIAS
# =========================================================
# Librería estándar
import os
import sys
import textwrap
import time
import json
import base64
import io
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, time as dt_time

# Dependencias de terceros
import numpy as np
import cv2
import pandas as pd
import pytz
from PIL import Image
from html import escape
import streamlit as st
from streamlit_cropper import st_cropper
from sqlalchemy import text
from streamlit_cookies_manager_ext import EncryptedCookieManager

# =========================================================
# 2. ZONA HORARIA OFICIAL DE PRODUCCIÓN
# =========================================================
# Las columnas de producción son TIMESTAMP WITHOUT TIME ZONE.
# Por eso todos los sellos operativos se generan explícitamente
# en hora central de México (America/Mexico_City).
# Expresión SQL para columnas TIMESTAMP WITHOUT TIME ZONE almacenadas en hora local.







# =========================================================
# 3. CONFIGURACIÓN DE PÁGINA Y RUTAS (PRIMER COMANDO STREAMLIT)
# =========================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
ruta_al_logo = os.path.join(current_dir, "assets", "logo_empresa.png")

st.set_page_config(
    page_title="Estatus-Máquinas Just in Time Printing", 
    page_icon=ruta_al_logo,
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

backend_path = os.path.join(BASE_DIR, "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# =========================================================
# 4. IMPORTACIONES LOCALES
# =========================================================
MACHINE_CONFIGS = {}

# Tipos de corte disponibles para routers. Se conserva como catálogo
# global de compatibilidad para la UI y las configuraciones de máquina.
TIPOS_CORTE = ["BROCA", "NAVAJA", "CORTE 45", "PLECA", "CORTE COMPLETO STICKER"]
try:
    from backend.crud import generate_pdf_report
    from backend.image_processor import process_smart_grid
    from backend.image_processor import process_test_image_v2
    from backend.config import MACHINE_CONFIGS
    from dashboard.services.production_service import (
        _config_produccion_maquina,
        calcular_area_produccion,
        calcular_tiempo_corte,
        calcular_tiempo_produccion,
        etiqueta_area_rigida,
        estimar_produccion,
        opciones_pasadas_para_maquina,
    )
except ImportError as e:
    st.error(f"Error crítico de importación: {e}")
    st.info("Revisa que en GitHub el archivo sea 'backend/config.py' y exista 'backend/__init__.py'")
    st.stop()

from dashboard.views.estatus import render_estatus
from dashboard.views.produccion import render_produccion
from dashboard.views.analisis import render_analisis
from dashboard.views.bitacoras import render_bitacora
from dashboard.views.registro_odp import render_registro_odp
from dashboard.views.historial_odp import render_historial_odp
from dashboard.views.operacion_odp import render_operacion_odp
from dashboard.views.sidebar import render_sidebar
from dashboard.views.login import render_login, render_header
try:
    from dashboard.views.gestion import render_gestion
except ModuleNotFoundError as e:
    if e.name == "dashboard.views.gestion":
        from views.gestion import render_gestion
    else:
        raise
from dashboard.utils.dates import ZONA_HORARIA_MEXICO, SQL_AHORA_MEXICO, ahora_mexico, ahora_mexico_texto
from dashboard.components.priority import PRIORIDADES_ODP, normalizar_prioridad_odp, etiqueta_prioridad_odp, prioridad_es_critica
from dashboard.utils.formatting import formatear_duracion
from dashboard.services.report_service import generar_pdf_reporte_maquinas
from dashboard.services.odp_service import ODPService
from dashboard.services.odp_query_service import ODPQueryService
from dashboard.services.auth_service import AuthService
from dashboard.services.export_service import dataframe_to_xlsx_bytes
from dashboard.services.pdf_service import generar_pdf_odps_finalizadas
from dashboard.services.machine_status_service import MachineStatusService
from dashboard.services.machine_service import (
    _norm_nombre_estacion,
    maquina_compatible_material,
    maquinas_impresion_compatibles,
    routers_compatibles,
)

# =========================================================
# 5. ESTILO VISUAL INDUSTRIAL GLOBAL
# =========================================================
st.markdown("""
    <style>
        /* Registro ODP — controles equilibrados */
        [data-testid="stHorizontalBlock"] .stButton > button {
            min-height: 42px;
            border-radius: 8px !important;
            font-weight: 700 !important;
            letter-spacing: .2px;
        }
        div[data-testid="stNumberInput"] input,
        div[data-testid="stTextInput"] input {
            border-radius: 7px !important;
        }
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            border-radius: 7px !important;
        }
        div[data-testid="stRadio"] > div {
            gap: 8px;
        }
        /* Color de los Tabs (Pestañas) */
        .stTabs [data-baseweb="tab-list"] {
            background-color: #1b263b;
            border-radius: 10px 10px 0 0;
            padding: 5px;
        }
        /* Color de las tarjetas de máquinas */
        div[data-testid="stMetricValue"] {
            background-color: #1b263b;
            border-radius: 10px;
            padding: 10px;
            border: 1px solid #415a77;
        }
        /* Texto de los headers */
        h1, h2, h3 {
            color: #778da9 !important;
        }
        /* Sidebar con tono más oscuro */
        [data-testid="stSidebar"] {
            background-color: #0b132b;
        }
        /* ASIGNACION ODP - diseño premium */
        .assign-hero { background: linear-gradient(135deg,#111827 0%,#172554 55%,#0f172a 100%); border:1px solid #334155; border-radius:16px; padding:20px 22px; margin:6px 0 16px; box-shadow:0 8px 28px rgba(0,0,0,.20); }
        .assign-kicker { font-size:11px; font-weight:800; letter-spacing:1.3px; color:#93c5fd; text-transform:uppercase; margin-bottom:5px; }
        .assign-title { font-size:25px; line-height:1.15; font-weight:800; color:#f8fafc; margin:0; }
        .assign-subtitle { margin-top:7px; color:#94a3b8; font-size:13px; }
        .time-summary { background:linear-gradient(135deg,#0f2742,#132f4c); border:1px solid #24527a; border-radius:14px; padding:15px 18px; margin:14px 0 16px; }
        .time-summary-label { color:#93c5fd; font-size:11px; font-weight:800; letter-spacing:.8px; text-transform:uppercase; margin-bottom:5px; }
        .time-summary-main { color:#f8fafc; font-size:23px; font-weight:800; }
        .time-summary-detail { color:#cbd5e1; font-size:13px; margin-top:3px; }
        .odp-active-id { color:#f8fafc; font-size:17px; font-weight:800; }
        .odp-active-meta { color:#94a3b8; font-size:12px; margin-top:3px; }
        .odp-active-state { display:inline-block; padding:4px 9px; border-radius:999px; background:#172554; border:1px solid #1d4ed8; color:#bfdbfe; font-size:11px; font-weight:800; }
        .route-note { color:#64748b; font-size:11px; margin-top:3px; }
        .station-time { display:inline-flex; align-items:center; gap:6px; padding:5px 9px; border-radius:8px; background:#0b1625; border:1px solid #26384d; color:#dbeafe; font-weight:800; }
        .process-time { color:#93c5fd; font-size:12px; font-weight:800; }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# 6. INICIALIZACIÓN DE SESSION STATE Y COOKIES
# =========================================================
cookies = EncryptedCookieManager(password=st.secrets["cookie_password"])

if not cookies.ready():
    st.spinner("Cargando entorno seguro...")
    st.stop()

if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'user_role' not in st.session_state: st.session_state.user_role = None
if 'username' not in st.session_state: st.session_state.username = None
if 'machine_selected' not in st.session_state: st.session_state.machine_selected = list(MACHINE_CONFIGS.keys())[0]

if 'estados_maquinas' not in st.session_state: st.session_state.estados_maquinas = {name: "Operativa" for name in MACHINE_CONFIGS.keys()}
if 'indice_carrusel' not in st.session_state: st.session_state.indice_carrusel = 0

if 'mapa_actual' not in st.session_state: st.session_state.mapa_actual = None
if 'img_resultado' not in st.session_state: st.session_state.img_resultado = None
if 'recortes' not in st.session_state: st.session_state.recortes = {}

if 'bloquear_refresco' not in st.session_state: st.session_state.bloquear_refresco = False

if "archivo_pdf_listo" not in st.session_state: st.session_state.archivo_pdf_listo = None
if "archivo_csv_listo" not in st.session_state: st.session_state.archivo_csv_listo = None
if "mostrar_descargas" not in st.session_state: st.session_state.mostrar_descargas = False

# Estado de sesión específico para flujo de asignación
if 'odp_para_asignar' not in st.session_state:
    st.session_state.odp_para_asignar = None # o False, dependiendo de qué tipo de dato esperas


run_camera = False

# Recuperar sesión desde cookies
if cookies.get("authenticated") == "true":
    st.session_state.authenticated = True
    st.session_state.username = cookies.get("username")
    raw_role = cookies.get("role")
    st.session_state.user_role = str(raw_role).strip().lower() if raw_role else None

# =========================================================
# 7. CONEXIÓN Y LÓGICA DE BASE DE DATOS
# =========================================================
conn = st.connection("postgresql", type="sql")

from dashboard.services.database_service import DatabaseService

_db_service = DatabaseService(conn=conn, machine_configs=MACHINE_CONFIGS)

_auth_service = AuthService(query_db=lambda sql, params=None: _db_service.query_db(sql, params))

_status_service = MachineStatusService(
    query_db=lambda sql, params=None: _db_service.query_db(sql, params),
    commit_db=lambda sql, params=None: _db_service.commit_db(sql, params),
    machine_configs=MACHINE_CONFIGS,
    ahora_mexico=ahora_mexico,
)

@st.cache_data(ttl=10, show_spinner=False)
def query_db(sql_string, params=None):
    return _db_service.query_db(sql_string, params)

def commit_db(sql_string, params=None):
    ok = _db_service.commit_db(sql_string, params)
    if not ok and _db_service.last_error and "already exists" not in _db_service.last_error:
        st.error(f"Error de base de datos: {_db_service.last_error}")
    return ok

def inicializar_base_de_datos():
    return _db_service.inicializar_base_de_datos()


def estado_con_icono(estado):
    return _status_service.estado_con_icono(estado)

def obtener_maquinas_operativas():
    return _status_service.obtener_maquinas_operativas()

def obtener_nombres_maquinas_operativas():
    return _status_service.obtener_nombres_maquinas_operativas()

def obtener_maquinas_impresion():
    return _status_service.obtener_maquinas_impresion()

def obtener_maquinas_router():
    return _status_service.obtener_maquinas_router()

def _numero_seguro(valor, default=0.0):
    return _status_service.numero_seguro(valor, default)

def save_test_result(machine_name, health_score, missing_nodes, health_map, evidence_path):
    return _status_service.save_test_result(machine_name, health_score, missing_nodes, health_map, evidence_path)

def render_machine_card(m_name, fecha_consulta, suffix=""):
    return _status_service.render_machine_card(m_name, fecha_consulta, suffix)

def generar_svg_slot_falla(color="#fd7e14"):
    return _status_service.generar_svg_slot_falla(color)

def obtener_ultimo_estado(nombre_maquina):
    return _db_service.obtener_ultimo_estado(nombre_maquina)


    








def es_maquina_router(nombre_maquina):
    config = MACHINE_CONFIGS.get(nombre_maquina, {})
    if isinstance(config, dict) and str(config.get("type", "")).lower() == "manual":
        return True
    return "router" in str(nombre_maquina).lower()


_odp_query_service = ODPQueryService(
    query_db=lambda sql, params=None: _db_service.query_db(sql, params),
    es_maquina_router=es_maquina_router,
    normalizar_prioridad_odp=normalizar_prioridad_odp,
)

def obtener_odps_en_proceso(maquina=None):
    return _odp_query_service.obtener_odps_en_proceso(maquina)

def obtener_odps_finalizadas(maquina=None, fecha_inicio=None, fecha_fin=None):
    return _odp_query_service.obtener_odps_finalizadas(maquina, fecha_inicio, fecha_fin)

def obtener_registro_odps_finalizadas(maquina=None, fecha_inicio=None, fecha_fin=None):
    return _odp_query_service.obtener_registro_odps_finalizadas(maquina, fecha_inicio, fecha_fin)


def check_password(username, password):
    return _auth_service.check_password(username, password)






# =========================================================
# 9. ACCESO Y ENCABEZADO PRINCIPAL
# =========================================================
render_login(cookies, check_password)
render_header(current_dir)

fecha_consulta = render_sidebar(
    machine_configs=MACHINE_CONFIGS,
    query_db=query_db,
    commit_db=commit_db,
    ahora_mexico=ahora_mexico,
    cookies=cookies,
)

st.divider()
hora_ajustada = ahora_mexico() 
fecha_mostrar = hora_ajustada.strftime('%d/%m/%Y')
es_hoy = (fecha_consulta == hora_ajustada.date())

if es_hoy:
    st.subheader(f"📊 Monitoreo en Tiempo Real ({fecha_mostrar})")
else:
    st.subheader(f"📰 Historial de Planta: {fecha_consulta.strftime('%d/%m/%Y')}")

tab_carrusel, tab_planta, tab_registro, tab_analisis, tab_bitacora, tab_gestion = st.tabs([
    "🔄 Render Estatus", "🏬 Render Producción","✍️Resgistro odp´s ","🔍 Análisis de Test","📙 Bitacoras", "⚙️ Gestión Administrador"
])

lista_maquinas = list(MACHINE_CONFIGS.keys())

interactuando = (
    st.session_state.get("bloquear_refresco", False) or 
    run_camera or 
    st.session_state.get("mostrar_descargas", False) or
    st.session_state.get("editando_manual", False)
)

if interactuando:
    st.sidebar.warning("⏸️ Monitoreo en pausa (Modo de edición activo)")
    if st.sidebar.button("▶️ Reanudar Monitoreo Auto"):
        st.session_state.bloquear_refresco = False
        st.session_state.editando_manual = False
        st.session_state.mostrar_descargas = False
        st.rerun()

# ============================================================
# TAB ESTATUS — delegación al módulo de vista
# ============================================================
render_estatus(
    tab_carrusel,
    fecha_consulta=fecha_consulta,
    interactuando=interactuando,
    lista_maquinas=lista_maquinas,
    render_machine_card=render_machine_card,
)

# ============================================================
# TAB PLANTA — CONTROL VISUAL DE PRODUCCIÓN
# ============================================================

with tab_planta:
    if "planta_maquina_index" not in st.session_state:
        st.session_state.planta_maquina_index = 0
    if "odp_para_asignar" not in st.session_state:
        st.session_state.odp_para_asignar = None

    def planta_escape(valor):
        return escape("" if valor is None else str(valor))

    def planta_html(contenido):
        contenido = textwrap.dedent(str(contenido)).strip()
        if hasattr(st, "html"):
            st.html(contenido)
        else:
            st.markdown(contenido, unsafe_allow_html=True)

    # Estética Industrial Avanzada (Dark Industrial / Control Room UI)
    planta_html("""
    <style>
    :root {
        --ind-bg: #0b0f19;
        --ind-surface: #111827;
        --ind-surface-alt: #1f2937;
        --ind-border: #334155;
        --ind-border-glow: #38bdf8;
        --ind-text: #f8fafc;
        --ind-muted: #94a3b8;
        --ind-accent: #0284c7;
        --ind-success: #059669;
        --ind-warning: #d97706;
    }
    .planta-hero {
        background: linear-gradient(135deg, #090d16 0%, #111c33 50%, #1e1b4b 100%);
        border: 1px solid var(--ind-border);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        border-left: 5px solid #0ea5e9;
    }
    .planta-hero h1 { margin: 0; color: var(--ind-text); font-size: 26px; font-weight: 800; letter-spacing: 0.5px; }
    .planta-hero p { margin: 6px 0 0; color: var(--ind-muted); font-size: 13px; font-family: monospace; }
    
    .planta-section { font-size: 18px; font-weight: 800; color: var(--ind-text); margin: 16px 0 4px; display: flex; align-items: center; gap: 8px; }
    .planta-sub { font-size: 11px; color: var(--ind-muted); margin-bottom: 10px; font-family: monospace; text-transform: uppercase; letter-spacing: 0.8px; }
    .odp-process-panel { background: linear-gradient(145deg, rgba(15,23,42,.98), rgba(17,24,39,.96)); border:1px solid #334155; border-left:4px solid #10b981; border-radius:14px; padding:10px; margin:8px 0 14px; box-shadow:0 10px 28px rgba(0,0,0,.25); }
    .odp-process-title { display:flex; align-items:center; justify-content:space-between; gap:12px; color:#f8fafc; font:800 15px/1.2 system-ui,sans-serif; padding:4px 6px 10px; }
    .odp-process-badge { display:inline-flex; align-items:center; gap:5px; border-radius:999px; padding:4px 9px; background:rgba(16,185,129,.12); color:#6ee7b7; border:1px solid rgba(16,185,129,.35); font:700 10px monospace; }

    .machine-card {
        background: linear-gradient(150deg, #0f172a 0%, #111827 100%);
        border: 1px solid var(--ind-border);
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 6px 18px rgba(0,0,0,0.3);
        min-height: 380px;
        transition: border-color 0.2s ease;
    }
    .machine-card:hover { border-color: #475569; }
    .machine-head {
        padding: 14px 16px;
        background: rgba(15, 23, 42, 0.7);
        border-bottom: 1px solid var(--ind-border);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .machine-name { color: var(--ind-text); font-size: 18px; font-weight: 750; font-family: monospace; }
    .machine-type { color: var(--ind-muted); font-size: 9px; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 2px; }
    .machine-pill {
        background: rgba(6, 78, 59, 0.6);
        color: #34d399;
        border: 1px solid #059669;
        border-radius: 6px;
        padding: 4px 8px;
        font-size: 9px;
        font-weight: 700;
        font-family: monospace;
        letter-spacing: 0.5px;
    }
    .machine-body { padding: 12px 14px; }
    .machine-count { color: var(--ind-muted); font-size: 10px; margin-bottom: 8px; font-family: monospace; text-transform: uppercase; }

    .order-card {
        background: #090d16;
        border: 1px solid var(--ind-border);
        border-left: 3px solid #0ea5e9;
        border-radius: 8px;
        padding: 10px 12px;
        margin: 8px 0;
    }
    .order-card.router { border-left-color: #8b5cf6; }
    .order-top { display: flex; justify-content: space-between; gap: 8px; align-items: center; }
    .order-odp { color: var(--ind-text); font-size: 14px; font-weight: 800; font-family: monospace; }
    .order-state {
        font-size: 8px;
        font-weight: 800;
        border-radius: 4px;
        padding: 3px 6px;
        background: #0369a1;
        color: #e0f2fe;
        font-family: monospace;
        letter-spacing: 0.5px;
    }
    .order-state.router { background: #5b21b6; color: #ede9fe; }
    .order-client { color: #cbd5e1; font-size: 11px; margin-top: 4px; }
    .order-meta { color: var(--ind-muted); font-size: 9px; margin-top: 4px; font-family: monospace; }

    .machine-empty { text-align: center; padding: 44px 15px; color: var(--ind-muted); }
    .machine-empty strong { display: block; color: var(--ind-text); font-size: 13px; margin-top: 6px; font-family: monospace; }
    
    .carousel-indicator {
        text-align: center;
        color: var(--ind-muted);
        font-size: 11px;
        font-weight: 600;
        font-family: monospace;
        padding: 8px;
        background: rgba(15, 23, 42, 0.4);
        border-radius: 6px;
        margin-top: 8px;
        border: 1px dashed var(--ind-border);
    }

    .planta-screen-wrap {
        position: relative;
        height: 100px;
        border-radius: 10px;
        overflow: hidden;
        margin: 0 0 12px;
        border: 1px solid var(--ind-border);
        background: #020617;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .planta-screen-video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.25; }
    .planta-screen-overlay { position: absolute; inset: 0; background: linear-gradient(90deg, rgba(2,6,23,0.9), rgba(2,6,23,0.4), rgba(2,6,23,0.9)); }
    .planta-screen-title { position: relative; z-index: 2; color: var(--ind-text); font-size: 20px; font-weight: 900; letter-spacing: 1px; font-family: monospace; text-align: center; }
    .planta-screen-card { min-height: 410px; }
    </style>
    """)

    maquinas_impresion = obtener_maquinas_impresion()
    maquinas_router = obtener_maquinas_router()
    todas_maquinas = list(MACHINE_CONFIGS.keys())
    maquinas_operativas = obtener_nombres_maquinas_operativas()

with tab_planta:
    render_produccion(
        machine_configs=MACHINE_CONFIGS,
        current_dir=current_dir,
        query_db=query_db,
        obtener_nombres_maquinas_operativas=obtener_nombres_maquinas_operativas,
        es_maquina_router=es_maquina_router,
        normalizar_prioridad_odp=normalizar_prioridad_odp,
        etiqueta_prioridad_odp=etiqueta_prioridad_odp,
        prioridad_es_critica=prioridad_es_critica,
        formatear_duracion=formatear_duracion,
        numero_seguro=_numero_seguro,
    )

    # DIAGNÓSTICO — FUERA DEL RENDER OPERATIVO
    # ============================================================
    # FALLA / MANTENIMIENTO — 2 POR FILA
    # ============================================================
    problemas=[]
    for m in todas_maquinas:
        d=query_db("SELECT estado FROM estados_maquinas WHERE machine_name=:m",{"m":m})
        est=str(d.iloc[0]["estado"]) if not d.empty else "Operativa"
        if est.strip().lower() != "operativa": problemas.append((m,est))
    with st.expander(f"⚠️ MÁQUINAS CON FALLA Y/O MANTENIMIENTO ({len(problemas)})",expanded=False):
        if not problemas: 
            st.success("🟢 Todos los equipos se encuentran operativos y sin reportes críticos.")
        else:
            for inicio in range(0,len(problemas),2):
                cols=st.columns(2,gap="large")
                for j,(m,est) in enumerate(problemas[inicio:inicio+2]):
                    with cols[j]:
                        planta_html(f'<div class="machine-card"><div class="machine-head"><div><div class="machine-name">⚠️ {planta_escape(m)}</div><div class="machine-type">{"ROUTER" if es_maquina_router(m) else "IMPRESIÓN"}</div></div><div class="machine-pill" style="background:#7f1d1d;color:#fca5a5;border-color:#991b1b;">⚠️ {planta_escape(est).upper()}</div></div><div class="machine-body"><div class="machine-empty"><div style="font-size:32px">🛠️</div><strong>ESTACIÓN BLOQUEADA</strong><div>Inspeccionar bitácora de mantenimiento o falla mecánica.</div></div></div></div>')

    # ============================================================
    # REGISTRAR + ASIGNAR EN UN SOLO PASO
    # ============================================================



# ============================================================
# CÁLCULO DE MATERIAL Y ÁREA (CORREGIDO)
# ============================================================
ANCHO_LAMINA_RIGIDA_M = 1.22
LARGO_LAMINA_RIGIDA_M = 2.44
M2_POR_LAMINA_RIGIDA = ANCHO_LAMINA_RIGIDA_M * LARGO_LAMINA_RIGIDA_M





# Servicio de negocio ODP: las dependencias se conectan aquí para conservar
# las mismas funciones públicas que utilizaba la UI antes de la Fase 9.
_odp_service = ODPService(
    query_db=query_db,
    commit_db=commit_db,
    ahora_mexico=ahora_mexico,
    estimar_produccion=estimar_produccion,
    normalizar_prioridad_odp=normalizar_prioridad_odp,
    etiqueta_prioridad_odp=etiqueta_prioridad_odp,
    formatear_duracion=formatear_duracion,
    numero_seguro=_numero_seguro,
    norm_nombre_estacion=_norm_nombre_estacion,
    maquina_compatible_material=maquina_compatible_material,
)

# Alias de compatibilidad: la UI sigue trabajando con los mismos nombres.
_sincronizar_estado_maestro_odp = _odp_service._sincronizar_estado_maestro_odp
actualizar_estado_asignacion = _odp_service.actualizar_estado_asignacion
eliminar_asignacion = _odp_service.eliminar_asignacion
editar_asignacion_produccion = _odp_service.editar_asignacion_produccion
asignar_odp = _odp_service.asignar_odp
registrar_odp = _odp_service.registrar_odp


with tab_registro:
    render_registro_odp(
        LARGO_LAMINA_RIGIDA_M=LARGO_LAMINA_RIGIDA_M,
        PRIORIDADES_ODP=PRIORIDADES_ODP,
        TIPOS_CORTE=TIPOS_CORTE,
        _config_produccion_maquina=_config_produccion_maquina,
        _numero_seguro=_numero_seguro,
        asignar_odp=asignar_odp,
        calcular_area_produccion=calcular_area_produccion,
        estimar_produccion=estimar_produccion,
        etiqueta_prioridad_odp=etiqueta_prioridad_odp,
        formatear_duracion=formatear_duracion,
        maquinas_impresion=maquinas_impresion,
        maquinas_impresion_compatibles=maquinas_impresion_compatibles,
        maquinas_router=maquinas_router,
        opciones_pasadas_para_maquina=opciones_pasadas_para_maquina,
        planta_html=planta_html,
        registrar_odp=registrar_odp,
        routers_compatibles=routers_compatibles,
    )

    render_operacion_odp(
        todas_maquinas=todas_maquinas,
        query_db=query_db,
        obtener_odps_en_proceso=obtener_odps_en_proceso,
        prioridad_es_critica=prioridad_es_critica,
        normalizar_prioridad_odp=normalizar_prioridad_odp,
        etiqueta_prioridad_odp=etiqueta_prioridad_odp,
        PRIORIDADES_ODP=PRIORIDADES_ODP,
        TIPOS_CORTE=TIPOS_CORTE,
        planta_html=planta_html,
        planta_escape=planta_escape,
        _numero_seguro=_numero_seguro,
        formatear_duracion=formatear_duracion,
        opciones_pasadas_para_maquina=opciones_pasadas_para_maquina,
        _config_produccion_maquina=_config_produccion_maquina,
        editar_asignacion_produccion=editar_asignacion_produccion,
        eliminar_asignacion=eliminar_asignacion,
        actualizar_estado_asignacion=actualizar_estado_asignacion,
        maquinas_impresion=maquinas_impresion,
        maquinas_router=maquinas_router,
        LARGO_LAMINA_RIGIDA_M=LARGO_LAMINA_RIGIDA_M,
        M2_POR_LAMINA_RIGIDA=M2_POR_LAMINA_RIGIDA,
        estimar_produccion=estimar_produccion,
        asignar_odp=asignar_odp,
    )


    render_historial_odp(
        todas_maquinas=todas_maquinas,
        obtener_registro_odps_finalizadas=obtener_registro_odps_finalizadas,
        dataframe_to_xlsx_bytes=dataframe_to_xlsx_bytes,
        generar_pdf_odps_finalizadas=generar_pdf_odps_finalizadas,
        ahora_mexico=ahora_mexico,
        formatear_duracion=formatear_duracion,
        numero_seguro=_numero_seguro,
    )

with tab_analisis:
    render_analisis(
        machine_configs=MACHINE_CONFIGS,
        process_smart_grid=process_smart_grid,
        commit_db=commit_db,
        ahora_mexico=ahora_mexico,
    )

with tab_bitacora:
    render_bitacora(
        machine_configs=MACHINE_CONFIGS,
        query_db=query_db,
        commit_db=commit_db,
        ahora_mexico=ahora_mexico,
    )

with tab_gestion:
    render_gestion(
        machine_configs=MACHINE_CONFIGS,
        query_db=query_db,
        commit_db=commit_db,
        ahora_mexico=ahora_mexico,
        ahora_mexico_texto=ahora_mexico_texto,
        sql_ahora_mexico=SQL_AHORA_MEXICO,
        generar_pdf_reporte_maquinas=generar_pdf_reporte_maquinas,
        formatear_duracion=formatear_duracion,
        numero_seguro=_numero_seguro,
    )
