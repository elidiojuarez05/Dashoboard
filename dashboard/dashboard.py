# =========================================================
# 1. IMPORTACIONES Y DEPENDENCIAS
# =========================================================
# Librería estándar
import os
import sys
import textwrap
import hashlib
import time
import tempfile
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
from fpdf import FPDF
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

@st.cache_resource(show_spinner=False)
def inicializar_base_de_datos():
    tablas = [
        """CREATE TABLE IF NOT EXISTS test_results (
            id SERIAL PRIMARY KEY,
            machine_name VARCHAR(100),
            health_score FLOAT,
            missing_nodes INTEGER,
            health_map TEXT,
            evidence_path TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password TEXT,
            role VARCHAR(20)
        );""",
        """CREATE TABLE IF NOT EXISTS estados_maquinas (
            machine_name VARCHAR(50) PRIMARY KEY,
            estado VARCHAR(50) NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""", # <-- ¡Aquí faltaba la coma!

        """CREATE TABLE IF NOT EXISTS bitacora_mantenimiento (
            id SERIAL PRIMARY KEY,
            machine_name VARCHAR(100) NOT NULL,
            tipo_mantenimiento VARCHAR(50) NOT NULL,
            piezas_cambiadas TEXT,
            notas TEXT,
            fecha_ejecucion DATE NOT NULL,
            proximo_mantenimiento DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        
        """CREATE TABLE IF NOT EXISTS odps (
            id SERIAL PRIMARY KEY,
            numero_odp VARCHAR(50) UNIQUE NOT NULL,
            cliente VARCHAR(150) NOT NULL,
            estado VARCHAR(30) NOT NULL DEFAULT 'PENDIENTE',
            maquina_asignada VARCHAR(100),
            fecha_asignacion TIMESTAMP,
            usuario_asignacion VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        
        """CREATE TABLE IF NOT EXISTS historial_odps (
            id SERIAL PRIMARY KEY,
            numero_odp VARCHAR(50) NOT NULL,
            cliente VARCHAR(150),
            estado_anterior VARCHAR(30),
            estado_nuevo VARCHAR(30),
            maquina_anterior VARCHAR(100),
            maquina_nueva VARCHAR(100),
            usuario VARCHAR(100),
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );""",
        """CREATE TABLE IF NOT EXISTS odp_asignaciones (
            id SERIAL PRIMARY KEY,
            odp_id INTEGER REFERENCES odps(id) ON DELETE CASCADE,
            numero_odp VARCHAR(50) NOT NULL,
            cliente VARCHAR(150),
            material VARCHAR(30) NOT NULL DEFAULT 'GENERAL',
            maquina_asignada VARCHAR(100),
            requiere_corte BOOLEAN NOT NULL DEFAULT FALSE,
            tipo_proceso VARCHAR(30) NOT NULL DEFAULT 'IMPRESION',
            cantidad_m2 FLOAT NOT NULL DEFAULT 0,
            cantidad_laminas INTEGER NOT NULL DEFAULT 0,
            pasadas INTEGER,
            tinta_blanca BOOLEAN NOT NULL DEFAULT FALSE,
            day_night BOOLEAN NOT NULL DEFAULT FALSE,
            tipo_corte VARCHAR(50),
            cantidad_cortes INTEGER NOT NULL DEFAULT 0,
            tiempo_produccion_min FLOAT NOT NULL DEFAULT 0,
            tiempo_corte_min FLOAT NOT NULL DEFAULT 0,
            tiempo_estimado_min FLOAT NOT NULL DEFAULT 0,
            fecha_estimada_finalizacion TIMESTAMP,
            estado VARCHAR(30) NOT NULL DEFAULT 'EN PROCESO',
            fecha_asignacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            usuario_asignacion VARCHAR(100),
            fecha_impresion TIMESTAMP,
            fecha_router TIMESTAMP,
            fecha_finalizacion TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );""",
        
        """CREATE TABLE IF NOT EXISTS historial_estados (
            id SERIAL PRIMARY KEY,
            machine_name VARCHAR(100) NOT NULL,
            estado VARCHAR(50) NOT NULL,
            fecha_inicio TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            fecha_fin TIMESTAMP,
            duracion_horas FLOAT
        );"""
        
    ]

    commit_db("ALTER TABLE bitacora_mantenimiento ADD COLUMN IF NOT EXISTS foto_tag TEXT;")

    for t in tablas:
        commit_db(t)

    commit_db("ALTER TABLE odp_asignaciones ADD COLUMN IF NOT EXISTS maquina_router VARCHAR(100);")
    commit_db("ALTER TABLE odps ADD COLUMN IF NOT EXISTS prioridad VARCHAR(20) NOT NULL DEFAULT 'NORMAL';")
    # Permitir ODPs que van directamente a Router sin pasar por impresión.
    commit_db("ALTER TABLE odp_asignaciones ALTER COLUMN maquina_asignada DROP NOT NULL;")
    # Campos de planeación de producción (compatibles con instalaciones existentes).
    for _col, _tipo in {
        "tipo_proceso": "VARCHAR(30) NOT NULL DEFAULT 'IMPRESION'",
        "cantidad_m2": "FLOAT NOT NULL DEFAULT 0",
        "cantidad_laminas": "INTEGER NOT NULL DEFAULT 0",
        "pasadas": "INTEGER",
        "tinta_blanca": "BOOLEAN NOT NULL DEFAULT FALSE",
        "day_night": "BOOLEAN NOT NULL DEFAULT FALSE",
        "tipo_corte": "VARCHAR(50)",
        "cantidad_cortes": "INTEGER NOT NULL DEFAULT 0",
        "tiempo_produccion_min": "FLOAT NOT NULL DEFAULT 0",
        "tiempo_corte_min": "FLOAT NOT NULL DEFAULT 0",
        "tiempo_estimado_min": "FLOAT NOT NULL DEFAULT 0",
        "fecha_estimada_finalizacion": "TIMESTAMP",
        "metros_lineales": "FLOAT NOT NULL DEFAULT 0",
        "ancho_material_m": "FLOAT NOT NULL DEFAULT 1.52",
        "cantidad_copias": "INTEGER NOT NULL DEFAULT 1",
        "modo_velocidad": "VARCHAR(20) NOT NULL DEFAULT 'MAXIMA'",
        "doble_saturacion": "BOOLEAN NOT NULL DEFAULT FALSE",
        "prioridad": "VARCHAR(20) NOT NULL DEFAULT 'NORMAL'"
    }.items():
        commit_db(f"ALTER TABLE odp_asignaciones ADD COLUMN IF NOT EXISTS {_col} {_tipo};")

    # Migración de estados de ODP de versiones anteriores.
    # ASIGNADO pasa a EN PROCESO porque ahora la asignación inicia directamente la producción.
    commit_db("""
        UPDATE odps
        SET estado = 'EN PROCESO', updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City')
        WHERE estado = 'ASIGNADO'
    """)

    # Crear una asignación histórica para ODPs existentes que ya tenían máquina.
    # Esto permite que la nueva arquitectura soporte varias máquinas por una misma ODP
    # sin perder los registros anteriores.
    commit_db("""
        INSERT INTO odp_asignaciones (
            odp_id, numero_odp, cliente, material, maquina_asignada,
            requiere_corte, estado, fecha_asignacion, usuario_asignacion,
            created_at, updated_at
        )
        SELECT
            o.id, o.numero_odp, o.cliente, 'GENERAL', o.maquina_asignada,
            FALSE, o.estado, COALESCE(o.fecha_asignacion, o.created_at),
            o.usuario_asignacion, o.created_at, o.updated_at
        FROM odps o
        WHERE o.maquina_asignada IS NOT NULL
          AND TRIM(o.maquina_asignada) <> ''
          AND NOT EXISTS (
              SELECT 1 FROM odp_asignaciones a
              WHERE a.odp_id = o.id
          );
    """)
    
    # Sincronizar automáticamente todas las máquinas de tu config
    for maq_nombre in MACHINE_CONFIGS.keys():
        commit_db("""
            INSERT INTO estados_maquinas (machine_name, estado) 
            VALUES (:m, 'Operativa') 
            ON CONFLICT (machine_name) DO NOTHING;
        """, {"m": maq_nombre})

    columnas = {
        "health_map": "TEXT",
        "missing_nodes": "INTEGER",
        "evidence_path": "TEXT",
        "comments": "TEXT"
    }
    for nombre_col, tipo_col in columnas.items():
        try:
            with conn.session as session:
                session.execute(text(f"ALTER TABLE test_results ADD COLUMN IF NOT EXISTS {nombre_col} {tipo_col};"))
                session.commit()
        except Exception as e: 
            print(f"Error en parche: {e}")
    # ------------------------------------------------------------
    # MIGRACIÓN ÚNICA: timestamps históricos UTC -> hora México
    # ------------------------------------------------------------
    # La versión anterior guardaba CURRENT_TIMESTAMP en columnas
    # TIMESTAMP WITHOUT TIME ZONE. Los registros existentes quedan
    # 6 horas adelantados respecto a la operación local.
    commit_db("""
        CREATE TABLE IF NOT EXISTS sistema_config (
            clave VARCHAR(100) PRIMARY KEY,
            valor TEXT,
            updated_at TIMESTAMP
        );
    """)

    migracion = query_db("""
        SELECT valor FROM sistema_config
        WHERE clave = 'timestamps_produccion_migrados_mexico_v1'
        LIMIT 1
    """)

    if migracion.empty:
        for tabla, columnas in {
            "odp_asignaciones": ["fecha_asignacion", "fecha_impresion", "fecha_router", "fecha_finalizacion"],
            "odps": ["fecha_asignacion"],
            "historial_odps": ["fecha"],
            "historial_estados": ["fecha_inicio", "fecha_fin"],
            "test_results": ["timestamp"]
        }.items():
            for columna in columnas:
                commit_db(f"""
                    UPDATE {tabla}
                    SET {columna} = {columna} - INTERVAL '6 hours'
                    WHERE {columna} IS NOT NULL;
                """)

        commit_db("""
            INSERT INTO sistema_config (clave, valor, updated_at)
            VALUES (
                'timestamps_produccion_migrados_mexico_v1',
                'UTC a America/Mexico_City; ejecutado una sola vez',
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (clave) DO NOTHING;
        """)

    return True

def obtener_ultimo_estado(nombre_maquina):
    sql = """
        SELECT health_score, timestamp, missing_nodes 
        FROM test_results 
        WHERE machine_name = :name 
        ORDER BY timestamp DESC LIMIT 1
    """
    df = query_db(sql, {"name": nombre_maquina})
    if not df.empty:
        return df.iloc[0]
    return None
    
@st.cache_data(ttl=10, show_spinner=False)
def query_db(sql_string, params=None):
    try:
        with conn.session as session:
            result = session.execute(text(sql_string), params or {})
            rows = result.fetchall()
            if not rows:
                return pd.DataFrame()
            df = pd.DataFrame(rows)
            df.columns = result.keys()
            df.columns = [c.lower() for c in df.columns]
            return df
    except Exception:
        return pd.DataFrame()

def commit_db(sql_string, params=None):
    try:
        with conn.session as session:
            session.execute(text(sql_string), params or {})
            session.commit()
        return True
    except Exception as e:
        if "already exists" not in str(e):
            st.error(f"Error de base de datos: {e}")
        return False

def estado_con_icono(estado):
    if not isinstance(estado, str): estado = str(estado)
    estado = estado.lower().strip()
    if "operativa" in estado: return "🟢 Operativa"
    elif "falla" in estado: return "🔴 Falla"
    elif "sin actividad" in estado: return "⚪ Sin actividad"
    else: return "⚪ Sin registro"


def obtener_maquinas_operativas():
    df = query_db("""
        SELECT machine_name, estado
        FROM estados_maquinas
        WHERE LOWER(TRIM(estado)) = 'operativa'
        ORDER BY machine_name
    """)
    return df


def obtener_nombres_maquinas_operativas():
    """Máquinas configuradas cuyo estado actual en BD es OPERATIVA."""
    df = obtener_maquinas_operativas()
    if df is None or df.empty:
        return []
    operativas_bd = {str(x).strip() for x in df["machine_name"].dropna().tolist()}
    return [m for m in MACHINE_CONFIGS.keys() if str(m).strip() in operativas_bd]


def es_maquina_router(nombre_maquina):
    config = MACHINE_CONFIGS.get(nombre_maquina, {})
    if isinstance(config, dict) and str(config.get("type", "")).lower() == "manual":
        return True
    return "router" in str(nombre_maquina).lower()

def obtener_maquinas_impresion():
    return [m for m in MACHINE_CONFIGS.keys() if not es_maquina_router(m)]

def obtener_maquinas_router():
    return [m for m in MACHINE_CONFIGS.keys() if es_maquina_router(m)]


def dataframe_to_xlsx_bytes(df):
    """Genera un XLSX básico sin depender de openpyxl/xlsxwriter."""
    buf = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", ns)
    def val(v):
        if v is None or pd.isna(v): return ""
        if isinstance(v, (pd.Timestamp, datetime)): return v.strftime("%d/%m/%Y %H:%M:%S")
        if isinstance(v, bool): return "Sí" if v else "No"
        return str(v)
    sheet = ET.Element(f"{{{ns}}}worksheet")
    data = ET.SubElement(sheet, f"{{{ns}}}sheetData")
    rows = [list(df.columns)] + df.astype(object).where(pd.notna(df), None).values.tolist()
    for ri, row in enumerate(rows, 1):
        er = ET.SubElement(data, f"{{{ns}}}row", {"r":str(ri)})
        for ci, value in enumerate(row, 1):
            n=ci; letters=""
            while n: n,rem=divmod(n-1,26); letters=chr(65+rem)+letters
            c=ET.SubElement(er, f"{{{ns}}}c", {"r":f"{letters}{ri}","t":"inlineStr"})
            isel=ET.SubElement(c, f"{{{ns}}}is")
            t=ET.SubElement(isel, f"{{{ns}}}t"); t.text=val(value)
    sheet_xml=ET.tostring(sheet, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>''')
        z.writestr("_rels/.rels", '''<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''')
        z.writestr("xl/workbook.xml", '''<?xml version="1.0"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="ODPs Acabadas" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        z.writestr("xl/_rels/workbook.xml.rels", '''<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>''')
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    return buf.getvalue()

def obtener_odps_en_proceso(maquina=None):

    params = {}

    filtro = ""

    if maquina and maquina != "Todas":

        params["maquina"] = maquina

        if es_maquina_router(maquina):

            filtro = """
                AND a.maquina_router = :maquina
                AND a.estado = 'EN ROUTER'
            """

        else:

            filtro = """
                AND a.maquina_asignada = :maquina
                AND a.estado = 'EN PROCESO'
            """

    return query_db(
        f"""
        SELECT
            a.id AS asignacion_id,
            a.numero_odp,
            a.cliente,
            a.material,
            a.estado,
            a.maquina_asignada,
            a.maquina_router,
            a.requiere_corte,
            a.tipo_proceso,
            a.cantidad_m2,
            a.cantidad_laminas,
            a.pasadas,
            a.modo_velocidad,
            a.tinta_blanca,
            a.day_night,
            a.prioridad,
            a.tipo_corte,
            a.cantidad_cortes,
            a.tiempo_produccion_min,
            a.tiempo_corte_min,
            a.tiempo_estimado_min,
            a.fecha_estimada_finalizacion,
            a.fecha_asignacion,
            a.usuario_asignacion,
            a.fecha_impresion,
            a.fecha_router

        FROM odp_asignaciones a

        WHERE a.estado IN ('EN PROCESO', 'EN ROUTER')

        {filtro}

        ORDER BY
            CASE UPPER(COALESCE(a.prioridad, 'NORMAL'))
                WHEN 'BOMBERAZO' THEN 1
                WHEN 'URGENTE' THEN 2
                ELSE 3
            END,
            a.fecha_asignacion ASC,
            a.numero_odp ASC,
            a.id ASC
        """,
        params
    )


def obtener_odps_finalizadas(maquina=None, fecha_inicio=None, fecha_fin=None):
    params = {}
    filtro = ""
    
    if maquina and maquina != "Todas":
        filtro += " AND (a.maquina_asignada=:maquina OR a.maquina_router=:maquina) "
        params["maquina"] = maquina
        
    # Filtro de fechas directo sobre la fecha de finalización real
    if fecha_inicio and fecha_fin:
        filtro += " AND a.fecha_finalizacion::date BETWEEN :fecha_inicio AND :fecha_fin "
        params["fecha_inicio"] = fecha_inicio
        params["fecha_fin"] = fecha_fin

    query = f"""
        SELECT a.id AS asignacion_id, a.numero_odp, a.cliente, a.material, a.estado,
               a.maquina_asignada, a.maquina_router, a.requiere_corte, a.tipo_proceso,
               a.cantidad_m2, a.cantidad_laminas, a.pasadas, a.tinta_blanca, a.day_night,
               a.prioridad, a.tipo_corte, a.cantidad_cortes, a.tiempo_produccion_min, a.tiempo_corte_min,
               a.tiempo_estimado_min, a.fecha_estimada_finalizacion, a.fecha_asignacion,
               a.fecha_impresion, a.fecha_router, a.fecha_finalizacion, a.usuario_asignacion 
        FROM odp_asignaciones a 
        WHERE (a.estado='CORTADO' OR (a.estado='IMPRESO' AND a.requiere_corte=FALSE)) {filtro} 
        ORDER BY a.fecha_finalizacion DESC, a.numero_odp
    """
    return query_db(query, params)

def obtener_registro_odps_finalizadas(maquina=None, fecha_inicio=None, fecha_fin=None):
    # Pasamos las fechas a la función principal
    df = obtener_odps_finalizadas(maquina, fecha_inicio, fecha_fin)
    if df.empty: 
        return df
    
    df = df.rename(columns={
        "numero_odp":"ODP", "cliente":"Cliente", "material":"Material",
        "maquina_asignada":"Máquina Impresión", "maquina_router":"Máquina Router",
        "requiere_corte":"Requiere corte", "tipo_proceso":"Ruta",
        "cantidad_m2":"m²", "cantidad_laminas":"Láminas", "pasadas":"Pasadas",
        "tinta_blanca":"Tinta blanca", "day_night":"Day & Night",
        "prioridad":"Prioridad",
        "tipo_corte":"Tipo corte", "cantidad_cortes":"Cortes",
        "tiempo_produccion_min":"Min impresión", "tiempo_corte_min":"Min corte",
        "tiempo_estimado_min":"Min total estimado",
        "fecha_estimada_finalizacion":"Fin estimado",
        "estado":"Estado", "fecha_asignacion":"Asignación",
        "fecha_impresion":"Impresión", "fecha_router":"Router",
        "fecha_finalizacion":"Finalización", "usuario_asignacion":"Usuario"
    }).copy()

    # Conservar la prioridad que tuvo la ODP al momento de finalizar.
    # Registros históricos sin prioridad se consideran NORMAL.
    if "Prioridad" in df.columns:
        df["Prioridad"] = df["Prioridad"].apply(normalizar_prioridad_odp)
    
    df["Requiere corte"] = df["Requiere corte"].map({True:"Sí", False:"No"}).fillna("No")
    # Estandarización visual: nunca mostrar None/NaN en Pasadas.
    # Cuando no se registró una cantidad de pasadas, se interpreta visualmente
    # como el modo estándar de producción.
    if "Pasadas" in df.columns:
        def _formatear_pasadas_tabla(x):
            if x is None or pd.isna(x):
                return "ESTÁNDAR"
            try:
                xf = float(x)
                if xf.is_integer():
                    return str(int(xf))
            except Exception:
                pass
            return str(x)
        df["Pasadas"] = df["Pasadas"].apply(_formatear_pasadas_tabla)
    return df




# ============================================================
# PLANEACIÓN DE PRODUCCIÓN — TIEMPOS ESTIMADOS
# ============================================================
# La calibración vive en backend/config.py. Cada máquina puede
# declarar:
#   "produccion": {
#       "min_por_m2": 6.0,
#       "min_por_m2_pasadas": {12: 6.0, 16: 8.0, 24: 12.0, 32: 16.0},
#       "min_por_corte": {"BROCA": 0.5, "NAVAJA": 0.3, ...},
#       "ancho_util_m": 3.2
#   }
# No se inventan velocidades: si faltan en config, el cálculo
# devuelve 0 y el tablero muestra "Pendiente de calibrar".

TIPOS_CORTE = ["BROCA", "NAVAJA", "CORTE 45", "PLECA", "CORTE COMPLETO STICKER"]





def _numero_seguro(valor, default=0.0):
    try:
        if valor is None or pd.isna(valor):
            return float(default)
        return float(valor)
    except Exception:
        return float(default)


























inicializar_base_de_datos()

#clase para pdf
# =========================================================
# 8. FUNCIONES DE APOYO
# =========================================================
class MockObj:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

def check_password(username, password):
    res = query_db("SELECT * FROM usuarios WHERE username = :u", {"u": username})
    if not res.empty:
        res.columns = [c.lower() for c in res.columns]
        db_pass = str(res.iloc[0]['password']).strip()
        input_hash = hashlib.sha256(password.encode()).hexdigest()
        if db_pass == input_hash:
            return MockObj(id=res.iloc[0]['id'], username=res.iloc[0]['username'], role=res.iloc[0]['role'])
    return None

def save_test_result(machine_name, health_score, missing_nodes, health_map, evidence_path):
    map_json = json.dumps(health_map)
    commit_db("""
        INSERT INTO test_results (machine_name, health_score, missing_nodes, health_map, evidence_path, timestamp)
        VALUES (:m, :s, :n, :map, :e, :t)
    """, {"m": machine_name, "s": health_score, "n": missing_nodes, "map": map_json, "e": evidence_path, "t": ahora_mexico()})


def render_machine_card(m_name, fecha_consulta, suffix=""):
    config = MACHINE_CONFIGS.get(m_name, {})
    if isinstance(config, dict):
        es_manual = config.get("type") == "manual"
    else:
        es_manual = "Router" in m_name

    inicio_dia = datetime.combine(fecha_consulta, dt_time.min)
    fin_dia = datetime.combine(fecha_consulta, dt_time.max)

    res_estado = query_db("SELECT estado FROM estados_maquinas WHERE machine_name = :m", {"m": m_name})
    estado_actual = res_estado.iloc[0]['estado'] if not res_estado.empty else "Operativa"
    
    color_router = "#1f77b4" 
    opciones_estilo = {
        "Operativa": {"color_b": "#28a745", "color_f": "rgba(40, 167, 69, 0.05)", "icon": "✅"},
        "Mantenimiento": {"color_b": "#6c757d", "color_f": "rgba(108, 117, 125, 0.1)", "icon": "🛠️"},
        "Falla Total": {"color_b": "#dc3545", "color_f": "rgba(220, 53, 69, 0.1)", "icon": "🚫"},
        "Falla de Slots": {"color_b": "#fd7e14", "color_f": "rgba(253, 126, 20, 0.1)", "icon": "😥"},
        "Falla de Tarjetas": {"color_b": "#0dcaf0", "color_f": "rgba(13, 202, 240, 0.1)", "icon": "😟"}
    }
    
    if estado_actual in opciones_estilo:
        estilo = opciones_estilo[estado_actual].copy()
    else:
        estilo = {"color_b": "#ffc107", "color_f": "rgba(255, 193, 7, 0.1)", "icon": "⚠️"}

    with st.container(border=True):
        if es_manual:
            df_manual = query_db("""
                SELECT health_score FROM test_results 
                WHERE machine_name = :m 
                AND timestamp BETWEEN :i AND :f
                ORDER BY timestamp DESC LIMIT 1
            """, {"m": m_name, "i": inicio_dia, "f": fin_dia})
            
            health_val = f"{df_manual.iloc[0]['health_score']:.1f}%" if not df_manual.empty else "N/A"
            icono_router = "🪚" if estado_actual == "Operativa" else estilo['icon']
            
            if estado_actual == "Operativa":
                color_b_card = color_router 
                color_f_card = "rgba(31, 119, 180, 0.05)" 
            else:
                color_b_card = estilo['color_b']
                color_f_card = estilo['color_f']
                
            st.html(f"""
                <div style="height: 355px; border-left: 5px solid {color_b_card}; padding: 25px; 
                            background-color: {color_f_card}; display: flex; flex-direction: column; 
                            justify-content: center; align-items: center; text-align: center; box-sizing: border-box;">
                    <h1 style="font-size: 3.5em; margin: 0;">{icono_router}</h1>
                    <h2 style="margin: 10px 0; font-family: sans-serif; font-weight: 700; color: #1a1a1a;">{m_name}</h2>
                    <div style="margin: 20px 0;">
                        <p style="font-size: 0.85em; color: #666; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px;">Estatus del Equipo</p>
                        <h1 style="margin: 0; color: {color_b_card}; font-size: 2.8em; font-family: sans-serif; font-weight: bold;">{health_val}</h1>
                    </div>
                    <div style="background-color: {color_b_card}; color: white; padding: 10px 0; 
                                font-weight: bold; text-transform: uppercase; font-size: 0.9em; letter-spacing: 2px; width: 100%; border-radius: 2px;">
                        {estado_actual}
                    </div>
                </div>
            """)
        else:
            df_test = query_db("""
                SELECT * FROM test_results 
                WHERE machine_name = :m 
                AND timestamp BETWEEN :inicio AND :fin
                ORDER BY timestamp DESC LIMIT 1
            """, {"m": m_name, "inicio": inicio_dia, "fin": fin_dia})
            
            last_test = df_test.iloc[0] if not df_test.empty else None

            if estado_actual == "Operativa" and last_test is not None:
                health = last_test['health_score']
                if health < 75: estilo["color_b"] = "#fd7e14"
                if health < 50: estilo["color_b"] = "#dc3545"

            if last_test is not None:
                ts = last_test['timestamp']
                fecha_txt = ts.strftime('%d/%m/%Y %I:%M %p') if hasattr(ts, 'strftime') else str(ts)
            else:
                fecha_txt = "Sin registros"

            if estado_actual == "Operativa" and last_test is not None:
                st.markdown(f"""
                    <div style="height: 60px; border-bottom: 1px solid {estilo['color_b']}; margin-bottom: 10px;">
                        <h3 style="margin: 0; color: {estilo['color_b']};">🖨️ {m_name}</h3>
                        <p style="color: gray; font-size: 0.8em; margin: 0;">Registro Último Test: {fecha_txt}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.metric(
                    label="Status", 
                    value=f"{last_test['health_score']:.1f}%", 
                    delta=f"{int(last_test['missing_nodes'])} Nozzles Fallidos", 
                    delta_color="inverse"
                )
                
                history = query_db("""
                    SELECT timestamp, health_score FROM test_results 
                    WHERE machine_name = :m ORDER BY timestamp DESC LIMIT 10
                """, {"m": m_name})
                
                if not history.empty:
                    st.area_chart(
                        history.sort_values('timestamp').set_index('timestamp')['health_score'], 
                        height=150, 
                        color=[estilo["color_b"]]
                    )
            else:
                etiqueta = estado_actual if last_test is not None or estado_actual != "Operativa" else "SIN TEST PROCESADO"
                
                st.markdown(f"""
                    <div style="height: 372px; border: 2px solid {estilo['color_b']}; border-radius: 10px; padding: 20px; 
                                background-color: {estilo['color_f']}; display: flex; flex-direction: column; 
                                justify-content: center; align-items: center; text-align: center; box-sizing: border-box;">
                        <h1 style="font-size: 3.5em; margin: 0;">{estilo['icon']}</h1>
                        <h2 style="margin: 10px 0;">{m_name}</h2>
                        <div style="background-color: {estilo['color_b']}; color: white; padding: 6px 20px; 
                                    border-radius: 20px; font-weight: bold; text-transform: uppercase; font-size: 0.9em;">
                            {etiqueta}
                        </div>
                        <p style="color: gray; font-size: 0.9em; margin-top: 25px;">
                            {f"Último análisis: {fecha_txt}" if last_test is not None else "No hay registros de análisis en esta fecha."}
                        </p>
                    </div>
                """, unsafe_allow_html=True)


def generar_svg_slot_falla(color="#fd7e14"):
    return f"""
    <div style="text-align: center; padding: 10px;">
        <svg width="80" height="80" viewBox="0 0 100 100">
            <path d="M 20 20 L 80 20 L 80 60 L 70 75 L 30 75 L 20 60 Z" fill="none" stroke="{color}" stroke-width="3"/>
            <rect x="35" y="75" width="6" height="12" fill="{color}" opacity="0.3"/>
            <rect x="47" y="75" width="6" height="12" fill="{color}" opacity="0.3"/>
            <rect x="59" y="75" width="6" height="12" fill="#e63946"/>
            <line x1="59" y1="90" x2="65" y2="96" stroke="#e63946" stroke-width="2"/>
            <line x1="65" y1="90" x2="59" y2="96" stroke="#e63946" stroke-width="2"/>
        </svg>
    </div>
    """

# =========================================================
# 9. LÓGICA DE LOGIN
# =========================================================
if not st.session_state.authenticated:
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
                            "username": user.username
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

# =========================================================
# 10. INTERFAZ PRINCIPAL (POST-LOGIN)
# =========================================================
posibles_rutas = [
    os.path.join(os.getcwd(), "assets", "logo.png"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")
]
ruta_logo = None
for r in posibles_rutas:
    if os.path.exists(r):
        ruta_logo = r
        break

if ruta_logo:
    with open(ruta_logo, 'rb') as f: 
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

with st.sidebar:
    st.write(f"👤 Usuario: **{st.session_state.username}**")
    st.write(f"🎖️ Rol: **{st.session_state.user_role.capitalize()}**")

    with st.expander("⚙️ Editar Mi Perfil"):
        new_user_val = st.text_input("Nuevo usuario", key="gestion_user", value=st.session_state.username)
        new_pass_val = st.text_input("Nueva Contraseña", type="password", key="gestion_pass", help="Dejar en blanco para no cambiar")
        confirm_pass_val = st.text_input("Confirmar Nueva Contraseña", type="password", key="gestion_confirm")
        st.divider()
        old_pw = st.text_input("Contraseña Actual", type="password", key="old_pass_input")
        
        if st.button("💾 Guardar Cambios"):
            if old_pw:
                res_u = query_db("SELECT * FROM usuarios WHERE username = :u", {"u": st.session_state.username})
                if not res_u.empty and res_u.iloc[0]['password'] == hashlib.sha256(old_pw.encode()).hexdigest():
                    if new_pass_val == confirm_pass_val:
                        h_new = hashlib.sha256(new_pass_val.encode()).hexdigest() if new_pass_val else res_u.iloc[0]['password']
                        user_id_puro = int(res_u.iloc[0]['id']) 
                        exito = commit_db(
                            "UPDATE usuarios SET username = :nu, password = :np WHERE id = :uid",
                            {"nu": new_user_val, "np": h_new, "uid": user_id_puro}
                        )
                        if exito:
                            st.session_state.username = new_user_val
                            st.session_state["perfil_actualizado"] = True
                            st.rerun()
                    else: 
                        st.error("❌ Contraseñas nuevas no coinciden")
                else: 
                    st.error("❌ Contraseña actual incorrecta")
            else: 
                st.warning("⚠️ Introduce tu contraseña actual para confirmar cambios")
    
    if st.session_state.get("perfil_actualizado"):
        st.success("✅ Contraseña y perfil actualizados correctamente")
        del st.session_state["perfil_actualizado"]

    
    
    st.divider()
    st.header("🛠️ Gestión de Equipos")
    maquina_a_configurar = st.selectbox("Seleccionar Máquina para Estado:", list(MACHINE_CONFIGS.keys()))
    
    res_est_actual = query_db("SELECT estado FROM estados_maquinas WHERE machine_name = :m", {"m": maquina_a_configurar})
    est_defecto = res_est_actual.iloc[0]['estado'] if not res_est_actual.empty else "Operativa"
    opciones_predefinidas = ["Operativa", "Mantenimiento", "Falla Total", "Falla de Slots", "Falla de Tarjetas"]
    
    if est_defecto in opciones_predefinidas:
        index_defecto = opciones_predefinidas.index(est_defecto)
        valor_personalizado_defecto = ""
    else:
        index_defecto = len(opciones_predefinidas) 
        valor_personalizado_defecto = est_defecto 

    opciones_select = opciones_predefinidas + ["Especificar manual"]
    nuevo_est_select = st.selectbox("Definir estado:", opciones_select, index=index_defecto)
    
    if nuevo_est_select == "Especificar manual":
        estado_final = st.text_input("Ingresa la falla o estado detectado:", value=valor_personalizado_defecto)
    else:
        estado_final = nuevo_est_select
    
    if st.button("🔄 Actualizar Estado"):
        if not estado_final.strip():
            st.warning("⚠️ El campo de estado personalizado no puede estar vacío.")
        else:
            # Solo registrar si el estado es diferente al actual
            if estado_final != est_defecto:
                # 1. Cerrar el estado anterior en el historial (calcular horas)
                commit_db("""
                    UPDATE historial_estados 
                    SET fecha_fin = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'),
                        duracion_horas = EXTRACT(EPOCH FROM ((CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City') - fecha_inicio)) / 3600.0
                    WHERE machine_name = :m AND fecha_fin IS NULL
                """, {"m": maquina_a_configurar})
                
                # 2. Registrar el inicio del nuevo estado
                commit_db("""
                    INSERT INTO historial_estados (machine_name, estado, fecha_inicio)
                    VALUES (:m, :e, (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'))
                """, {"m": maquina_a_configurar, "e": estado_final})

                # 3. Actualizar el estado actual (lógica original)
                commit_db("""
                    INSERT INTO estados_maquinas (machine_name, estado, updated_at)
                    VALUES (:m, :e, (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City'))
                    ON CONFLICT (machine_name) 
                    DO UPDATE SET estado = EXCLUDED.estado, updated_at = (CURRENT_TIMESTAMP AT TIME ZONE 'America/Mexico_City');
                """, {"m": maquina_a_configurar, "e": estado_final})
                
                st.success(f"✅ Estado de {maquina_a_configurar} guardado en la red como: **{estado_final}**")
                time.sleep(1)
                st.rerun()
            else:
                st.info(f"El equipo ya se encuentra en estado: {estado_final}")

    st.divider()
    ahora_gdl = ahora_mexico()
    fecha_real_hoy = ahora_gdl.date()
    
    st.sidebar.header("🔍 Consultar Historial")
    fecha_consulta = st.sidebar.date_input("Fecha de consulta", value=fecha_real_hoy, key="fecha_filtro_principal")
    es_hoy = (fecha_consulta == fecha_real_hoy)
    
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.user_role = None
        cookies["authenticated"] = "false"
        cookies["username"] = ""
        cookies["role"] = ""
        cookies.save()
        st.rerun()

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
# COMPATIBILIDAD MATERIAL ↔ ESTACIÓN
# ============================================================
# Las reglas se mantienen aquí además de la UI para que el filtro no sea
# solamente visual: la función de asignación también valida la compatibilidad.
MAQUINAS_FLEXIBLES = {
    "EPSON 1", "EPSON 2", "ALLWIN", "GRANDO", "DURST 312",
    "MIMAKI", "FAVUTEK"
}

MAQUINAS_RIGIDO_FLEXIBLE = {
    "VUTEK PRO", "VUTEK F4", "VUTEK H5", "DURST P10 PLUS"
}

ROUTERS_RIGIDO_FLEXIBLE = {
    "ROUTER ZUND XL", "ROUTER ZUND G3", "ROUTER KONSGGBERG",
    "ROUTER KONSGBERG", "ROUTER KONSGSBERG"
}

# El nombre real de la configuración actual es "Router Konsgberg".
ROUTERS_RIGIDO_FLEXIBLE = {
    "ROUTER ZUND XL", "ROUTER ZUND G3", "ROUTER KONSGGBERG",
    "ROUTER KONSGBERG", "ROUTER KONSGGBERG", "ROUTER KONSGSBERG",
    "ROUTER KONSGGBERG", "ROUTER KONSGGBERG", "ROUTER KONSGGBERG",
    "ROUTER KONSGBERG", "ROUTER KONSGBERG"
}

# Normalizamos por nombre para tolerar mayúsculas/minúsculas y la escritura
# histórica "Konsgberg" usada en la configuración.
def _norm_nombre_estacion(nombre):
    return " ".join(str(nombre or "").strip().upper().split())


def maquina_compatible_material(nombre_maquina, material):
    n = _norm_nombre_estacion(nombre_maquina)
    m = _norm_nombre_estacion(material)

    if not n or not m:
        return False

    # Xerox: exclusivamente papel couché.
    if n == "XEROX":
        return m in {"PAPEL COUCHÉ", "PAPEL COUCHE"}

    # Plotter Recorte: exclusivamente recorte de vinil.
    if "PLOTTER RECORTE" in n:
        return m == "VINIL"

    # Routers de mesa: aceptan rígido y flexible, excepto el Plotter.
    if "ROUTER" in n:
        if "PLOTTER RECORTE" in n:
            return m == "VINIL"
        # Los tres routers CNC también son compatibles con trabajos
        # provenientes de XEROX sobre papel couché.
        return m in {
            "RIGIDO", "RÍGIDO", "FLEXIBLE", "GENERAL",
            "PAPEL COUCHÉ", "PAPEL COUCHE"
        }

    # Impresión: Vutek/F4/H5/P10 aceptan ambos.
    if n in MAQUINAS_RIGIDO_FLEXIBLE:
        return m in {"RIGIDO", "RÍGIDO", "FLEXIBLE", "VINIL", "GENERAL"}

    # Máquinas exclusivamente flexibles.
    if n in MAQUINAS_FLEXIBLES:
        return m in {"FLEXIBLE", "VINIL", "GENERAL"}

    # Para configuraciones antiguas/no clasificadas, no bloqueamos GENERAL.
    return m == "GENERAL"


def maquinas_impresion_compatibles(material, maquinas):
    return [m for m in (maquinas or []) if maquina_compatible_material(m, material)]


def routers_compatibles(material, maquinas):
    return [m for m in (maquinas or []) if maquina_compatible_material(m, material)]


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

    with st.expander("🟢 ÓRDENES DE PRODUCCIÓN EN CURSO", expanded=False):
        # La lista de ODPs se puede actualizar manualmente para que el operador
        # tenga control sobre cuándo traer los cambios más recientes de BD.
        col_filtro_op, col_refresh_op = st.columns([4.5, 1.0], gap="small")
        with col_filtro_op:
            filtro_op = st.selectbox(
                "Filtrar por estación",
                ["Todas"] + todas_maquinas,
                key="filtro_odp_maquina_v4"
            )
        with col_refresh_op:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("🔄 Actualizar", use_container_width=True, key="btn_actualizar_odps_proceso"):
                query_db.clear()
                st.rerun()

        df_proc = obtener_odps_en_proceso(filtro_op)
        df_bomberazos = df_proc[df_proc["prioridad"].apply(prioridad_es_critica)] if (not df_proc.empty and "prioridad" in df_proc.columns) else pd.DataFrame()
        if not df_bomberazos.empty:
            nombres_alarm = ", ".join(f"ODP {x}" for x in df_bomberazos["numero_odp"].astype(str).tolist()[:5])
            if len(df_bomberazos) > 5: nombres_alarm += f" +{len(df_bomberazos)-5} más"
            planta_html(f'<div class="odp-alarm-banner">🚨 BOMBERAZO ACTIVO · {planta_escape(nombres_alarm)} · ATENCIÓN PRIORITARIA</div>')
        if df_proc.empty:
            st.info("No hay órdenes de producción activas bajo los criterios actuales.")
        else:
            planta_html('<div class="odp-process-panel"><div class="odp-process-title"><span>📋 Asignaciones activas</span><span class="odp-process-badge">' + str(len(df_proc)) + ' ACTIVAS</span></div></div>')
            # Altura fija equivalente a unas 5 tarjetas compactas. Si hay más
            # registros, el usuario se desplaza dentro del panel y el resto
            # del dashboard no se desplaza hacia abajo.
            with st.container(height=1100, border=False):
                for _, r in df_proc.iterrows():
                    aid = int(r["asignacion_id"]); numero = str(r["numero_odp"]); cliente = str(r["cliente"]); est = str(r["estado"]); corte = bool(r["requiere_corte"])
                    with st.container(border=True):
                        a, b, c = st.columns([2.0, 2.3, 1.7], gap="small")
                        with a:
                            p_odp = normalizar_prioridad_odp(r.get("prioridad"))
                            st.markdown(f"**📋 ODP {numero}** · {etiqueta_prioridad_odp(p_odp)}")
                            st.caption(f"👤 {cliente} · 🗞️ {r['material']}")
                        with b:
                            maquina_display = r['maquina_asignada'] or 'Solo ROUTER'
                            st.write(f"🖨️ {maquina_display}")
                            if corte:
                                st.caption(f"🪚 ROUTER: {r['maquina_router'] or 'SIN ASIGNAR'}")
                            # En la tarjeta de una impresora mostramos solo impresión.
                            # En la tarjeta de un Router mostramos solo corte.
                            if r.get('tiempo_produccion_min') and _numero_seguro(r.get('tiempo_produccion_min'), 0) > 0:
                                st.caption(f"🖨️ Impresión: **{formatear_duracion(_numero_seguro(r.get('tiempo_produccion_min'), 0))}**")
                            if corte and r.get('tiempo_corte_min') and _numero_seguro(r.get('tiempo_corte_min'), 0) > 0:
                                st.caption(f"🪚 Corte: **{formatear_duracion(_numero_seguro(r.get('tiempo_corte_min'), 0))}**")
                            st.caption(f"Estado: **{est}**")
                        with c:
                            if st.button("✏️ Editar parámetros", key=f"edit_{aid}", use_container_width=True):
                                st.session_state[f"editar_odp_{aid}"] = not st.session_state.get(f"editar_odp_{aid}", False)
                                st.rerun()

                            if st.session_state.get(f"editar_odp_{aid}", False):
                                with st.expander("⚙️ Ajustar ODP", expanded=True):
                                    edit_prioridad = normalizar_prioridad_odp(r.get("prioridad"))
                                    edit_prioridad = st.selectbox("🚦 Prioridad", PRIORIDADES_ODP, index=PRIORIDADES_ODP.index(edit_prioridad), key=f"edit_prioridad_{aid}", format_func=lambda x: etiqueta_prioridad_odp(x))
                                    edit_pass = r.get("pasadas", None)
                                    edit_modo = r.get("modo_velocidad", None) or "MAXIMA"
                                    edit_tipo_corte = r.get("tipo_corte", None)
                                    edit_cortes = int(r.get("cantidad_cortes", 1) or 1)

                                    pass_opts_edit = []
                                    # Las pasadas pertenecen a la IMPRESORA, no al Router.
                                    # Una ODP puede ser "IMPRESION + CORTE" y aun así debe
                                    # permitir editar las pasadas de impresión.
                                    if r.get("maquina_asignada"):
                                        pass_opts_edit = opciones_pasadas_para_maquina(
                                            r.get("maquina_asignada"),
                                            tinta_blanca=bool(r.get("tinta_blanca")),
                                            day_night=bool(r.get("day_night")),
                                        )
                                    nombre_edit_maquina = str(r.get("maquina_asignada") or "").strip().upper()
                                    if nombre_edit_maquina == "VUTEK PRO" and bool(r.get("tinta_blanca")):
                                        pass_opts_edit = [48]
                                    elif nombre_edit_maquina == "VUTEK PRO" and bool(r.get("day_night")):
                                        pass_opts_edit = [72]
                                    elif nombre_edit_maquina in {"EPSON 1", "EPSON 2"} and bool(r.get("tinta_blanca")):
                                        pass_opts_edit = [12]

                                    if pass_opts_edit:
                                        current_pass = int(r["pasadas"]) if pd.notna(r["pasadas"]) else pass_opts_edit[0]
                                        if current_pass not in pass_opts_edit:
                                            current_pass = pass_opts_edit[0]
                                        edit_pass = st.selectbox("Pasadas", pass_opts_edit, index=pass_opts_edit.index(current_pass), key=f"edit_pass_{aid}")

                                    if r["maquina_asignada"] and str(r["maquina_asignada"]).strip().upper() in {"VUTEK PRO", "VUTEK F4"}:
                                        edit_modo = st.radio(
                                            "Velocidad",
                                            ["MAXIMA", "ESTANDAR"],
                                            index=0 if str(r.get("modo_velocidad", "MAXIMA") or "MAXIMA").upper() == "MAXIMA" else 1,
                                            horizontal=True,
                                            key=f"edit_modo_{aid}",
                                            format_func=lambda x: "⚡ Máxima" if x == "MAXIMA" else "🎯 Estándar"
                                        )

                                    if corte and r.get("maquina_router"):
                                        cfg_re = _config_produccion_maquina(r.get("maquina_router"))
                                        tipos_re = cfg_re.get("tipos_corte") or TIPOS_CORTE
                                        if edit_tipo_corte not in tipos_re:
                                            edit_tipo_corte = tipos_re[0]
                                        edit_tipo_corte = st.selectbox(
                                            "Tipo de corte",
                                            tipos_re,
                                            index=tipos_re.index(edit_tipo_corte),
                                            key=f"edit_tipo_corte_{aid}"
                                        )
                                        edit_cortes = st.number_input(
                                            "Cantidad de cortes",
                                            min_value=1,
                                            value=max(1, edit_cortes),
                                            step=1,
                                            key=f"edit_cortes_{aid}"
                                        )

                                    if st.button("💾 Guardar cambios", type="primary", use_container_width=True, key=f"save_edit_{aid}"):
                                        ok_edit, msg_edit = editar_asignacion_produccion(
                                            aid,
                                            pasadas=edit_pass,
                                            prioridad=edit_prioridad,
                                            tipo_corte=edit_tipo_corte,
                                            cantidad_cortes=edit_cortes,
                                            modo_velocidad=edit_modo,
                                            usuario=st.session_state.username,
                                        )
                                        if ok_edit:
                                            st.success(msg_edit)
                                            st.session_state[f"editar_odp_{aid}"] = False
                                            time.sleep(.25)
                                            st.rerun()
                                        else:
                                            st.error(msg_edit)

                            if st.button("➕ Otra asignación", key=f"otra_{aid}", use_container_width=True):
                                st.session_state.odp_para_asignar = numero
                                st.session_state.odp_proceso_expanded = False
                                st.rerun()
                            if st.button("🗑️ Eliminar", key=f"elim_{aid}", use_container_width=True):
                                st.session_state[f"confirmar_eliminar_{aid}"] = True
                                st.rerun()
                        if st.session_state.get(f"confirmar_eliminar_{aid}", False):
                            st.warning(f"¿Eliminar la asignación de la ODP {numero}? Se registrará como cancelación.")
                            y, n = st.columns(2)
                            with y:
                                if st.button("Sí, eliminar asignación", key=f"conf_elim_{aid}", type="primary", use_container_width=True):
                                    ok, msg = eliminar_asignacion(aid, st.session_state.username)
                                    st.session_state[f"confirmar_eliminar_{aid}"] = False
                                    if ok: st.success(msg)
                                    else: st.error(msg)
                                    time.sleep(.2); st.rerun()
                            with n:
                                if st.button("Cancelar", key=f"cancel_elim_{aid}", use_container_width=True):
                                    st.session_state[f"confirmar_eliminar_{aid}"] = False
                                    st.rerun()
                        if est == "EN PROCESO":
                            if st.button("🟦 MARCAR IMPRESO", key=f"imp_{aid}", type="primary", use_container_width=True):
                                ok, msg = actualizar_estado_asignacion(aid, "IMPRESO", st.session_state.username)
                                if ok: st.success(msg)
                                else: st.error(msg)
                                time.sleep(.2); st.rerun()
                        elif est == "EN ROUTER":
                            if st.button("🟩 MARCAR CORTADO / FINALIZAR", key=f"cut_{aid}", type="primary", use_container_width=True):
                                ok, msg = actualizar_estado_asignacion(aid, "CORTADO", st.session_state.username)
                                if ok: st.success(msg)
                                else: st.error(msg)
                                time.sleep(.2); st.rerun()

    # ============================================================
    # OTRA ASIGNACIÓN PARA LA MISMA ODP
    # ============================================================
    if st.session_state.get("odp_para_asignar"):
        odp_sel = st.session_state.odp_para_asignar
        df_o = query_db(
            "SELECT numero_odp, cliente FROM odps WHERE numero_odp=:o",
            {"o": odp_sel}
        )

        if not df_o.empty:
            cliente_odp = str(df_o.iloc[0]["cliente"] or "")

            planta_html(
                f"""<div class="assign-hero"><div class="assign-kicker">Asignación complementaria</div><div class="assign-title">➕ ODP {planta_escape(odp_sel)}</div><div class="assign-subtitle">{planta_escape(cliente_odp)} · Asigna una nueva parte sin modificar las asignaciones existentes.</div></div>"""
            )

            tipo2 = st.radio(
                "Ruta complementaria",
                ["IMPRESION", "IMPRESION + CORTE", "SOLO CORTE"],
                horizontal=True,
                key=f"tipo2_{odp_sel}"
            )
            solo2 = tipo2 == "SOLO CORTE"
            corte2 = tipo2 in {"IMPRESION + CORTE", "SOLO CORTE"}

            x1, x2 = st.columns(2)
            with x1:
                if solo2:
                    m2 = None
                    st.info("🪚 **Solo corte:** no se asignará impresora.")
                else:
                    m2 = st.selectbox("🖨️ Impresora", maquinas_impresion, key=f"m2_{odp_sel}")
            with x2:
                mat2 = st.selectbox("🗞️ Material", ["FLEXIBLE", "RÍGIDO", "VINIL", "PAPEL COUCHÉ", "GENERAL"], key=f"mat2_{odp_sel}")

            prioridad2 = st.selectbox("🚦 Prioridad de la asignación", PRIORIDADES_ODP, key=f"prioridad2_{odp_sel}", format_func=lambda x: etiqueta_prioridad_odp(x))

            if corte2:
                router2 = st.selectbox(
                    "🔧 Router CNC",
                    maquinas_router if maquinas_router else ["Sin ROUTER"],
                    key=f"router2_{odp_sel}"
                )
            else:
                router2 = None
                st.markdown('<div class="route-note">✓ Ruta sin corte · no requiere Router</div>', unsafe_allow_html=True)

            cantidad_m2_2 = 0.0
            laminas2 = 0
            pasadas2 = None
            blanco2 = False
            dn2 = False
            doble_saturacion2 = False

            if not solo2:
                q1, q2, q3 = st.columns(3)
                cfg_m2_form = _config_produccion_maquina(m2)
                ancho2 = _numero_seguro(cfg_m2_form.get("ancho_referencia_m"), 1.52) or 1.52
                if mat2 == "FLEXIBLE":
                    with q1:
                        metros2 = st.number_input("Metros lineales", min_value=0.0, step=0.5, key=f"metros2_{odp_sel}")
                    cantidad_copias2 = int(metros2) if metros2 >= 1 else (1 if metros2 > 0 else 0)
                    cantidad_m2_2 = float(metros2 * ancho2)
                    with q2:
                        st.metric("Copias calculadas", cantidad_copias2)
                    with q3:
                        st.metric("Ancho estándar", f"{ancho2:.2f} m")
                elif mat2 == "RÍGIDO":
                    with q1:
                        laminas2 = st.number_input("Láminas · 1.22 × 2.44 m", min_value=0, step=1, key=f"laminas2_{odp_sel}")
                    cantidad_m2_2 = float(laminas2 * M2_POR_LAMINA_RIGIDA)
                    with q2:
                        st.metric("Copias", int(laminas2 or 0))
                    with q3:
                        st.metric("Área", f"{cantidad_m2_2:.2f} m²")
                else:
                    with q1:
                        cantidad_m2_2 = st.number_input("Cantidad (m²)", min_value=0.0, step=1.0, key=f"m2_2_{odp_sel}")
                    with q3:
                        st.metric("Área", f"{cantidad_m2_2:.2f} m²")

                pass_options2 = opciones_pasadas_para_maquina(
                    m2,
                    tinta_blanca=bool(r.get("tinta_blanca")),
                    day_night=bool(r.get("day_night")),
                )
                if pass_options2:
                    p1, p2, p3 = st.columns(3)
                    with p1:
                        pasadas2 = st.selectbox("Pasadas", pass_options2, key=f"pasadas2_{odp_sel}")
                    with p2:
                        if "vutek" in str(m2).lower() and "pro" in str(m2).lower():
                            blanco2 = st.checkbox("🎨 Tinta blanca a registro (×2)", key=f"blanco2_{odp_sel}")
                    with p3:
                        if "vutek" in str(m2).lower() and "pro" in str(m2).lower():
                            dn2 = st.checkbox("🌗 Day & Night (×3)", key=f"dn2_{odp_sel}")

            if (
                m2
                and str(m2).strip().upper() == "DURST 312"
                and not solo2
            ):
                doble_saturacion2 = st.checkbox(
                    "🔥 Doble saturación",
                    key=f"doble_sat2_{odp_sel}"
                )
                if pasadas2 is None:
                    pasadas2 = 4

            tipo_corte2 = None
            cantidad_cortes2 = 0
            if corte2:
                c1, c2 = st.columns([2.2, 1.2])
                with c1:
                    cfg_router2 = _config_produccion_maquina(router2)
                    tipos_router2 = cfg_router2.get("tipos_corte") or TIPOS_CORTE
                    tipo_corte2 = st.selectbox("Tipo de corte", tipos_router2, key=f"tc2_{odp_sel}")
                with c2:
                    cantidad_cortes2 = st.number_input("Cantidad de cortes", min_value=1, value=1, step=1, key=f"nc2_{odp_sel}")

            ml2 = float(metros2) if mat2 == "FLEXIBLE" else (float(laminas2) * LARGO_LAMINA_RIGIDA_M if mat2 == "RÍGIDO" else 0.0)
            copias2 = cantidad_copias2 if mat2 == "FLEXIBLE" else (int(laminas2 or 0) if mat2 == "RÍGIDO" else 1)
            modo2 = "MAXIMA"
            if m2 and str(m2).strip().upper() in {"VUTEK PRO", "VUTEK F4"}:
                modo2 = st.radio(
                    "Velocidad",
                    ["MAXIMA", "ESTANDAR"],
                    horizontal=True,
                    key=f"modo2_{odp_sel}",
                    format_func=lambda x: "⚡ Máxima" if x == "MAXIMA" else "🎯 Estándar"
                )

            mi2, mc2, mt2 = estimar_produccion(
                m2, router2 if corte2 else None, mat2, tipo2,
                cantidad_m2_2, laminas2, pasadas2, blanco2, dn2,
                tipo_corte2, cantidad_cortes2,
                modo_velocidad=modo2,
                metros_lineales=ml2, cantidad_copias=copias2, ancho_material_m=ancho2,
                doble_saturacion=doble_saturacion2
            )
            if mt2 > 0:
                if corte2:
                    planta_html(
                        f"""<div class="time-summary"><div class="time-summary-label">⏱️ Tiempo estimado de esta asignación</div><div class="time-summary-main">🏁 {formatear_duracion(mt2)}</div><div class="time-summary-detail">🖨️ Impresión: <strong>{formatear_duracion(mi2)}</strong> &nbsp; · &nbsp; 🪚 Corte: <strong>{formatear_duracion(mc2)}</strong></div></div>"""
                    )
                else:
                    planta_html(
                        f"""<div class="time-summary"><div class="time-summary-label">⏱️ Tiempo estimado</div><div class="time-summary-main">🖨️ {formatear_duracion(mi2)}</div><div class="time-summary-detail">Ruta: <strong>Solo impresión</strong> · Sin tiempo de Router</div></div>"""
                    )
            else:
                st.info("Complete los campos de cantidad para calcular el tiempo de impresión.")

            z1, z2 = st.columns(2)
            with z1:
                guardar2 = st.button("🚀 ENVIAR A PRODUCCIÓN", type="primary", use_container_width=True, key=f"guardar2_{odp_sel}")
            with z2:
                cerrar2 = st.button("Cancelar", use_container_width=True, key=f"cerrar2_{odp_sel}")

            if cerrar2:
                st.session_state.odp_para_asignar = None
                st.rerun()

            if guardar2:
                if not solo2 and not m2:
                    st.error("Debe seleccionar una impresora.")
                elif corte2 and (not maquinas_router or router2 == "Sin ROUTER"):
                    st.error("Debe seleccionar un Router.")
                elif not solo2 and cantidad_m2_2 <= 0:
                    st.error("La cantidad de producción debe ser mayor que cero.")
                else:
                    ok, msg = asignar_odp(
                        odp_sel, m2, cliente_odp, st.session_state.username,
                        mat2, corte2, router2 if corte2 else None,
                        tipo2, cantidad_m2_2, laminas2, pasadas2,
                        blanco2, dn2, tipo_corte2, cantidad_cortes2,
                        modo2, ml2, copias2, ancho2,
                        doble_saturacion=doble_saturacion2,
                        prioridad=prioridad2,
                    )
                    if ok:
                        st.success(msg)
                        st.session_state.odp_para_asignar = None
                        time.sleep(.25)
                        st.rerun()
                    else:
                        st.error(msg)

    # ============================================================
    # ACABADAS + PDF / EXCEL
    # ============================================================
    with st.expander("🔵 HISTORIAL DE ODPs FINALIZADAS Y REPORTES", expanded=False):
    
        # ============================================================
        # FILTROS
        # ============================================================
        col_filtro, col_fecha = st.columns(2)
    
        with col_filtro:
            filtro_fin = st.selectbox(
                "Filtrar historial por estación",
                ["Todas"] + todas_maquinas,
                key="filtro_final_maquina_v3"
            )
    
        with col_fecha:
            fecha_default = (
                ahora_mexico().date() - timedelta(days=7),
                ahora_mexico().date()
            )
    
            rango_fechas = st.date_input(
                "Filtrar por rango de fechas",
                value=fecha_default,
                key="rango_fechas_odps_finalizadas"
            )
    
        # ============================================================
        # VALIDAR RANGO DE FECHAS
        # ============================================================
        if len(rango_fechas) == 2:
    
            fecha_inicio, fecha_fin = rango_fechas
    
            # ========================================================
            # CONSULTAR ODPs FINALIZADAS
            # ========================================================
            df_fin = obtener_registro_odps_finalizadas(
                filtro_fin,
                fecha_inicio,
                fecha_fin
            )
    
            if df_fin.empty:
    
                st.info(
                    "No existen registros de ODPs finalizadas "
                    "para el filtro seleccionado."
                )
    
            else:
    
                # ====================================================
                # BUSCADOR
                # ====================================================
                busqueda = st.text_input(
                    "🔍 Buscar por número de ODP o Cliente en este rango:",
                    "",
                    key="buscar_odp_historial"
                )
    
                if busqueda:
    
                    texto_busqueda = busqueda.strip()
    
                    df_fin = df_fin[
                        df_fin["ODP"]
                        .astype(str)
                        .str.contains(
                            texto_busqueda,
                            case=False,
                            na=False
                        )
                        |
                        df_fin["Cliente"]
                        .astype(str)
                        .str.contains(
                            texto_busqueda,
                            case=False,
                            na=False
                        )
                    ]
    
                if df_fin.empty:
    
                    st.warning(
                        "No se encontraron coincidencias para tu búsqueda."
                    )
    
                else:
    
                    # =================================================
                    # EXCEL
                    # =================================================
                    excel_data = dataframe_to_xlsx_bytes(df_fin)
    
                    # =================================================
                    # PDF
                    # =================================================
                    pdf = FPDF(
                        orientation="L",
                        unit="mm",
                        format="A4"
                    )
    
                    pdf.set_auto_page_break(
                        auto=True,
                        margin=10
                    )
    
                    pdf.add_page()
    
                    # -------------------------------------------------
                    # TÍTULO
                    # -------------------------------------------------
                    pdf.set_font(
                        "Helvetica",
                        "B",
                        15
                    )
    
                    pdf.cell(
                        0,
                        10,
                        "REGISTRO DE ODPs FINALIZADAS",
                        ln=True,
                        align="C"
                    )
    
                    # -------------------------------------------------
                    # INFORMACIÓN DEL REPORTE
                    # -------------------------------------------------
                    pdf.set_font(
                        "Helvetica",
                        "",
                        8
                    )
    
                    texto_filtro = (
                        "Todas"
                        if filtro_fin == "Todas"
                        else str(filtro_fin)
                    )
    
                    texto_periodo = (
                        f"Periodo: "
                        f"{fecha_inicio.strftime('%d/%m/%Y')} "
                        f"al "
                        f"{fecha_fin.strftime('%d/%m/%Y')}"
                    )
    
                    pdf.cell(
                        0,
                        6,
                        (
                            f"Generado: "
                            f"{ahora_mexico().strftime('%d/%m/%Y %H:%M')} "
                            f"| Estación: {texto_filtro} "
                            f"| {texto_periodo}"
                        ),
                        ln=True
                    )
    
                    pdf.ln(3)
    
                    # =================================================
                    # ENCABEZADOS
                    # =================================================
                    headers = [
                        "ODP",
                        "Cliente",
                        "Material",
                        "Máq. Impresión",
                        "Máq. Router",
                        "Prioridad",
                        "Corte",
                        "Estado",
                        "Impresión",
                        "Router",
                        "Finalización"
                    ]
    
                    # Distribución compacta para mantener A4 horizontal.
                    widths = [
                        16, 39, 20, 33, 28, 27, 11, 22, 27, 27, 27
                    ]
    
                    def pdf_text(valor):
                        """
                        Convierte cualquier valor a texto compatible
                        con Helvetica de FPDF.
                        """
                        if valor is None:
                            return ""
    
                        try:
                            if pd.isna(valor):
                                return ""
                        except Exception:
                            pass
    
                        return (
                            str(valor)
                            .encode(
                                "latin-1",
                                "replace"
                            )
                            .decode("latin-1")
                        )
    
                    def fdt(valor):
                        """
                        Formatea fechas evitando problemas con NaT,
                        None y valores no fecha.
                        """
                        if valor is None:
                            return ""
    
                        try:
                            if pd.isna(valor):
                                return ""
                        except Exception:
                            pass
    
                        if hasattr(valor, "strftime"):
                            try:
                                return valor.strftime(
                                    "%d/%m/%y %H:%M"
                                )
                            except (
                                ValueError,
                                TypeError,
                                AttributeError
                            ):
                                return ""
    
                        return str(valor)[:16]
    
                    pdf.set_font(
                        "Helvetica",
                        "B",
                        6.5
                    )
    
                    for encabezado, ancho in zip(
                        headers,
                        widths
                    ):
    
                        pdf.cell(
                            ancho,
                            6,
                            pdf_text(encabezado),
                            border=1,
                            align="C"
                        )
    
                    pdf.ln()
    
                    # =================================================
                    # FILAS
                    # =================================================
                    pdf.set_font(
                        "Helvetica",
                        "",
                        6.2
                    )
    
                    for _, r in df_fin.iterrows():
    
                        requiere_corte = r.get(
                            "Requiere corte",
                            ""
                        )
    
                        if isinstance(
                            requiere_corte,
                            bool
                        ):
                            corte_txt = (
                                "SI"
                                if requiere_corte
                                else "NO"
                            )
                        else:
                            corte_txt = pdf_text(
                                requiere_corte
                            )
    
                        valores = [
                            r.get("ODP", ""),
                            r.get("Cliente", ""),
                            r.get("Material", ""),
                            r.get(
                                "Máquina Impresión",
                                ""
                            ),
                            r.get(
                                "Máquina Router",
                                ""
                            ) or "—",
                            r.get("Prioridad", "NORMAL"),
                            corte_txt,
                            r.get("Estado", ""),
                            fdt(
                                r.get(
                                    "Impresión"
                                )
                            ),
                            fdt(
                                r.get(
                                    "Router"
                                )
                            ),
                            fdt(
                                r.get(
                                    "Finalización"
                                )
                            )
                        ]
    
                        for valor, ancho in zip(
                            valores,
                            widths
                        ):
    
                            texto = pdf_text(valor)
    
                            limite = max(
                                8,
                                int(ancho / 1.6)
                            )
    
                            pdf.cell(
                                ancho,
                                5.5,
                                texto[:limite],
                                border=1
                            )
    
                        pdf.ln()
    
                    # =================================================
                    # GENERAR PDF COMO BYTES
                    # =================================================
                    #
                    # IMPORTANTE:
                    # NO usar:
                    #
                    # pdf.output(dest="S").encode(...)
                    #
                    # porque FPDF2 puede devolver bytearray.
                    #
                    pdf_tmp = os.path.join(
                        tempfile.gettempdir(),
                        (
                            f"odps_finalizadas_"
                            f"{os.getpid()}_"
                            f"{ahora_mexico().strftime('%Y%m%d%H%M%S%f')}.pdf"
                        )
                    )
    
                    try:
    
                        # FPDF escribe directamente al archivo
                        pdf.output(pdf_tmp)
    
                        # Leemos el PDF como bytes
                        with open(
                            pdf_tmp,
                            "rb"
                        ) as archivo_pdf:
    
                            pdf_data = archivo_pdf.read()
    
                    finally:
    
                        # Limpiar archivo temporal
                        try:
    
                            if os.path.exists(
                                pdf_tmp
                            ):
    
                                os.remove(
                                    pdf_tmp
                                )
    
                        except OSError:
                            pass
    
                    # =================================================
                    # BOTONES DE DESCARGA
                    # =================================================
                    d1, d2 = st.columns(2)
    
                    with d1:
    
                        st.download_button(
                            "📄 EXPORTAR REPORTE PDF",
                            pdf_data,
                            (
                                f"ODPs_"
                                f"{fecha_inicio}_al_"
                                f"{fecha_fin}.pdf"
                            ),
                            "application/pdf",
                            use_container_width=True,
                            key="download_pdf_odps_finalizadas"
                        )
    
                    with d2:
    
                        st.download_button(
                            "📊 EXPORTAR DATOS EXCEL",
                            excel_data,
                            (
                                f"ODPs_"
                                f"{fecha_inicio}_al_"
                                f"{fecha_fin}.xlsx"
                            ),
                            (
                                "application/vnd.openxmlformats-"
                                "officedocument.spreadsheetml.sheet"
                            ),
                            use_container_width=True,
                            key="download_excel_odps_finalizadas"
                        )
    
                    # =================================================
                    # TABLA
                    # =================================================
                    columnas_registro = [c for c in [
                        "ODP", "Cliente", "Material", "Prioridad", "Máquina Impresión", "Máquina Router",
                        "Ruta", "m²", "Láminas", "Pasadas", "Min total estimado", "Estado", "Finalización"
                    ] if c in df_fin.columns]
                    df_tabla = df_fin[columnas_registro].copy()
                    if "Min total estimado" in df_tabla.columns:
                        df_tabla["Tiempo"] = df_tabla["Min total estimado"].apply(lambda x: formatear_duracion(_numero_seguro(x)))
                        df_tabla.drop(columns=["Min total estimado"], inplace=True)
                    if "Finalización" in df_tabla.columns:
                        df_tabla["Finalización"] = pd.to_datetime(df_tabla["Finalización"], errors="coerce").dt.strftime("%d/%m/%y %H:%M")
                    st.dataframe(df_tabla, use_container_width=True, hide_index=True, height=330, column_config={
                        "ODP": st.column_config.TextColumn("ODP", width="small"),
                        "Cliente": st.column_config.TextColumn("Cliente", width="medium"),
                        "Material": st.column_config.TextColumn("Material", width="small"),
                        "Prioridad": st.column_config.TextColumn("Prioridad", width="small"),
                        "Tiempo": st.column_config.TextColumn("Tiempo", width="small"),
                        "Estado": st.column_config.TextColumn("Estado", width="small"),
                    })
    
        else:
    
            st.warning(
                "Por favor, selecciona una fecha de inicio "
                "y una fecha de fin."
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
