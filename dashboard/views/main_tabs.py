"""Orquestación de las pestañas principales del dashboard.

Este módulo contiene únicamente composición de vistas: no implementa reglas
 de negocio. Mantiene el orden y el comportamiento de las pestañas originales.
"""

import streamlit as st


def render_main_tabs(context):
    """Renderiza las pestañas principales conservando el flujo existente."""

    fecha_consulta = context.fecha_consulta
    ahora_mexico = context.ahora_mexico
    machine_configs = context.machine_configs
    current_dir = context.current_dir
    query_db = context.query_db
    commit_db = context.commit_db
    run_camera = context.run_camera
    render_estatus = context.render_estatus
    render_planta = context.render_planta
    render_registro_odp = context.render_registro_odp
    render_operacion_odp = context.render_operacion_odp
    render_historial_odp = context.render_historial_odp
    render_analisis = context.render_analisis
    render_bitacora = context.render_bitacora
    render_gestion = context.render_gestion
    render_machine_card = context.render_machine_card
    lista_maquinas = context.lista_maquinas
    reiniciar_modo_interaccion = context.reiniciar_modo_interaccion
    obtener_nombres_maquinas_operativas = context.obtener_nombres_maquinas_operativas
    obtener_maquinas_impresion = context.obtener_maquinas_impresion
    obtener_maquinas_router = context.obtener_maquinas_router
    es_maquina_router = context.es_maquina_router
    normalizar_prioridad_odp = context.normalizar_prioridad_odp
    etiqueta_prioridad_odp = context.etiqueta_prioridad_odp
    prioridad_es_critica = context.prioridad_es_critica
    formatear_duracion = context.formatear_duracion
    numero_seguro = context.numero_seguro
    render_produccion = context.render_produccion
    todas_maquinas = context.todas_maquinas
    obtener_odps_en_proceso = context.obtener_odps_en_proceso
    PRIORIDADES_ODP = context.PRIORIDADES_ODP
    TIPOS_CORTE = context.TIPOS_CORTE
    planta_html = context.planta_html
    planta_escape = context.planta_escape
    config_produccion_maquina = context.config_produccion_maquina
    asignar_odp = context.asignar_odp
    registrar_odp = context.registrar_odp
    calcular_area_produccion = context.calcular_area_produccion
    estimar_produccion = context.estimar_produccion
    maquinas_impresion = context.maquinas_impresion
    maquinas_impresion_compatibles = context.maquinas_impresion_compatibles
    maquinas_router = context.maquinas_router
    opciones_pasadas_para_maquina = context.opciones_pasadas_para_maquina
    routers_compatibles = context.routers_compatibles
    largo_lamina_rigida_m = context.largo_lamina_rigida_m
    m2_por_lamina_rigida = context.m2_por_lamina_rigida
    editar_asignacion_produccion = context.editar_asignacion_produccion
    eliminar_asignacion = context.eliminar_asignacion
    actualizar_estado_asignacion = context.actualizar_estado_asignacion
    obtener_registro_odps_finalizadas = context.obtener_registro_odps_finalizadas
    dataframe_to_xlsx_bytes = context.dataframe_to_xlsx_bytes
    generar_pdf_odps_finalizadas = context.generar_pdf_odps_finalizadas
    process_smart_grid = context.process_smart_grid
    generar_pdf_reporte_maquinas = context.generar_pdf_reporte_maquinas
    ahora_mexico_texto = context.ahora_mexico_texto
    sql_ahora_mexico = context.sql_ahora_mexico


    hora_ajustada = ahora_mexico()
    fecha_mostrar = hora_ajustada.strftime("%d/%m/%Y")
    es_hoy = fecha_consulta == hora_ajustada.date()

    if es_hoy:
        st.subheader(f"📊 Monitoreo en Tiempo Real ({fecha_mostrar})")
    else:
        st.subheader(f"📰 Historial de Planta: {fecha_consulta.strftime('%d/%m/%Y')}")

    (
        tab_carrusel,
        tab_planta,
        tab_registro,
        tab_analisis,
        tab_bitacora,
        tab_gestion,
    ) = st.tabs([
        "🔄 Render Estatus",
        "🏬 Render Producción",
        "✍️Resgistro odp´s ",
        "🔍 Análisis de Test",
        "📙 Bitacoras",
        "⚙️ Gestión Administrador",
    ])

    interactuando = (
        st.session_state.get("bloquear_refresco", False)
        or run_camera
        or st.session_state.get("mostrar_descargas", False)
        or st.session_state.get("editando_manual", False)
    )

    if interactuando:
        st.sidebar.warning("⏸️ Monitoreo en pausa (Modo de edición activo)")
        if st.sidebar.button("▶️ Reanudar Monitoreo Auto"):
            reiniciar_modo_interaccion()

    render_estatus(
        tab_carrusel,
        fecha_consulta=fecha_consulta,
        interactuando=interactuando,
        lista_maquinas=lista_maquinas,
        render_machine_card=render_machine_card,
    )

    render_planta(
        tab_planta,
        machine_configs=machine_configs,
        current_dir=current_dir,
        query_db=query_db,
        obtener_nombres_maquinas_operativas=obtener_nombres_maquinas_operativas,
        obtener_maquinas_impresion=obtener_maquinas_impresion,
        obtener_maquinas_router=obtener_maquinas_router,
        es_maquina_router=es_maquina_router,
        normalizar_prioridad_odp=normalizar_prioridad_odp,
        etiqueta_prioridad_odp=etiqueta_prioridad_odp,
        prioridad_es_critica=prioridad_es_critica,
        formatear_duracion=formatear_duracion,
        numero_seguro=numero_seguro,
        render_produccion=render_produccion,
    )

    with tab_registro:
        # Los servicios ODP se crean en dashboard.py y se exponen aquí mediante
        # sus métodos ya validados. La vista no conoce detalles de construcción.
        render_registro_odp(
            LARGO_LAMINA_RIGIDA_M=largo_lamina_rigida_m,
            PRIORIDADES_ODP=PRIORIDADES_ODP,
            TIPOS_CORTE=TIPOS_CORTE,
            _config_produccion_maquina=config_produccion_maquina,
            _numero_seguro=numero_seguro,
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
            _numero_seguro=numero_seguro,
            formatear_duracion=formatear_duracion,
            opciones_pasadas_para_maquina=opciones_pasadas_para_maquina,
            _config_produccion_maquina=config_produccion_maquina,
            editar_asignacion_produccion=editar_asignacion_produccion,
            eliminar_asignacion=eliminar_asignacion,
            actualizar_estado_asignacion=actualizar_estado_asignacion,
            maquinas_impresion=maquinas_impresion,
            maquinas_router=maquinas_router,
            LARGO_LAMINA_RIGIDA_M=largo_lamina_rigida_m,
            M2_POR_LAMINA_RIGIDA=m2_por_lamina_rigida,
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
            numero_seguro=numero_seguro,
        )

    with tab_analisis:
        render_analisis(
            machine_configs=machine_configs,
            process_smart_grid=process_smart_grid,
            commit_db=commit_db,
            ahora_mexico=ahora_mexico,
        )

    with tab_bitacora:
        render_bitacora(
            machine_configs=machine_configs,
            query_db=query_db,
            commit_db=commit_db,
            ahora_mexico=ahora_mexico,
        )

    with tab_gestion:
        render_gestion(
            machine_configs=machine_configs,
            query_db=query_db,
            commit_db=commit_db,
            ahora_mexico=ahora_mexico,
            ahora_mexico_texto=ahora_mexico_texto,
            sql_ahora_mexico=sql_ahora_mexico,
            generar_pdf_reporte_maquinas=generar_pdf_reporte_maquinas,
            formatear_duracion=formatear_duracion,
            numero_seguro=numero_seguro,
        )
