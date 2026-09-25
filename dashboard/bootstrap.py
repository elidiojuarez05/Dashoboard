"""Punto de arranque de la aplicación Streamlit.

La lógica de ejecución se mantiene aquí para que dashboard.py pueda actuar
como un entrypoint mínimo compatible con Streamlit Cloud.
"""

# =========================================================
# 1. IMPORTACIONES Y DEPENDENCIAS
# =========================================================
# Librería estándar
import os
import sys
import time
from datetime import datetime, timedelta, time as dt_time

# Dependencias de terceros
import pandas as pd
import pytz
import streamlit as st


def run_dashboard():

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
            ANCHO_LAMINA_RIGIDA_M,
            LARGO_LAMINA_RIGIDA_M,
            M2_POR_LAMINA_RIGIDA,
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
    from dashboard.utils.ui import render_html, ui_escape
    from dashboard.components.priority import PRIORIDADES_ODP, normalizar_prioridad_odp, etiqueta_prioridad_odp, prioridad_es_critica
    from dashboard.utils.formatting import formatear_duracion
    from dashboard.services.report_service import generar_pdf_reporte_maquinas
    from dashboard.services.odp_service import ODPService
    from dashboard.services.application_service import ApplicationServices
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
    # 5. ESTILOS VISUALES GLOBALES
    # =========================================================
    from dashboard.styles.theme import aplicar_estilos_globales

    aplicar_estilos_globales()

    # =========================================================
    # 6. INICIALIZACIÓN DE SESSION STATE Y COOKIES
    # =========================================================
    from dashboard.utils.session import inicializar_sesion, reiniciar_modo_interaccion

    cookies = inicializar_sesion(MACHINE_CONFIGS)
    run_camera = False

    # =========================================================
    # 7. CONEXIÓN Y LÓGICA DE BASE DE DATOS
    # =========================================================
    conn = st.connection("postgresql", type="sql")

    def es_maquina_router(nombre_maquina):
        config = MACHINE_CONFIGS.get(nombre_maquina, {})
        if isinstance(config, dict) and str(config.get("type", "")).lower() == "manual":
            return True
        return "router" in str(nombre_maquina).lower()

    _app_services = ApplicationServices(
        conn=conn,
        machine_configs=MACHINE_CONFIGS,
        ahora_mexico=ahora_mexico,
        es_maquina_router=es_maquina_router,
        estimar_produccion=estimar_produccion,
        formatear_duracion=formatear_duracion,
        numero_seguro=lambda valor, default=0.0: _status_service.numero_seguro(valor, default),
        norm_nombre_estacion=_norm_nombre_estacion,
        maquina_compatible_material=maquina_compatible_material,
    )
    _db_service = _app_services.db
    _auth_service = _app_services.auth
    _status_service = _app_services.status
    _odp_query_service = _app_services.odp_query

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










    def obtener_odps_en_proceso(maquina=None):
        return _odp_query_service.obtener_odps_en_proceso(maquina)

    def obtener_odps_finalizadas(maquina=None, fecha_inicio=None, fecha_fin=None):
        return _odp_query_service.obtener_odps_finalizadas(maquina, fecha_inicio, fecha_fin)

    def obtener_registro_odps_finalizadas(maquina=None, fecha_inicio=None, fecha_fin=None):
        return _odp_query_service.obtener_registro_odps_finalizadas(maquina, fecha_inicio, fecha_fin)


    def check_password(username, password):
        return _auth_service.check_password(username, password)






    # =========================================================
    # 9. ACCESO Y ORQUESTACIÓN PRINCIPAL
    # =========================================================
    from dashboard.views.planta import render_planta
    from dashboard.views.main_tabs import render_main_tabs
    from dashboard.views.view_context import DashboardViewContext

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

    lista_maquinas = list(MACHINE_CONFIGS.keys())
    maquinas_impresion = obtener_maquinas_impresion()
    maquinas_router = obtener_maquinas_router()
    todas_maquinas = lista_maquinas

    # El servicio ODP se construye una sola vez desde ApplicationServices.
    _odp_service = _app_services.odp

    contexto = DashboardViewContext(
        fecha_consulta=fecha_consulta,
        ahora_mexico=ahora_mexico,
        machine_configs=MACHINE_CONFIGS,
        current_dir=current_dir,
        query_db=query_db,
        commit_db=commit_db,
        run_camera=run_camera,
        render_estatus=render_estatus,
        render_planta=render_planta,
        render_registro_odp=render_registro_odp,
        render_operacion_odp=render_operacion_odp,
        render_historial_odp=render_historial_odp,
        render_analisis=render_analisis,
        render_bitacora=render_bitacora,
        render_gestion=render_gestion,
        render_machine_card=render_machine_card,
        lista_maquinas=lista_maquinas,
        reiniciar_modo_interaccion=reiniciar_modo_interaccion,
        obtener_nombres_maquinas_operativas=obtener_nombres_maquinas_operativas,
        obtener_maquinas_impresion=obtener_maquinas_impresion,
        obtener_maquinas_router=obtener_maquinas_router,
        es_maquina_router=es_maquina_router,
        normalizar_prioridad_odp=normalizar_prioridad_odp,
        etiqueta_prioridad_odp=etiqueta_prioridad_odp,
        prioridad_es_critica=prioridad_es_critica,
        formatear_duracion=formatear_duracion,
        numero_seguro=_numero_seguro,
        render_produccion=render_produccion,
        todas_maquinas=todas_maquinas,
        obtener_odps_en_proceso=obtener_odps_en_proceso,
        PRIORIDADES_ODP=PRIORIDADES_ODP,
        TIPOS_CORTE=TIPOS_CORTE,
        planta_html=render_html,
        planta_escape=ui_escape,
        config_produccion_maquina=_config_produccion_maquina,
        asignar_odp=_odp_service.asignar_odp,
        registrar_odp=_odp_service.registrar_odp,
        calcular_area_produccion=calcular_area_produccion,
        estimar_produccion=estimar_produccion,
        maquinas_impresion=maquinas_impresion,
        maquinas_impresion_compatibles=maquinas_impresion_compatibles,
        maquinas_router=maquinas_router,
        opciones_pasadas_para_maquina=opciones_pasadas_para_maquina,
        routers_compatibles=routers_compatibles,
        largo_lamina_rigida_m=LARGO_LAMINA_RIGIDA_M,
        m2_por_lamina_rigida=M2_POR_LAMINA_RIGIDA,
        editar_asignacion_produccion=_odp_service.editar_asignacion_produccion,
        eliminar_asignacion=_odp_service.eliminar_asignacion,
        actualizar_estado_asignacion=_odp_service.actualizar_estado_asignacion,
        obtener_registro_odps_finalizadas=obtener_registro_odps_finalizadas,
        dataframe_to_xlsx_bytes=dataframe_to_xlsx_bytes,
        generar_pdf_odps_finalizadas=generar_pdf_odps_finalizadas,
        process_smart_grid=process_smart_grid,
        generar_pdf_reporte_maquinas=generar_pdf_reporte_maquinas,
        ahora_mexico_texto=ahora_mexico_texto,
        sql_ahora_mexico=SQL_AHORA_MEXICO,
    )

    render_main_tabs(contexto)



if __name__ == "__main__":
    run_dashboard()
